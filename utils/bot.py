import os
import asyncio
from dotenv import load_dotenv
from loguru import logger
import aiohttp
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor

from utils.call_audio import save_audio, finalize_audio_recording
from utils.post_call import delayed_background_processing
import asyncio

print("🚀 Starting Pipecat bot...")

# Global variables for pre-initialized components
_tools_schema = None


_cost_tracker = None
_session = None
_initialization_lock = asyncio.Lock()

load_dotenv(override=True)




async def initialize_heavy_components():
    """Initialize expensive components once at startup"""
    global _tools_schema, _cost_tracker, _session

    if _tools_schema is not None:
        return  # Already initialized

    async with _initialization_lock:
        if _tools_schema is not None:
            return  # Double-check after acquiring lock

        logger.info("🔧 Initializing heavy components...")

        try:
            # Import heavy components only when needed
            from pipecat.adapters.schemas.tools_schema import ToolsSchema
            from utils.tool_schema import fs_get_nearby_clinics, fs_end_call
            from utils.cost_tracker import CostTracker

            # Pre-initialize tools schema
            _tools_schema = ToolsSchema(
                standard_tools=[fs_get_nearby_clinics, fs_end_call]
            )

            # Pre-create session and cost tracker
            _session = aiohttp.ClientSession()
            _cost_tracker = CostTracker()

            logger.info("✅ Heavy components initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize heavy components: {e}")
            raise e


