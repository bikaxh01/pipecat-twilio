from loguru import logger
import glob
import os
import asyncio




async def save_audio(
    server_name: str, audio_data: bytes, sample_rate: int, num_channels: int
):
    """Save audio data to a proper WAV file for recording purposes."""
    try:
        import aiofiles
        import os
        import struct
        from datetime import datetime

        # Create recordings directory if it doesn't exist
        recordings_dir = "recordings"
        os.makedirs(recordings_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{recordings_dir}/{server_name}_{timestamp}.wav"

        # Create proper WAV file with headers
        def create_wav_header(
            data_length, sample_rate, num_channels, bits_per_sample=16
        ):
            """Create WAV file header"""
            byte_rate = sample_rate * num_channels * bits_per_sample // 8
            block_align = num_channels * bits_per_sample // 8

            header = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF",  # ChunkID
                data_length + 36,  # ChunkSize
                b"WAVE",  # Format
                b"fmt ",  # Subchunk1ID
                16,  # Subchunk1Size
                1,  # AudioFormat (PCM)
                num_channels,  # NumChannels
                sample_rate,  # SampleRate
                byte_rate,  # ByteRate
                block_align,  # BlockAlign
                bits_per_sample,  # BitsPerSample
                b"data",  # Subchunk2ID
                data_length,  # Subchunk2Size
            )
            return header

        # Check if file exists to determine if we need to write header
        file_exists = os.path.exists(filename)

        if not file_exists:
            # Write WAV header for new file
            header = create_wav_header(len(audio_data), sample_rate, num_channels)
            async with aiofiles.open(filename, "wb") as f:
                await f.write(header)
                await f.write(audio_data)
        else:
            # Append to existing file (update file size in header)
            async with aiofiles.open(filename, "ab") as f:
                await f.write(audio_data)

            # Update the file size in the WAV header
            file_size = os.path.getsize(filename)
            async with aiofiles.open(filename, "r+b") as f:
                await f.seek(4)
                await f.write(struct.pack("<I", file_size - 8))  # Update ChunkSize
                await f.seek(40)
                await f.write(struct.pack("<I", file_size - 44))  # Update Subchunk2Size

        logger.info(
            f"Audio saved to {filename} ({len(audio_data)} bytes, {sample_rate}Hz, {num_channels}ch)"
        )

    except Exception as e:
        logger.error(f"Failed to save audio: {e}")


async def finalize_audio_recording(call_sid: str, server_name: str, transcript: str = "", call_cost: float = 0.0):
    """
    Finalize audio recording and trigger upload.
    This should be called when the call ends to ensure the recording is complete.
    
    Args:
        call_sid: The Twilio call SID
        server_name: The server name for the recording file
        transcript: The call transcript text
        call_cost: The total call cost
    """
    try:
        logger.info(f"🎬 Finalizing audio recording for call {call_sid}")
        
        # Wait for recording file to be available with retry mechanism
        recordings_dir = "recordings"
        pattern = f"{recordings_dir}/{server_name}_*.wav"
        recording_files = []
        max_retries = 10
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            recording_files = glob.glob(pattern)
            if recording_files:
                break
            logger.info(f"⏳ Waiting for recording file... attempt {attempt + 1}/{max_retries}")
            await asyncio.sleep(retry_delay)
        
        if recording_files:
            # Get the most recent file
            latest_file = max(recording_files, key=os.path.getctime)
            logger.info(f"📁 Found recording file: {latest_file}")
            
            # Import here to avoid circular imports
            from utils.post_call import process_call_completion_background
            
            # Start background processing for the completed recording
            asyncio.create_task(process_call_completion_background(
                call_sid=call_sid,
                transcript=transcript,
                call_cost=call_cost,
                status="completed"
            ))
            logger.info(f"🚀 Background processing started for completed recording: {call_sid}")
        else:
            logger.warning(f"No recording files found for call {call_sid} after {max_retries} attempts")
            
    except Exception as e:
        logger.error(f"❌ Failed to finalize audio recording: {e}")


async def upload_recording(call_sid: str, filename: str = None, audio_data: bytes = None, format: str = "wav") -> str:
    """
    Upload audio recording to Cloudinary with call_sid as filename.
    
    Args:
        call_sid (str): The Twilio call SID to use as the filename
        filename (str, optional): Path to the local audio file to upload
        audio_data (bytes, optional): Raw audio data to upload (base64 decoded)
        format (str): Audio format (default: "wav")
        
    Returns:
        str: The secure URL of the uploaded file
        
    Raises:
        Exception: If upload fails or Cloudinary configuration is missing
        
    Environment Variables Required:
        CLOUDINARY_CLOUD_NAME: Your Cloudinary cloud name
        CLOUDINARY_API_KEY: Your Cloudinary API key
        CLOUDINARY_API_SECRET: Your Cloudinary API secret
    """
    try:
        import cloudinary
        import cloudinary.uploader
        import os
        
        # Validate required environment variables
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            raise ValueError("Missing required Cloudinary environment variables: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        
        # Determine upload source
        if filename and os.path.exists(filename):
            # Upload from file
            result = cloudinary.uploader.upload(
                filename,
                folder="recordings",
                public_id=call_sid,  # Use call_sid as filename
                resource_type="video",  # Cloudinary treats audio as video resource
                overwrite=True
            )
        elif audio_data:
            # Upload from raw data
            result = cloudinary.uploader.upload(
                audio_data,
                folder="recordings",
                public_id=call_sid,  # Use call_sid as filename
                resource_type="video",  # Cloudinary treats audio as video resource
                format=format,
                overwrite=True
            )
        else:
            raise ValueError("Either filename or audio_data must be provided")
        
        # Get the secure URL
        upload_url = result.get("secure_url")
        
        logger.info(f"Successfully uploaded recording to Cloudinary: {upload_url}")
        return upload_url
        
    except Exception as e:
        logger.error(f"Failed to upload recording to Cloudinary: {e}")
        raise e