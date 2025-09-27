import os
from datetime import datetime


import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from utils.twilio import generate_twiml, make_twilio_call
from loguru import logger

from model.model import Call, CallStatus, STTProvider, TTSProvider

load_dotenv(override=True)

# Configure file logging
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # Rotate at midnight (00:00)
    retention="30 days",  # Keep logs for 30 days
    level="DEBUG",  # Log everything from DEBUG level and above
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
    compression="zip",  # Compress old log files
)


class PromptUpdate(BaseModel):
    prompt: str
    multimodel: bool = True


class CallDetailsUpdate(BaseModel):
    timestamp: str
    call_id: str
    cost_data: dict
    total_latency_ms: float
    tts_ttfb_ms: float
    stt_ttfb_ms: float
    llm_ttfb_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tts_characters: int
    total_stt_duration_ms: float
    transcript: str


class UploadRecordingRequest(BaseModel):
    call_id: str
    audio_data: str  # base64 encoded audio file
    filename: str
    format: str
    timestamp: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    """
    Initialize database connection on application startup.
    Uses Motor async client for better performance and reliability.
    """
    from model.model import connect_to_db
    from utils.bot import initialize_heavy_components

    logger.info("🟢🟢Connecting to MongoDB")
    await connect_to_db()

    # Pre-initialize heavy bot components at startup
    logger.info("🚀 Pre-initializing bot components...")
    await initialize_heavy_components()
    logger.info("✅ Bot components ready - initialization time optimized!")


@app.on_event("shutdown")
async def shutdown_db_client():
    """
    Close database connection gracefully on application shutdown.
    This ensures proper cleanup of resources.
    """
    from model.model import close_db_connection

    logger.info("🔴 Shutting down MongoDB connection")
    await close_db_connection()


@app.get("/")
async def root():
    from utils.prompt import get_raw_prompt

    prompt = await get_raw_prompt(multimodel=False)
    return {"message": "Hello World", "result": prompt}


@app.get("/prompt")
async def prompt_ui():
    """Serve the HTML UI for editing prompts"""
    from utils.gardio_ui import create_prompt_ui

    return HTMLResponse(content=create_prompt_ui())


@app.get("/api/get-raw-prompt")
async def get_raw_prompt_api(multimodel: bool = True):
    """API endpoint to get the current raw prompt"""
    from utils.prompt import get_raw_prompt

    try:
        prompt = await get_raw_prompt(multimodel=multimodel)
        return {"prompt": prompt}
    except Exception as e:
        logger.error(f"Error getting raw prompt: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prompt")


