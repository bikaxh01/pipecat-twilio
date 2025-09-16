import asyncio
import os
import glob
import json
from loguru import logger
from model.model import Call, CallStatus
from utils.call_audio import upload_recording
import aiohttp


async def process_call_completion_background(
    call_sid: str, 
    transcript: str, 
    call_cost: float,
    status: str = "completed"
):
    """
    Background task to handle post-call processing including:
    - Uploading audio recording to Cloudinary
    - Saving transcript to database
    - Updating call status and cost
    """
    try:
        # Ensure all parameters are the correct type
        call_sid = str(call_sid)
        transcript = str(transcript) if transcript else ""
        call_cost = float(call_cost) if call_cost is not None else 0.0
        status = str(status)
        
        logger.info(f"🔄 Starting background processing for call {call_sid}")
        logger.info(f"📝 Received transcript: {transcript[:100]}..." if transcript else "📝 No transcript provided")
        logger.info(f"💰 Received call cost: {call_cost}")
        
        # Find the call record in database
        call = await Call.find_one({"call_sid": call_sid})
        if not call:
            logger.error(f"Call record not found for SID: {call_sid}")
            return
        
        # Update call status and cost (only if values are provided)
        call.status = status
        if call_cost > 0:
            call.call_cost = round(call_cost, 2)
            logger.info(f"💰 Updated call cost to: {call.call_cost}")
        if transcript:
            call.transcript = transcript
            logger.info(f"📝 Updated transcript (length: {len(transcript)} chars)")
        
        # If transcript or cost are not provided, we'll update them later
        # This allows the upload to proceed even if these values aren't available yet
        
        # Find and upload recording file
        server_name = f"server_{call_sid}"
        recordings_dir = "recordings"
        
        # Find the most recent recording file for this call
        pattern = f"{recordings_dir}/{server_name}_*.wav"
        recording_files = glob.glob(pattern)
        
        if recording_files:
            # Get the most recent file
            latest_file = max(recording_files, key=os.path.getctime)
            try:
                logger.info(f"📤 Uploading recording: {latest_file}")
                # Upload to Cloudinary
                upload_url = await upload_recording(call_sid, latest_file)
                call.recording_url = upload_url
                logger.info(f"✅ Recording uploaded to Cloudinary: {upload_url}")
                
                # Clean up local file after successful upload
                try:
                    # os.remove(latest_file)
                    logger.info(f"🗑️ Cleaned up local file: {latest_file}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up local file: {cleanup_error}")
                    
            except Exception as upload_error:
                logger.error(f"❌ Failed to upload recording to Cloudinary: {upload_error}")
        else:
            logger.warning(f"No recording files found for call {call_sid}")
        
        # Save all updates to database
        await call.save()
        logger.info(f"✅ Background processing completed for call {call_sid}")
        
        # Send webhook to update the call status
        await call_completion_webhook(call_sid, status)
    except Exception as e:
        logger.error(f"❌ Error in background processing for call {call_sid}: {e}")



async def call_completion_webhook(call_sid: str, status: str):
    """
    Send call completion webhook with call status, transcript, and recording URL.
    
    Args:
        call_sid: The Twilio call SID
        status: The call status to send in the webhook
    """
    try:
        # Get webhook URL from environment variables
        webhook_url = os.getenv("CALL_COMPLETION_WEBHOOK_URL")
        logger.info(f"Call completion webhook URL 🟢🟢🟢: {webhook_url}")
        if not webhook_url:
            logger.warning("CALL_COMPLETION_WEBHOOK_URL not set in environment variables")
            return
        
        # Fetch call data from database
        call = await Call.find_one({"call_sid": call_sid})
        if not call:
            logger.error(f"Call record not found for SID: {call_sid}")
            return
        
        # Prepare webhook payload
        webhook_payload = {
            "call_sid": call_sid,
            "status": status,
            "phone_number": call.phone_number,
            "name": call.name,
            "transcript": call.transcript or "",
            "recording_url": call.recording_url or "",
            "call_cost": call.call_cost or 0.0,
            "created_at": call.created_at.isoformat() if call.created_at else None,
            "updated_at": call.updated_at.isoformat() if call.updated_at else None
        }
        
        logger.info(f"📤 Sending webhook for call {call_sid} to {webhook_url}")
        
        # Make POST request to webhook URL
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=webhook_payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)  # 30 second timeout
            ) as response:
                if response.status == 200:
                    logger.info(f"✅ Webhook sent successfully for call {call_sid}")
                else:
                    response_text = await response.text()
                    logger.error(f"❌ Webhook failed for call {call_sid}. Status: {response.status}, Response: {response_text}")
                    
    except aiohttp.ClientError as e:
        logger.error(f"❌ HTTP error sending webhook for call {call_sid}: {e}")
    except Exception as e:
        logger.error(f"❌ Error sending webhook for call {call_sid}: {e}")


def start_background_task(call_sid: str, transcript: str, call_cost: float, status: str = "completed"):
    """
    Start background task for post-call processing.
    This function can be called from the main thread without blocking.
    """
    try:
        # Create and schedule the background task
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a task
            asyncio.create_task(process_call_completion_background(call_sid, transcript, call_cost, status))
        else:
            # If we're not in an async context, run in a new event loop
            asyncio.run(process_call_completion_background(call_sid, transcript, call_cost, status))
    except Exception as e:
        logger.error(f"❌ Failed to start background task: {e}")


async def delayed_background_processing(call_sid: str, transcript: str, call_cost: float, status: str = "completed"):
    """
    Delayed background processing with a small delay to ensure pipeline cleanup completes first.
    """
    logger.info(f"⏳ Waiting 1 second before starting background processing for call {call_sid}")
    await asyncio.sleep(1.0)  # 1 second delay
    logger.info(f"🚀 Starting delayed background processing for call {call_sid}")
    await process_call_completion_background(
        call_sid=call_sid,
        transcript=transcript,
        call_cost=call_cost,
        status=status
    )
