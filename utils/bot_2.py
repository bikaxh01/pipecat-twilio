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


# Cost Tracker class for bot_2
class CostTracker:
    def __init__(self):
        self.total_cost = 0.0
        self.sessions = []
        self.stt_cost = 0.0
        self.tts_cost = 0.0
        self.llm_cost = 0.0

    def calculate_llm_cost(self, input_tokens: int, output_tokens: int) -> float:
        # OpenAI GPT-4o-mini pricing per 1M tokens
        input_cost = (input_tokens / 1_000_000) * 0.15  # Input tokens
        output_cost = (output_tokens / 1_000_000) * 0.60  # Output tokens
        return input_cost + output_cost

    def calculate_stt_cost(self, audio_seconds: float) -> float:
        # Deepgram STT pricing: $0.0043 per minute (per second = $0.0043/60)
        return audio_seconds * (0.0043 / 60)

    def calculate_tts_cost(self, characters: int) -> float:
        # Sarvam TTS pricing: ₹0.0015 per character (₹1.5 per 1000 characters)
        return characters * 0.0015

    def log_llm_usage(self, input_tokens: int, output_tokens: int):
        cost = self.calculate_llm_cost(input_tokens, output_tokens)
        self.llm_cost += cost
        self.total_cost += cost

        session_data = {
            "type": "llm",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
        }
        self.sessions.append(session_data)

        return cost

    def log_stt_usage(self, audio_seconds: float):
        cost = self.calculate_stt_cost(audio_seconds)
        self.stt_cost += cost
        self.total_cost += cost

        session_data = {"type": "stt", "audio_seconds": audio_seconds, "cost": cost}
        self.sessions.append(session_data)

        return cost

    def log_tts_usage(self, characters: int):
        cost = self.calculate_tts_cost(characters)
        self.tts_cost += cost
        self.total_cost += cost

        session_data = {"type": "tts", "characters": characters, "cost": cost}
        self.sessions.append(session_data)

        return cost

    def get_final_summary(self):
        """Get final cost summary for the call."""
        llm_sessions = [s for s in self.sessions if s["type"] == "llm"]
        stt_sessions = [s for s in self.sessions if s["type"] == "stt"]
        tts_sessions = [s for s in self.sessions if s["type"] == "tts"]

        total_input_tokens = sum(s.get("input_tokens", 0) for s in llm_sessions)
        total_output_tokens = sum(s.get("output_tokens", 0) for s in llm_sessions)
        total_audio_seconds = sum(s.get("audio_seconds", 0) for s in stt_sessions)
        total_characters = sum(s.get("characters", 0) for s in tts_sessions)

        return {
            "llm": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost": self.llm_cost,
            },
            "stt": {"audio_seconds": total_audio_seconds, "cost": self.stt_cost},
            "tts": {"characters": total_characters, "cost": self.tts_cost},
            "total_cost": self.total_cost,
            "total_sessions": len(self.sessions),
        }


async def run_bot_2(
    transport,  # Will be BaseTransport when imported
    handle_sigint: bool,
    call_data: dict,
):
    logger.info(f"Starting bot")

    # Initialize cost tracker for bot_2
    cost_tracker = CostTracker()

    session = aiohttp.ClientSession()

    try:
        tts = SarvamTTSService(
            api_key=os.getenv("SARVAM_API_KEY"),
            aiohttp_session=session,
            voice_id="anushka",
            model="bulbul:v2",
            sample_rate=8000,  # Match Twilio's audio format
            params=SarvamTTSService.InputParams(
                language=Language.HI, pitch=0.0, pace=1.0, loudness=1.0
            ),
        )
        # tts = DeepgramTTSService(
        #     api_key=os.getenv("DEEPGRAM_API_KEY"),
        #     voice="aura-2-andromeda-en",
        #     sample_rate=24000,
        #     encoding="linear16",
        # )

        stt = DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            live_options=LiveOptions(
                language=Language.HI, 
                model="nova-2-general",
                sample_rate=8000,  # Match Twilio's audio format
                encoding="linear16"
            ),
        )

        # Build function schemas for tool calls
        tools_schema = ToolsSchema(
            standard_tools=[
                fs_get_nearby_clinics,
                fs_end_call,
            ]
        )

        # Create LLM service with search grounding
        # llm = GoogleLLMService(
        #     api_key=os.getenv("GOOGLE_API_KEY"),
        #     model="gemini-1.5-flash-002",
        #     system_instruction=dynamic_prompt,
        # )

        llm = OpenAILLMService(
            model="gpt-4o-mini-2024-07-18",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

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

        # Override the start_llm_usage_metrics method to capture cost data
        original_start_llm_usage_metrics = llm.start_llm_usage_metrics

        async def custom_start_llm_usage_metrics(tokens):
            cost_tracker.log_llm_usage(tokens.prompt_tokens, tokens.completion_tokens)
            return await original_start_llm_usage_metrics(tokens)

        llm.start_llm_usage_metrics = custom_start_llm_usage_metrics

        # Track STT costs through transcript updates
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
                    cost_tracker.log_stt_usage(estimated_duration)

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

        # Track TTS costs through TTS audio frames
        @tts.event_handler("on_tts_started")
        async def on_tts_started(processor, frame):
            if hasattr(frame, "text") and frame.text:
                character_count = len(frame.text)
                cost_tracker.log_tts_usage(character_count)

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
        # Final cost summary for bot_2 (in case of exceptions)
        try:
            summary = cost_tracker.get_final_summary()
            logger.info(f"💰 Bot_2 Final Call Cost Summary:")
            logger.info(
                f"   LLM - Input Tokens: {summary['llm']['input_tokens']:,}, Output Tokens: {summary['llm']['output_tokens']:,}, Cost: ${summary['llm']['cost']:.4f}"
            )
            logger.info(
                f"   STT - Audio Seconds: {summary['stt']['audio_seconds']:.2f}, Cost: ${summary['stt']['cost']:.4f}"
            )
            logger.info(
                f"   TTS - Characters: {summary['tts']['characters']:,}, Cost: ${summary['tts']['cost']:.4f}"
            )
            logger.info(f"   Total Cost: ${summary['total_cost']:.4f}")
            logger.info(f"   Total Sessions: {summary['total_sessions']}")
        except Exception as e:
            logger.warning(f"Failed to log bot_2 cost summary: {e}")

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
        transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
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
