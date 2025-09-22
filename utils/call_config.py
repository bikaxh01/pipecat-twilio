from aiohttp import ClientSession
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.services.gladia.config import LanguageConfig




def get_stt_service_config(stt_provider: str):
    """
    Returns STT service configuration based on provider.

    Args:
        stt_provider: STT provider name from STTProvider enum

    Returns:
        dict: Configuration dictionary for the STT service
    """
    import os
    from pipecat.transcriptions.language import Language
    from deepgram import LiveOptions

    # Convert string to STTProvider enum if needed
    if isinstance(stt_provider, str):
        from model.model import STTProvider

        language = Language.HI
        provider_enum = STTProvider.from_string(stt_provider, STTProvider.DEEPGRAM)
    else:
        provider_enum = stt_provider

    # Switch case for each STT provider
    if provider_enum == STTProvider.DEEPGRAM:
        return DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            live_options=LiveOptions(
                language=language,
                model="nova-2-general",
                sample_rate=8000,  # Match Twilio's audio format
                encoding="linear16",
            ),
        )

    elif provider_enum == STTProvider.GOOGLE:
        return GoogleSTTService(
            credentials_path=os.getenv("GOOGLE_STT_CREDENTIALS_PATH"),
            params=GoogleSTTService.InputParams(
                languages=language,
                model="telephony",
                sample_rate=8000,
                enable_automatic_punctuation=True,
                enable_interim_results=True,
            ),
        )
    elif provider_enum == STTProvider.AZURE:
        from pipecat.services.azure.stt import AzureSTTService

        return AzureSTTService(
            api_key=os.getenv("AZURE_SPEECH_API_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION"),
            sample_rate=8000,
            language=language,
        )

    elif provider_enum == STTProvider.AWS_TRANSCRIBE:
        from pipecat.services.aws.stt import AWSTranscribeSTTService

        return AWSTranscribeSTTService(
            sample_rate=8000,
            aws_access_key_id="YOUR_ACCESS_KEY_ID",
            api_key="YOUR_SECRET_ACCESS_KEY",
            aws_session_token="YOUR_SESSION_TOKEN",  # If using temporary credentials
            language=language,
        )
    elif provider_enum == STTProvider.GLADIA:
        from pipecat.services.gladia.stt import GladiaSTTService
        from pipecat.services.gladia.config import GladiaInputParams, LanguageConfig

        return GladiaSTTService(
            api_key=os.getenv("GLADIA_API_KEY"),
            params=GladiaInputParams(
                language_config=LanguageConfig(
                    languages=[language],
                    code_switching=True,
                )
            ),
        )

    elif provider_enum == STTProvider.SONIOX:
        from pipecat.services.soniox.stt import SonioxSTTService, SonioxInputParams

        return SonioxSTTService(
            api_key=os.getenv("SONIOX_API_KEY"),
            sample_rate=8000,
            params=SonioxInputParams(
                language_hints=[Language.EN, language],
            ),
        )

    elif provider_enum == STTProvider.CARTESIA:
        from pipecat.services.cartesia.stt import (
            CartesiaSTTService,
            CartesiaLiveOptions,
        )

        return CartesiaSTTService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            live_options=CartesiaLiveOptions(
                model="ink-whisper",
                language=language,
                sample_rate=8000,
            ),
        )
    elif provider_enum == STTProvider.GROQ:
        from pipecat.services.groq.stt import GroqSTTService

        return GroqSTTService(api_key=os.getenv("GROQ_API_KEY"), language=language)

    elif provider_enum == STTProvider.FAL_WIZPER:
        from pipecat.services.fal.stt import FalSTTService

        return FalSTTService(
            api_key=os.getenv("FAL_KEY"),
            sample_rate=8000,
            params=FalSTTService.InputParams(language=language),
        )

    else:
        # Default fallback to Deepgram
        return DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            live_options=LiveOptions(
                language=language,
                model="nova-2-general",
                sample_rate=8000,  # Match Twilio's audio format
                encoding="linear16",
            ),
        )




