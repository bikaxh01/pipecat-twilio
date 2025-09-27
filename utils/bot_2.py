import os
import asyncio
from dotenv import load_dotenv
from loguru import logger
import aiohttp

from pipecat.processors.frameworks.rtvi import RTVIProcessor, RTVIConfig
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIObserver

from utils.tool_schema import (
    fs_get_nearby_clinics,
    fs_end_call,
    _handle_get_nearby_clinics,
    _handle_end_call,
)


from pipecat.processors.transcript_processor import TranscriptProcessor
from utils.prompt import create_dynamic_prompt

from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor

from pipecat.frames.frames import (
    LLMMessagesAppendFrame,
    TranscriptionMessage,
    LLMRunFrame,
)
import asyncio
from pipecat.adapters.schemas.tools_schema import ToolsSchema

# Import post-call processing utilities
from utils.call_audio import save_audio, finalize_audio_recording
from utils.post_call import delayed_background_processing
from model.model import Call, CallStatus
from bots.standard.metric_collector import MetricsCollector


load_dotenv(override=True)


async def run_bot_2(
    transport,  
    handle_sigint: bool,
    call_data: dict,
):
    logger.info(f"Starting bot")

    session = aiohttp.ClientSession()

    try:
        from utils.call_config import (
            get_providers_from_call,
            get_stt_service_config,
            get_tts_service_config,
        )

        logger.info(f"Call data: 🟢🟢🟢🟢{call_data}")

        # Get both STT and TTS providers from a single DB call
        stt_provider, tts_provider, llm_provider = await get_providers_from_call(
            call_data["call_id"]
        )
        logger.info(f"STT provider: {stt_provider}, TTS provider: {tts_provider}")

        # Get STT service configuration
        stt = get_stt_service_config(stt_provider)

        # Get TTS service configuration
        tts = get_tts_service_config(tts_provider, session)

        # Build function schemas for tool calls
        tools_schema = ToolsSchema(
            standard_tools=[
                fs_get_nearby_clinics,
                fs_end_call,
            ]
        )
        metric_collector = MetricsCollector()

        from utils.call_config import get_llm_service_config

        llm = get_llm_service_config(llm_provider)
        logger.info(f"STT service: 🟢🟢🟢🟢{stt}")
        logger.info(f"LLM service: 🟢🟢🟢🟢{llm}")
        logger.info(f"TTS service: 🟢🟢🟢🟢{tts}")

        # register handlers with the LLM service
        llm.register_function("get_nearby_clinics", _handle_get_nearby_clinics)
        llm.register_function("end_call", _handle_end_call)
        body_data = call_data.get("body", {})
        customer_name = body_data.get("name", "there")
        dynamic_prompt = await create_dynamic_prompt(customer_name, multimodel=False)

        messages = [
            {
                "role": "system",
                "content": dynamic_prompt,
            },
            {
                "role": "user",
                "content": "say: Hello,",
            },
        ]

        context = OpenAILLMContext(messages, tools=tools_schema)
        context_aggregator = llm.create_context_aggregator(context)

        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
        transcript = TranscriptProcessor()

        # Create an audio buffer processor to capture conversation audio
        audiobuffer = AudioBufferProcessor(
            sample_rate=None,
            num_channels=2,
            buffer_size=0,
            enable_turn_audio=False,
        )
        from bots.standard.metric_collector import CostCollector
        cost_collector = CostCollector()
        # Initialize transcript list for tracking
        transcript_list = []

        # Track transcript updates
        @transcript.event_handler("on_transcript_update")
        async def handle_transcript_update(processor, frame):
            logger.info(
                f"🔍 Transcript update received: {len(frame.messages)} messages"
            )
            for msg in frame.messages:
                if isinstance(msg, TranscriptionMessage):
                    # Estimate audio duration based on text length (rough approximation)
                    # Average speaking rate is about 150 words per minute = 2.5 words per second
                    # Average word length is about 5 characters
                    text_length = len(msg.content)
                    estimated_duration = (text_length / 5) / 2.5  # Convert to seconds

                    # Add to transcript list for post-call processing
                    line = f"{msg.role}: {msg.content}"
                    transcript_list.append(line)

                    # Log transcript to file
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

        pipeline = Pipeline(
            [
                transport.input(),  # Transport user input
                rtvi,  # RTVI processor
                stt,  # STT (Deepgram for speech-to-text)
                transcript.user(),
                context_aggregator.user(),  # User responses
                llm,  # LLM (OpenAI for text-to-text)
                tts,  # TTS (Sarvam for text-to-speech)
                transport.output(),  # Transport bot output
                audiobuffer,  # Audio buffer for recording
                transcript.assistant(),  # Assistant spoken responses
                context_aggregator.assistant(),  # Assistant context
            ]
        )
        idle_timeout_secs = os.getenv("IDLE_TIMEOUT_SECS", 10)
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=8000,  # Twilio's audio format
                audio_out_sample_rate=8000,
                allow_interruptions=True,
                report_only_initial_ttfb=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                idle_timeout_secs=int(idle_timeout_secs),
                cancel_on_idle_timeout=False,  # Don't auto-cancel
            ),
            observers=[RTVIObserver(rtvi), metric_collector],
        )

        # Debug: Log that the metrics collector has been added
        logger.info(f"🔧 MetricsCollector added to task observers")
        logger.info(
            f"🔧 Metrics enabled: enable_metrics={True}, enable_usage_metrics={True}"
        )

        task._initial_metrics_frame

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

            await task.queue_frames([LLMRunFrame()])

        @task.event_handler("on_idle_timeout")
        async def on_idle_timeout(task):
            logger.info("Conversation has been idle for 10 seconds")
            messages = [
                {
                    "role": "user",
                    "content": "The user has been idle for 0 seconds. say: Hey are you there?",
                },
            ]
            await task.queue_frame(
                LLMMessagesAppendFrame(messages=messages, run_llm=True)
            )

        @audiobuffer.event_handler("on_audio_data")
        async def on_audio_data(buffer, audio, sample_rate, num_channels):
            server_name = f"server_{call_data['call_id']}"
            await save_audio(server_name, audio, sample_rate, num_channels)

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):

            transcript_text = "\n".join(transcript_list)
            bot_metrics = metric_collector.get_metric_summary()

            logger.info(f"Client disconnected ❌❌❌")

            # Update call record with metrics data
            try:
                call = await Call.find_one({"call_sid": call_data["call_id"]})
                if call:
                    cost_collector.calculate_llm_cost(bot_metrics.get("tokens", {}).get("prompt_tokens", 0), bot_metrics.get("tokens", {}).get("completion_tokens", 0), llm_provider)
                    logger.info(f"LLM cost: {cost_collector.llm_cost}")
                    from model.model import MetricsData, CostData
                    cost_data = CostData(
                        llm_cost=cost_collector.llm_cost,
                        tts_cost=cost_collector.tts_cost,
                        stt_cost=cost_collector.stt_cost,
                        total_cost=cost_collector.total_cost
                    )
                    
                    # Create MetricsData object with collected metrics
                    metrics_data = MetricsData(
                        total_latency_ms=bot_metrics.get("total_latency", 0),
                        tts_ttfb_ms=bot_metrics.get("tts_ttfb", 0),
                        stt_ttfb_ms=bot_metrics.get("stt_ttfb", 0),
                        llm_ttfb_ms=bot_metrics.get("llm_ttfb", 0),
                        total_prompt_tokens=bot_metrics.get("tokens", {}).get("prompt_tokens", 0),
                        total_completion_tokens=bot_metrics.get("tokens", {}).get("completion_tokens", 0),
                        total_tts_characters=bot_metrics.get("tts_characters", 0),
                        total_sst_duration_ms=bot_metrics.get("stt_total_duration", 0)
                    )
                    call.cost = cost_data
                    call.metrics = metrics_data
                    call.status = CallStatus.COMPLETED
                    call.transcript = transcript_text
                    await call.save()
                    
                    logger.info(f"✅ Updated call {call_data['call_id']} with metrics data")
                    logger.info(f"📊 Metrics saved: total_latency={metrics_data.total_latency_ms}ms, "
                               f"tokens={metrics_data.total_prompt_tokens + metrics_data.total_completion_tokens}, "
                               f"tts_chars={metrics_data.total_tts_characters}")
                else:
                    logger.warning(f"Call record not found for {call_data['call_id']}")
            except Exception as e:
                logger.error(f"❌ Failed to update call with metrics: {e}")

            # Stop audio recording first to ensure file writing is complete
            try:
                await audiobuffer.stop_recording()
                logger.info(
                    f"🎬 Audio recording stopped for call {call_data['call_id']}"
                )
            except Exception as e:
                logger.warning(f"Failed to stop audio recording: {e}")

            # Add a small delay to ensure file writing is complete
            await asyncio.sleep(0.5)  # 500ms delay

            # Finalize audio recording and trigger upload
            try:
                server_name = f"server_{call_data['call_id']}"
                await finalize_audio_recording(
                    call_data["call_id"],
                    server_name,
                    transcript_text,
                    0.0,
                )
                logger.info(
                    f"🎬 Audio recording finalized for call {call_data['call_id']}"
                )
            except Exception as e:
                logger.error(f"❌ Failed to finalize audio recording: {e}")
                # Fallback to old method if finalization fails
                try:
                    asyncio.create_task(
                        delayed_background_processing(
                            call_sid=str(call_data["call_id"]),
                            transcript=str(transcript_text),
                            call_cost=0.0,
                            status="completed",
                        )
                    )
                    logger.info(
                        f"🚀 Fallback background processing started for call {call_data['call_id']}"
                    )
                except Exception as fallback_error:
                    logger.error(
                        f"❌ Fallback background processing also failed: {fallback_error}"
                    )

            await task.cancel()

        runner = PipelineRunner(handle_sigint=handle_sigint)

        await runner.run(task)
    finally:
        await session.close()


async def bot_2(runner_args, call_data=None):
    """Main bot entry point compatible with Pipecat Cloud."""

    # Import heavy components only when needed
    from pipecat.serializers.twilio import TwilioFrameSerializer
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketParams,
        FastAPIWebsocketTransport,
    )
    from pipecat.audio.vad.silero import SileroVADAnalyzer

    # Use provided call_data or parse from WebSocket
    if call_data is None:
        from pipecat.runner.utils import parse_telephony_websocket

        transport_type, call_data = await parse_telephony_websocket(
            runner_args.websocket
        )
        logger.info(f"Auto-detected transport: {transport_type}")
    else:
        logger.info(f"Using provided call_data: {call_data}")

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

    await run_bot_2(transport, handle_sigint, call_data)