@app.post("/api/save-prompt")
async def save_prompt_api(prompt_data: PromptUpdate):
    """API endpoint to save a new raw prompt"""
    from utils.prompt import save_raw_prompt

    if not prompt_data.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    try:
        success = await save_raw_prompt(
            prompt_data.prompt.strip(), multimodel=prompt_data.multimodel
        )
        if success:
            return {
                "message": "Prompt saved successfully",
                "prompt": prompt_data.prompt,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save prompt")
    except Exception as e:
        logger.error(f"Error saving prompt: {e}")
        raise HTTPException(status_code=500, detail="Failed to save prompt")


@app.get("/api/call-details/{call_sid}")
async def get_call_details(call_sid: str):
    """API endpoint to get call details by SID"""
    try:
        call_record = await Call.find_one({"call_sid": call_sid})
        if not call_record:
            raise HTTPException(status_code=404, detail="Call not found")

        return {
            "call_sid": call_record.call_sid,
            "status": call_record.status,
            "phone_number": call_record.phone_number,
            "name": call_record.name,
            "multimodel": call_record.multimodel,
            "recording_url": call_record.recording_url,
            "stt_provider": call_record.stt_provider,
            "tts_provider": call_record.tts_provider,
            "llm_provider": call_record.llm_provider,
            "call_cost": call_record.call_cost,
            "call_duration": call_record.call_duration,
            "transcript": call_record.transcript,
            "metrics": (
                call_record.metrics.model_dump() if call_record.metrics else None
            ),
            "cost": call_record.cost.model_dump() if call_record.cost else None,
            "created_at": (
                call_record.created_at.isoformat() if call_record.created_at else None
            ),
            "updated_at": (
                call_record.updated_at.isoformat() if call_record.updated_at else None
            ),
        }
    except Exception as e:
        logger.error(f"Error getting call details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get call details")


@app.get("/api/latest-calls")
async def get_latest_calls():
    """API endpoint to get 5 latest calls"""
    try:
        # Get 5 latest calls ordered by created_at descending
        calls = await Call.find_all().sort([("created_at", -1)]).limit(5).to_list()

        latest_calls = []
        for call_record in calls:
            latest_calls.append(
                {
                    "call_sid": call_record.call_sid,
                    "status": call_record.status,
                    "phone_number": call_record.phone_number,
                    "name": call_record.name,
                    "multimodel": call_record.multimodel,
                    "recording_url": call_record.recording_url,
                    "stt_provider": call_record.stt_provider,
                    "tts_provider": call_record.tts_provider,
                    "llm_provider": call_record.llm_provider,
                    "call_cost": call_record.call_cost,
                    "call_duration": call_record.call_duration,
                    "transcript": call_record.transcript,
                    "metrics": (
                        call_record.metrics.model_dump()
                        if call_record.metrics
                        else None
                    ),
                    "cost": call_record.cost.model_dump() if call_record.cost else None,
                    "created_at": (
                        call_record.created_at.isoformat()
                        if call_record.created_at
                        else None
                    ),
                    "updated_at": (
                        call_record.updated_at.isoformat()
                        if call_record.updated_at
                        else None
                    ),
                }
            )

        return {"calls": latest_calls}
    except Exception as e:
        logger.error(f"Error fetching latest calls: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest calls")


@app.get("/get-nearby-clinic")
async def get_nearby_clinic(pincode: str = None, city: str = None):
    """Get nearby clinic information based on pincode and/or city."""
    try:
        logger.info(
            f"Received request for nearby clinics - pincode: {pincode}, city: {city}"
        )

        # Validate that at least one parameter is provided
        if not pincode and not city:
            logger.warning("No pincode or city provided in request")
            raise HTTPException(
                status_code=400, detail="Either pincode or city parameter is required"
            )

        # Import the existing function
        from utils.tools import get_near_by_clinic_data

        # Call the existing function
        clinic_data = await get_near_by_clinic_data(pincode=pincode, city=city)

        logger.info(
            f"Successfully retrieved clinic data for pincode: {pincode}, city: {city}"
        )

        return {
            "pincode": pincode,
            "city": city,
            "clinic_data": clinic_data,
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting nearby clinic data: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get nearby clinic data: {str(e)}"
        )


@app.get("/get-dynamic-prompt")
async def get_dynamic_prompt(call_sid: str):
    """Get dynamic prompt for a specific call with multimodel=False."""
    try:
        # Validate call_sid parameter
        logger.info(f"Received request for dynamic prompt for call_sid: {call_sid}")
        if not call_sid:
            raise HTTPException(
                status_code=400, detail="call_sid parameter is required"
            )
        logger.info(f"Call SID: {call_sid}")
        # Find the call in database
        call = await Call.find_one(Call.call_sid == call_sid)
        logger.info(f"Call: {call}")
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        # Get customer name from call record, default to "there" if not set
        customer_name = call.name if call.name else "there"
        

        # Import and call create_dynamic_prompt with multimodel=False
        from utils.prompt import create_dynamic_prompt

        dynamic_prompt = await create_dynamic_prompt(
            customer_name=customer_name, multimodel=False
        )

        logger.info(
            f"Generated dynamic prompt for call {call_sid} with customer name: {customer_name}"
        )

        return {
            "call_sid": call_sid,
            "customer_name": customer_name,
            "dynamic_prompt": dynamic_prompt,
            "multimodel": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dynamic prompt for call {call_sid}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get dynamic prompt: {str(e)}"
        )


@app.post("/upload-recording")
async def upload_recording_endpoint(request: UploadRecordingRequest):
    """Upload recording to Cloudinary and save URL to database using existing upload_recording function."""
    try:
        # Validate required fields
        if not request.call_id:
            raise HTTPException(status_code=400, detail="call_id is required")

        if not request.audio_data:
            raise HTTPException(status_code=400, detail="audio_data is required")

        if not request.filename:
            raise HTTPException(status_code=400, detail="filename is required")

        # Find the call in database
        call = await Call.find_one({"call_sid": request.call_id})
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        # Decode base64 audio data
        try:
            import base64

            audio_bytes = base64.b64decode(request.audio_data)
        except Exception as e:
            logger.error(f"Failed to decode base64 audio data: {e}")
            raise HTTPException(status_code=400, detail="Invalid base64 audio data")

        # Use existing upload_recording function
        from utils.call_audio import upload_recording

        try:
            cloudinary_url = await upload_recording(
                call_sid=request.call_id, audio_data=audio_bytes, format=request.format
            )

            logger.info(
                f"Successfully uploaded recording to Cloudinary: {cloudinary_url}"
            )

        except Exception as e:
            logger.error(f"Failed to upload to Cloudinary: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to upload to Cloudinary: {str(e)}"
            )

        # Update call record with recording URL
        call.recording_url = cloudinary_url
        call.updated_at = datetime.utcnow()
        await call.save()

        logger.info(f"Successfully updated call {request.call_id} with recording URL")

        return {
            "message": "Recording uploaded successfully",
            "call_id": request.call_id,
            "recording_url": cloudinary_url,
            "filename": request.filename,
            "format": request.format,
            "timestamp": request.timestamp,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading recording: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to upload recording: {str(e)}"
        )


@app.post("/update-call-details")
async def update_call_details(call_details: CallDetailsUpdate):
    """Update call details with metrics, cost data, and transcript."""
    try:
        # Find the call by call_sid (which is call_id in the payload)
        call = await Call.find_one({"call_sid": call_details.call_id})

        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        # Parse cost data from the payload
        cost_data = call_details.cost_data
        parsed_cost_data = {
            "llm_cost": float(cost_data.get("llm_cost", "$0.0").replace("$", "")),
            "tts_cost": float(cost_data.get("tts_cost", "$0.0").replace("$", "")),
            "stt_cost": float(cost_data.get("stt_cost", "$0.0").replace("$", "")),
            "total_cost": float(cost_data.get("total_cost", "$0.0").replace("$", "")),
        }

        # Create metrics data from the payload
        metrics_data = {
            "total_latency_ms": call_details.total_latency_ms,
            "tts_ttfb_ms": call_details.tts_ttfb_ms,
            "stt_ttfb_ms": call_details.stt_ttfb_ms,
            "llm_ttfb_ms": call_details.llm_ttfb_ms,
            "total_prompt_tokens": call_details.total_prompt_tokens,
            "total_completion_tokens": call_details.total_completion_tokens,
            "total_tts_characters": call_details.total_tts_characters,
            "total_sst_duration_ms": call_details.total_stt_duration_ms,  # Note: using sst_duration_ms as per model schema
        }

        # Update the call record
        call.cost = parsed_cost_data
        call.metrics = metrics_data
        call.transcript = call_details.transcript
        call.call_cost = parsed_cost_data[
            "total_cost"
        ]  # Store total cost in the call_cost field as well
        call.updated_at = datetime.utcnow()

        await call.save()

        logger.info(
            f"Successfully updated call details for call_sid: {call_details.call_id}"
        )

        return {
            "message": "Call details updated successfully",
            "call_sid": call_details.call_id,
            "updated_fields": ["cost", "metrics", "transcript", "call_cost"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating call details: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update call details: {str(e)}"
        )


@app.post("/outbound")
async def initiate_outbound_call(request: Request) -> JSONResponse:
    """Handle outbound call request and initiate call via Twilio."""
    print("Received outbound call request")

    try:
        data = await request.json()

        # Validate request data
        if not data.get("phone_number"):
            raise HTTPException(
                status_code=400, detail="Missing 'phone_number' in the request body"
            )

        # Extract the phone number, name, multimodel setting, and providers
        phone_number = str(data["phone_number"])
        customer_name = data.get("name", "there")  # Extract name, default to "there"
        multimodel = data.get("multimodel", True)  # Extract multimodel, default to True
        stt_provider_str = data.get("stt_provider", None)
        tts_provider_str = data.get("tts_provider", None)
        llm_provider_str = data.get("llm_provider", None)

        # Map string to STTProvider enum using the utility method
        if not multimodel:
            if stt_provider_str:
                stt_provider_str = STTProvider.from_string(
                    stt_provider_str, default=STTProvider.DEEPGRAM
                )

        # Map string to TTSProvider enum using the utility method
        if tts_provider_str:
            tts_provider_str = TTSProvider.from_string(
                tts_provider_str, default=TTSProvider.CARTESIA
            )
             
        logger.info(
            f"Processing outbound call to {phone_number} for {customer_name} (multimodel: {multimodel})"
        )
        print(
            f"Processing outbound call to {phone_number} for {customer_name} (multimodel: {multimodel})"
        )

        # Extract body data if provided
        body_data = data.get("body", {})

        # Get server URL for TwiML webhook
        host = request.headers.get("host")

        if not host:
            raise HTTPException(
                status_code=400, detail="Unable to determine server host"
            )

        # Use https for production, http for localhost
        protocol = (
            "https"
            if not host.startswith("localhost") and not host.startswith("127.0.0.1")
            else "http"
        )

        # Simple TwiML URL without query parameters
        twiml_url = f"{protocol}://{host}/twiml"
        call_sid = None

        # Initiate outbound call 
        try:
            
             call_result = make_twilio_call(
                to_number=phone_number,
                from_number=os.getenv("TWILIO_PHONE_NUMBER"),
                twiml_url=twiml_url,
                status_callback_url=os.getenv("TWILIO_STATUS_CALLBACK_URL"),
             )
             call_sid = call_result["sid"]
            
             logger.info(f"Call SID: {call_sid}")
           

             await Call.insert_one(
                Call(
                    call_sid=call_sid,
                    phone_number=phone_number,
                    name=customer_name,  # Store the customer name in DB
                    multimodel=multimodel,  # Store the multimodel setting in DB
                    stt_provider=stt_provider_str,
                    tts_provider=tts_provider_str,
                    llm_provider=llm_provider_str,
                )
            )
        except Exception as e:
            print(f"Error initiating Twilio call: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to initiate call: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

    return JSONResponse(
        {
            "call_sid": call_sid,
            "status": "call_initiated",
            "phone_number": phone_number,
            "customer_name": customer_name,
        }
    )


@app.post("/inbound")
async def start_call(request: Request):
    """Handle Twilio webhook and return TwiML with WebSocket streaming."""
    print("POST TwiML")

    # Parse form data from Twilio webhook
    form_data = await request.form()

    # Extract call information
    call_sid = form_data.get("CallSid", "")
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")

    # Extract body data from query parameters and add phone numbers
    body_data = {}
    for key, value in request.query_params.items():
        body_data[key] = value

    # Always include phone numbers in body data
    body_data["from"] = from_number
    body_data["to"] = to_number

    # Log call details
    if call_sid:
        print(f"Twilio inbound call SID: {call_sid}")
        if body_data:
            print(f"Body data: {body_data}")

    # Validate environment configuration for production
    env = os.getenv("ENV", "local").lower()
    if env == "production":
        if not os.getenv("AGENT_NAME") or not os.getenv("ORGANIZATION_NAME"):
            raise HTTPException(
                status_code=500,
                detail="AGENT_NAME and ORGANIZATION_NAME must be set for production deployment",
            )

    # Get request host and construct WebSocket URL
    host = request.headers.get("host")
    if not host:
        raise HTTPException(status_code=400, detail="Unable to determine server host")

    # Generate TwiML response (body_data always contains phone numbers)
    # For inbound calls, default to multimodel=True
    twiml_content = generate_twiml(host, body_data, multimodel=True)

    return HTMLResponse(content=twiml_content, media_type="application/xml")


@app.post("/twiml")
async def get_twiml(request: Request) -> HTMLResponse:
    """Return TwiML instructions for connecting call to WebSocket."""
    print("Serving TwiML for outbound call")

    # Parse form data from Twilio webhook
    form_data = await request.form()
  
    # Extract call information
    call_sid = form_data.get("CallSid", "")
    
    # Retrieve call data from database instead of in-memory store
    body_data = {}
    multimodel = True  # Default to True
    if call_sid:
        try:
            call_record = await Call.find_one({"call_sid": call_sid})
            if call_record:
                if call_record.name:
                    body_data["name"] = call_record.name
                    logger.info(
                        f"Retrieved name from database for TwiML: {call_record.name}"
                    )
                # Check multimodel setting
                multimodel = call_record.multimodel
                logger.info(f"Multimodel setting for call {call_sid}: {multimodel}")
        except Exception as e:
            logger.warning(f"Failed to retrieve call data from database: {e}")
            body_data = {}

    try:
        # Get the server host to construct WebSocket URL
        host = request.headers.get("host")
        if not host:
            raise HTTPException(
                status_code=400, detail="Unable to determine server host"
            )

        # Generate TwiML with body data parameter and multimodel-specific WebSocket endpoint
        twiml_content = generate_twiml(host, body_data, multimodel)
        logger.info(f"TwiML content: {twiml_content}")
        return HTMLResponse(content=twiml_content, media_type="application/xml")

    except Exception as e:
        print(f"Error generating TwiML: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate TwiML: {str(e)}"
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connection from Twilio Media Streams."""
    await websocket.accept()
    print("WebSocket connection accepted for outbound call")
    from utils.bot_2 import bot_2

    try:
        # Import the bot function from the bot module
        from utils.bot import bot
        from pipecat.runner.types import WebSocketRunnerArguments

        # Create runner arguments and run the bot
        runner_args = WebSocketRunnerArguments(websocket=websocket)
        runner_args.handle_sigint = False

        await bot(runner_args)

    except Exception as e:
        print(f"Error in WebSocket endpoint: {e}")
        await websocket.close()


@app.websocket("/ws2")
async def websocket_endpoint_2(websocket: WebSocket):
    """Handle WebSocket connection from Twilio Media Streams for non-multimodel calls."""
    await websocket.accept()
    print("WebSocket connection accepted for non-multimodel call")

    try:
        # Import the bot_2 function for non-multimodel calls
        from utils.bot_2 import bot_2
        from pipecat.runner.types import WebSocketRunnerArguments

        # Create runner arguments and run the bot_2
        runner_args = WebSocketRunnerArguments(websocket=websocket)
        runner_args.handle_sigint = False

        await bot_2(runner_args)

    except Exception as e:
        print(f"Error in WebSocket endpoint 2: {e}")
        await websocket.close()


@app.post("/twilio-status-callback")
async def twilio_status_callback(request: Request):
    """Handle Twilio status callback."""
    try:
        print("Twilio status callback received")

        # Parse form data from Twilio status callback
        form_data = await request.form()

        # Extract call information
        call_sid = form_data.get("CallSid", "")
        call_status = form_data.get("CallStatus", "")
        call_duration = form_data.get("CallDuration", "")

        print(f"Twilio status callback call SID: {call_sid}")
        print(f"Twilio status callback status: {call_status}")
        print(f"Call duration: {call_duration}")

        # Update call status and duration in database if call_sid exists
        if call_sid:
            try:
                call = await Call.find_one({"call_sid": call_sid})
                if call:
                    # Map Twilio status to our internal status
                    status_mapping = {
                        "ringing": CallStatus.RINGING,
                        "in-progress": CallStatus.IN_PROGRESS,
                        "completed": CallStatus.COMPLETED,
                        "busy": CallStatus.BUSY,
                        "failed": CallStatus.FAILED,
                        "no-answer": CallStatus.NO_ANSWER,
                        "canceled": CallStatus.CANCELED,
                    }

                    if call_status in status_mapping:
                        call.status = status_mapping[call_status]

                    # Store call duration if provided (in seconds)
                    if call_duration and call_duration.isdigit():
                        call.call_duration = int(call_duration)
                        print(
                            f"Updated call {call_sid} duration to {call.call_duration} seconds"
                        )

                    # Update the updated_at timestamp
                    call.updated_at = datetime.utcnow()

                    await call.save()
                    print(f"Updated call {call_sid} status to {call.status}")
            except Exception as e:
                print(f"Error updating call status in database: {e}")

        return JSONResponse(content={"message": "Twilio status callback received"})

    except Exception as e:
        print(f"Error processing Twilio status callback: {e}")
        return JSONResponse(
            content={"error": "Failed to process status callback"}, status_code=500
        )


if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", "8000"))

    print(f"Starting Twilio outbound chatbot server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