async def get_providers_from_call(call_sid: str):
    """
    Get STT, TTS, and LLM providers from a single database call.
    
    Args:
        call_sid: Call SID to look up
        
    Returns:
        tuple: (stt_provider, tts_provider, llm_provider) or defaults if call not found
    """
    from model.model import Call, STTProvider, TTSProvider
    
    call = await Call.find_one({"call_sid": call_sid})
    if call:
        stt_provider = call.stt_provider or STTProvider.DEEPGRAM
        tts_provider = call.tts_provider or TTSProvider.SARVAM_AI
        llm_provider = call.llm_provider or "openai"
        return stt_provider, tts_provider, llm_provider
    return STTProvider.DEEPGRAM, TTSProvider.SARVAM_AI, "openai"


def get_tts_service_config(tts_provider: str, session: ClientSession):
    """
    Returns TTS service configuration based on provider.

    Args:
        tts_provider: TTS provider name from TTSProvider enum

    Returns:
        dict: Configuration dictionary for the TTS service
    """
    import os
    from model.model import TTSProvider
    from pipecat.transcriptions.language import Language

    # Convert string to TTSProvider enum if needed
    language = Language.HI
    if isinstance(tts_provider, str):
        provider_enum = TTSProvider.from_string(tts_provider, TTSProvider.SARVAM_AI)
    else:
        provider_enum = tts_provider

    # Switch case for each TTS provider
    if provider_enum == TTSProvider.CARTESIA:
        from pipecat.services.cartesia.tts import CartesiaTTSService

        return CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id=os.getenv("CARTESIA_VOICE_ID"),
            sample_rate=8000,
            model="sonic-2",
            params=CartesiaTTSService.InputParams(language=language, speed="normal"),
        )

    elif provider_enum == TTSProvider.ELEVENLABS:
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

        return ElevenLabsTTSService(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
            model="eleven_flash_v2_5",
            sample_rate=8000,
            params=ElevenLabsTTSService.InputParams(
                language=language,
                stability=0.7,
                similarity_boost=0.8,
                style=0.5,
                use_speaker_boost=True,
                speed=1.1,
            ),
        )

    elif provider_enum == TTSProvider.SARVAM_AI:
        from pipecat.services.sarvam.tts import SarvamTTSService

        return SarvamTTSService(
            api_key=os.getenv("SARVAM_API_KEY"),
            aiohttp_session=session,
            sample_rate=8000,  # Match Twilio's audio format
            params=SarvamTTSService.InputParams(
                language=language, pitch=0.0, pace=1.0, loudness=1.0
            ),
        )

    else:
        # Default fallback
        return SarvamTTSService(
            api_key=os.getenv("SARVAM_API_KEY"),
            aiohttp_session=session,
            
            sample_rate=8000,  # Match Twilio's audio format
            params=SarvamTTSService.InputParams(
                language=language, pitch=0.0, pace=1.0, loudness=1.0
            ),
        )


def get_llm_service_config(llm_provider: str):
    """
    Returns LLM service configuration based on provider.

    Args:
        llm_provider: LLM provider string in format "provider/model" (e.g., "openai/gpt-4o", "gemini/gemini-1.5-flash")

    Returns:
        LLM service instance
    """
    import os
    from pipecat.services.google.llm import GoogleLLMService
    from pipecat.services.openai.llm import OpenAILLMService
    from loguru import logger
    # Split the provider string by "/" to get provider and model
    if llm_provider and "/" in llm_provider:
        provider_part, model_part = llm_provider.split("/", 1)
        provider_lower = provider_part.lower().strip()
        logger.info(f"Provider part: 🟢{provider_lower}")
        logger.info(f"Model part:🟢 {model_part}")
        model = model_part.strip()
    else:
        # Fallback to old format or default
        provider_lower = llm_provider.lower() if llm_provider else ""
        model = None

    if provider_lower == "gemini":
        # Use provided model or default
        model_to_use = model if model else "gemini-1.5-flash-002"
        return GoogleLLMService(
            api_key=os.getenv("GOOGLE_API_KEY"),
            model=model_to_use,
        )
    elif provider_lower == "openai":
        # Use provided model or default
        model_to_use = model if model else "gpt-4o-mini-2024-07-18"
        return OpenAILLMService(
            model=model_to_use,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    else:
        # Default fallback to OpenAI
        return OpenAILLMService(
            model="gpt-4o-mini-2024-07-18",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    