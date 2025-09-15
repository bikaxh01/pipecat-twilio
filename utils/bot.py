import os

from dotenv import load_dotenv
from loguru import logger
import aiohttp
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor

from utils.prompt import PROMPT

print("🚀 Starting Pipecat bot...")
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer

from pipecat.pipeline.pipeline import Pipeline

from pipecat.pipeline.runner import PipelineRunner
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.services.gemini_multimodal_live.gemini import (
    GeminiMultimodalLiveLLMService,
    InputParams,
)
from pipecat.frames.frames import (
    TranscriptionMessage,
    LLMRunFrame,
    LLMMessagesAppendFrame,
)
from pipecat.transcriptions.language import Language
from model.model import Call, CallStatus

# import tools
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from utils.tool_schema import fs_get_nearby_clinics, _handle_get_nearby_clinics, fs_end_call, _handle_end_call
from pipecat.transports.base_transport import BaseTransport
from utils.cost_tracker import CostTracker, SimpleCostMonitor

load_dotenv(override=True)


async def run_bot(
    transport: BaseTransport,
    handle_sigint: bool,
    call_data: dict,
):
    logger.info(f"Starting bot")

    session = aiohttp.ClientSession()
    cost_tracker = CostTracker()
    cost_monitor = SimpleCostMonitor(cost_tracker)
    try:
        # Build function schemas for tool calls
        tools_schema = ToolsSchema(
            standard_tools=[
                fs_get_nearby_clinics,
                fs_end_call,
            ]
        )

        llm = GeminiMultimodalLiveLLMService(
            api_key=os.getenv("GEMINI_API_KEY"),
            model="models/gemini-2.0-flash-live-001",
            params=InputParams(language=Language.EN_IN),
            system_instruction=PROMPT,
            voice_id="Zephyr",
            tools=tools_schema,
        )

        # register handlers with the LLM service
        llm.register_function("get_nearby_clinics", _handle_get_nearby_clinics)
        llm.register_function("end_call", _handle_end_call)
        messages = [
            {
                "role": "user",
                "content": 'Start by saying "Hello, and give short intro',
            },
        ]
        context = OpenAILLMContext(messages)
        context_aggregator = llm.create_context_aggregator(context)
        transcript_list = []
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

        transcript = TranscriptProcessor()

        # Override the start_llm_usage_metrics method to capture cost data
        original_start_llm_usage_metrics = llm.start_llm_usage_metrics

        async def custom_start_llm_usage_metrics(tokens):
            cost_tracker.log_usage(tokens.prompt_tokens, tokens.completion_tokens)
            return await original_start_llm_usage_metrics(tokens)

        llm.start_llm_usage_metrics = custom_start_llm_usage_metrics

        pipeline = Pipeline(
            [
                transport.input(),
                context_aggregator.user(),
                rtvi,
                transcript.user(),
                llm,
                transport.output(),
                transcript.assistant(),
                context_aggregator.assistant(),
            ]
        )
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=8000,  # Twilio's audio format
                audio_out_sample_rate=8000,
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
            idle_timeout_secs=20,  # 20 seconds
            cancel_on_idle_timeout=False,  # Don't auto-cancel
            observers=[RTVIObserver(rtvi)],
        )

        @task.event_handler("on_idle_timeout")
        async def on_idle_timeout(task):
            logger.info("Conversation has been idle for 20 seconds")
            messages = [
                {
                    "role": "user",
                    "content": "The user has been idle for 20 seconds. say: Hey are you there?",
                },
            ]
            await task.queue_frame(
                LLMMessagesAppendFrame(messages=messages, run_llm=True)
            )

        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info(f"Client connected")
            logger.info(f"Transport call_sid: {transport}")
            call = await Call.find_one({"call_sid": call_data["call_id"]})
            if call:
                call.status = CallStatus.IN_PROGRESS
                await call.save()

            await task.queue_frames([LLMRunFrame()])

        @transcript.event_handler("on_transcript_update")
        async def handle_update(processor, frame):
            logger.info(
                f"🔍 Transcript update received: {len(frame.messages)} messages"
            )
            for msg in frame.messages:
                if isinstance(msg, TranscriptionMessage):
                    line = f"{msg.role}: {msg.content}"
                    transcript_list.append(line)
                    # Example: Save to a list or file (async to avoid blocking)
                    try:
                        import aiofiles
                        async with aiofiles.open("transcripts.txt", "a", encoding="utf-8") as f:
                            await f.write(line + "\n")
                    except Exception as e:
                        logger.warning(f"Failed to write transcript to file: {e}")
                else:
                    logger.info(f"🔍 Non-transcription message: {type(msg)} - {msg}")

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            summary = cost_tracker.get_final_summary()
            
            # Add timeout for database operations to prevent pipeline blocking
            try:
                import asyncio
                call = await asyncio.wait_for(
                    Call.find_one({"call_sid": call_data["call_id"]}),
                    timeout=5.0  # 5 second timeout
                )
                if call:
                    call.status = CallStatus.COMPLETED
                    call.call_cost = round(summary["total_cost"], 2)
                    call.transcript = "\n".join(transcript_list)
                    await asyncio.wait_for(call.save(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Database operation timed out during call cleanup")
            except Exception as e:
                logger.error(f"Error during call cleanup: {e}")

            print(f"   Total Cost: ${summary['total_cost']:.2f}")
            logger.info(f"Client disconnected ❌❌❌")

            await task.cancel()

        runner = PipelineRunner(handle_sigint=handle_sigint)

        await runner.run(task)
    finally:
        await session.close()


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""

    transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
    logger.info(f"Auto-detected transport: {transport_type}")

    serializer = TwilioFrameSerializer(
        stream_sid=call_data["stream_id"],
        call_sid=call_data["call_id"],
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
    )

    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=serializer,
        ),
    )
    handle_sigint = runner_args.handle_sigint

    logger.info(f"Transport 🟢🟢: {handle_sigint}")

    await run_bot(transport, handle_sigint, call_data)
