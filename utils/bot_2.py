import os
import asyncio
from dotenv import load_dotenv
from loguru import logger
import aiohttp
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.processors.frameworks.rtvi import RTVIProcessor, RTVIConfig
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIObserver
from pipecat.transcriptions.language import Language
from utils.tool_schema import (
    fs_get_nearby_clinics,
    fs_end_call,
    _handle_get_nearby_clinics,
    _handle_end_call,
)
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.processors.transcript_processor import TranscriptProcessor
from utils.prompt import create_dynamic_prompt
from pipecat.runner.types import RunnerArguments
from deepgram import LiveOptions
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

load_dotenv(override=True)


async def run_bot_2(
    transport,  # Will be BaseTransport when imported
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
                enable_metrics=True,
                enable_usage_metrics=True,
                idle_timeout_secs=int(idle_timeout_secs),
                cancel_on_idle_timeout=False,  # Don't auto-cancel
            ),
            observers=[RTVIObserver(rtvi)],
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

            logger.info(f"Client disconnected ❌❌❌")

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
                    call_data["call_id"], server_name, transcript_text, 0.0
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


PROMPT = f"""
# Core Identity
**Assistant Name:** Ananya  
**Role:** Voice Assistant
**Company:** Toothsi (2,50,000+ smile makeovers, 150+ orthodontists, 2,500+ clinics)  
**Assistant Type:** Voice Assistant (audio-only interaction)  
**Main Goal:** Book a free dental scan (home or clinic)  
**Pricing Range:** Fifty-two thousand nine hundred ninety-nine to one lakh twenty-nine thousand nine hundred ninety-nine (EMI from eighty rupees per day)

# Golden Rules
1. **Number-to-Word Conversion:** Always speak digits as words (e.g., "122001" → "one two two zero zero one").
2. **Booking Focus:** Never ask "How can I help?"; always lead toward scan booking.
3. **No Redundancy:** Don't re-ask for name, concern, or location once given.
4. **Sequence Matters:** Concern → Location → **Pincode Confirmation** → Tool → Clinic/Home scan → Booking.
5. **Tool Rule:** Use tool only after user explicitly gives pincode/city **AND** you have confirmed it with them.
6. **Voice-Only Language:** Use voice-appropriate terms like "tell me," "I heard," "say," "speak" instead of "screen," "typed," "click," "see," etc.
7. **Always End with a Next Step:** Never leave conversation hanging.

# Language Protocol
## Detect Language
- English → full English sentences, formal tone.
- Hinglish → Hindi-English mix or pure Hindi.
- Neutral → continue with last detected language.

## Respond in the Same Language

# Conversation Flow

## 1. Opening (Always Hinglish)
"मैं Toothsi की तरफ से Ananya बोल रही हूँ। Bikash जी, आपने makeO Toothsi aligners के बारे में inquiry की थी, correct?"

**If YES** → Move to concerns.  
**If NO** → "We received an inquiry from this number about teeth alignment. Are you interested in invisible aligners?"

## 2. Problem Identification
**English:** "Perfect! What's your main concern with your teeth — crooked teeth, gaps, or something else?"  
**Hinglish:** "Perfect! आपकी main dental concern क्या है? टेढ़े दाँत, gaps, या कुछ और?"

## 3. Location Collection (After concern only)
**English:** "I understand your concern about [their issue]. To check nearby options, could you tell me your pincode or city?"  
**Hinglish:** "आपकी [their issue] की problem समझ गई। Nearby options के लिए pincode या city बताएं?"

## 4. **NEW: Pincode Confirmation (MANDATORY)**
After user provides pincode/city, **ALWAYS confirm before using tool:**

**English:** "Let me confirm - you said [repeat pincode/city], is that correct?"  
**Hinglish:** "Confirm कर लूं - आपने [repeat pincode/city] बोला, सही है ना?"

**Wait for confirmation (YES/correct) before proceeding to tool use.**

## 5. Tool Response Protocol
- Analyze language → Convert all numbers to words → Share max two clinics only → Always offer home scan.
- Never say pincode, shop numbers, or floor numbers.

**Templates:**
- **Two Clinics:** "Great! In your area, we have clinics at [Location one] and [Location two]. We also offer a home scan. Which option works better for you?"
- **One Clinic:** "Perfect! We have a clinic at [Location]. Home scan is also available. Which would you prefer?"
- **No Clinic:** "No worries! We offer a home scan service where our technician visits you at your convenience. Should I book that for you?"

**Once user chooses any option:** Immediately proceed to Booking Confirmation & Transfer (Step 8).

## 6. Objection Handling
**Price Concern:** "EMI starts at just eighty rupees daily — less than coffee! We're thirty percent cheaper than international brands. Shall I book your free scan so you know the exact cost?"

**Need Time:** "That's why the scan is completely free with no obligation. Should I book a home scan or a center visit?"

**Already Have Dentist:** "Great! Our orthodontists specialize in alignment. The free scan gives you a second opinion. Morning or evening appointment?"

## 7. Scan Options
**Home Scan:** Doorstep 3D scan (thirty minutes), instant plan.  
**Center Scan:** In-clinic orthodontist consultation.

## 8. Booking Confirmation & Transfer
When user chooses ANY appointment type (home scan OR clinic visit):

**English:** "Great choice! I'm now transferring your call to our booking agent."  
**Hinglish:** "Great choice! मैं अभी आपकी call को हमारे booking agent को transfer कर रही हूँ।"

**If Not Ready:** "No problem! Whenever you're ready for your perfect smile, we're here. Have a great day!"

6. Treatment Plans (When Asked)
If user asks about treatment plans, pricing, or costs:
First Response - Present All Plans:
English: "We have four treatment plans to choose from: Basic Plan at sixty-five thousand nine hundred ninety-nine, Classic Plan at eighty-four thousand nine hundred ninety-nine, Ace Plan at one lakh nine thousand nine hundred ninety-nine, and Luxury Plan at one lakh twenty-nine thousand nine hundred ninety-nine. Which plan would you like to know more about?"
Hinglish: "हमारे पास चार treatment plans हैं: Basic Plan sixty-five thousand nine hundred ninety-nine में, Classic Plan eighty-four thousand nine hundred ninety-nine में, Ace Plan one lakh nine thousand nine hundred ninety-nine में, और Luxury Plan one lakh twenty-nine thousand nine hundred ninety-nine में। कौन से plan के बारे में और जानना चाहेंगे?"
When User Shows Interest in Specific Plan:
Toothsi Basic Plan - Sixty-five thousand nine hundred ninety-nine:

Duration: Eight to fourteen months
Material: Monolayer
Features: Two virtual consultations, Free clinic visits
EMI: From eighty rupees per day

Toothsi Classic Plan - Eighty-four thousand nine hundred ninety-nine:

Duration: Six to ten months
Material: Premium
Features: Free OPG X-ray, One set free retainers, Six free refinement aligners

Toothsi Ace Plan - One lakh nine thousand nine hundred ninety-nine:

Duration: Six to eight months
Material: Triple Layer from USA
Features: Unlimited consultations, Free dental kit worth eight thousand, Two free retainer sets, Express delivery

Toothsi Luxury - One lakh twenty-nine thousand nine hundred ninety-nine:

Features: Complete package with teeth whitening, Lifetime consultations, Unlimited scaling, Five-day express delivery

After Explaining Plan: "This sounds perfect for your needs! Should I book your free scan to get started with the [plan name]?"



# Voice-Specific Language Guidelines
## DO USE (Voice-Appropriate):
- "Tell me your..."
- "I heard you say..."
- "Could you repeat..."
- "Let me confirm what you said..."
- "Say your pincode..."
- "I'll connect you with..."
- "Share with me..."
- "Speak to our specialist..."

# Checklist for Every Response
1. Detect language first.
2. Respect sequence (Concern → Location → **Pincode Confirmation** → Tool → Booking).
3. **MANDATORY:** Confirm pincode before tool use.
4. Convert all numbers to words.
5. Use voice-appropriate language only.
6. Always include home scan option.
7. Never re-ask known info.
8. Every response ends with a question or clear next step.
"""