async def run_bot(
    transport,  # Will be BaseTransport when imported
    handle_sigint: bool,
    call_data: dict,
):
    logger.info(f"Starting bot")

    # Components are already initialized at startup, no need to call again
    # Use global pre-initialized components
    session = _session
    cost_tracker = _cost_tracker

    # Import SimpleCostMonitor here
    from utils.cost_tracker import SimpleCostMonitor

    cost_monitor = SimpleCostMonitor(cost_tracker)

    try:
        # Import heavy components only when needed
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineTask, PipelineParams
        from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
        from pipecat.processors.frameworks.rtvi import (
            RTVIConfig,
            RTVIObserver,
            RTVIProcessor,
        )
        from pipecat.processors.transcript_processor import TranscriptProcessor
        from pipecat.frames.frames import (
            TranscriptionMessage,
            LLMRunFrame,
            LLMMessagesAppendFrame,
            TextFrame,
        )
        from pipecat.transports.base_transport import BaseTransport
        from model.model import Call, CallStatus
        from pipecat.runner.types import RunnerArguments

        # Extract customer name from WebSocket URL parameters (fastest method)
        # The name is nested under 'body' in call_data
        body_data = call_data.get("body", {})
        customer_name = body_data.get("name", "there")
        
        if customer_name != "there":
            logger.info(f"🚀 OPTIMIZED: Using customer name from URL parameters: {customer_name}")
        else:
            logger.info("📝 No name found in URL parameters, using default 'there'")

        # Create dynamic prompt with customer name
        from utils.prompt import create_dynamic_prompt
        dynamic_prompt = create_dynamic_prompt(customer_name)

        # Create a new LLM service instance with dynamic prompt
        from pipecat.services.gemini_multimodal_live.gemini import (
            GeminiMultimodalLiveLLMService,
            InputParams,
        )
        from pipecat.transcriptions.language import Language

        # Use pre-initialized tools schema
        tools_schema = _tools_schema

        # Create LLM service with dynamic prompt
        llm = GeminiMultimodalLiveLLMService(
            api_key=os.getenv("GEMINI_API_KEY"),
            model="models/gemini-2.0-flash-live-001",
            params=InputParams(language=Language.EN_IN),
            system_instruction=dynamic_prompt,  # Use dynamic prompt
            voice_id="Zephyr",
            tools=tools_schema,
        )

        # Register function handlers
        from utils.tool_schema import _handle_get_nearby_clinics, _handle_end_call
        llm.register_function("get_nearby_clinics", _handle_get_nearby_clinics)
        llm.register_function("end_call", _handle_end_call)
        messages = [
            {
                "role": "user",
                "content": f'Start by saying "Hello {customer_name}! I\'m Ananya from Toothsi. How can I help you today?"',
            },
        ]
        context = OpenAILLMContext(messages)
        context_aggregator = llm.create_context_aggregator(context)
        transcript_list = []
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

        # Create an audio buffer processor to capture conversation audio
        audiobuffer = AudioBufferProcessor(
            sample_rate=None,
            num_channels=2,
            buffer_size=0,
            enable_turn_audio=False,
        )

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
                audiobuffer,
                transcript.assistant(),
                context_aggregator.assistant(),
            ]
        )
        idle_timeout_secs = os.getenv("IDLE_TIMEOUT_SECS", 20)
        
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=8000,  # Twilio's audio format
                audio_out_sample_rate=8000,
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
            
            idle_timeout_secs=int(idle_timeout_secs),  # 20 seconds
            
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

            # Update database status
            call = await Call.find_one({"call_sid": call_data["call_id"]})
            if call:
                call.status = CallStatus.IN_PROGRESS
                await call.save()

            # Start recording
            await audiobuffer.start_recording()

            # Queue the main LLM response with immediate greeting
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

                        async with aiofiles.open(
                            "transcripts.txt", "a", encoding="utf-8"
                        ) as f:
                            await f.write(line + "\n")
                    except Exception as e:
                        logger.warning(f"Failed to write transcript to file: {e}")
                else:
                    logger.info(f"🔍 Non-transcription message: {type(msg)} - {msg}")

        @audiobuffer.event_handler("on_audio_data")
        async def on_audio_data(buffer, audio, sample_rate, num_channels):
            server_name = f"server_{call_data['call_id']}"
            await save_audio(server_name, audio, sample_rate, num_channels)
            

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            summary = cost_tracker.get_final_summary()
            transcript_text = "\n".join(transcript_list)
            
            print(f"   Total Cost: ${summary['total_cost']:.2f}")
            logger.info(f"Client disconnected ❌❌❌")
            
            # Stop audio recording first to ensure file writing is complete
            try:
                await audiobuffer.stop_recording()
                logger.info(f"🎬 Audio recording stopped for call {call_data['call_id']}")
            except Exception as e:
                logger.warning(f"Failed to stop audio recording: {e}")
            
            # Add a small delay to ensure file writing is complete
            await asyncio.sleep(0.5)  # 500ms delay
            
            # Finalize audio recording and trigger upload
            try:
                server_name = f"server_{call_data['call_id']}"
                call_cost = float(summary.get("total_cost", 0.0))
                await finalize_audio_recording(call_data['call_id'], server_name, transcript_text, call_cost)
                logger.info(f"🎬 Audio recording finalized for call {call_data['call_id']}")
            except Exception as e:
                logger.error(f"❌ Failed to finalize audio recording: {e}")
                # Fallback to old method if finalization fails
                try:
                    call_cost = float(summary.get("total_cost", 0.0))
                    asyncio.create_task(delayed_background_processing(
                        call_sid=str(call_data["call_id"]),
                        transcript=str(transcript_text),
                        call_cost=call_cost,
                        status="completed"
                    ))
                    logger.info(f"🚀 Fallback background processing started for call {call_data['call_id']}")
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback background processing also failed: {fallback_error}")

            await task.cancel()

        runner = PipelineRunner(handle_sigint=handle_sigint)

        await runner.run(task)
    finally:
        await session.close()


async def bot(runner_args):
    """Main bot entry point compatible with Pipecat Cloud."""

    # Import heavy components only when needed
    from pipecat.runner.utils import parse_telephony_websocket
    from pipecat.serializers.twilio import TwilioFrameSerializer
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketParams,
        FastAPIWebsocketTransport,
    )
    from pipecat.audio.vad.silero import SileroVADAnalyzer

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
