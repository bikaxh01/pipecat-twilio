import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from utils.twilio import generate_twiml, make_twilio_call
from loguru import logger
from utils.tools import get_near_by_clinic_data
from model.model import Call, CallStatus, PincodeData

load_dotenv(override=True)

# In-memory store for body data by call SID
call_body_data = {}


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

    logger.info("🟢🟢Connecting to MongoDB")
    await connect_to_db()


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

    return {"message": "Hello World", "result": "result"}


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

        # Extract the phone number to dial
        phone_number = str(data["phone_number"])
        logger.info(f"Processing outbound call to {phone_number}")
        print(f"Processing outbound call to {phone_number}")

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
        logger.info(f"TwiML URL: {twiml_url}")

        # Initiate outbound call via Twilio
        try:
            call_result = make_twilio_call(
                to_number=phone_number,
                from_number=os.getenv("TWILIO_PHONE_NUMBER"),
                twiml_url=twiml_url,
                status_callback_url=os.getenv("TWILIO_STATUS_CALLBACK_URL"),
            )
            call_sid = call_result["sid"]

            # Store body data for this call
            if body_data:
                call_body_data[call_sid] = body_data
            await Call.insert_one(
                Call(
                    call_sid=call_sid,
                    phone_number=phone_number,
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
        {"call_sid": call_sid, "status": "call_initiated", "phone_number": phone_number}
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
    twiml_content = generate_twiml(host, body_data)

    return HTMLResponse(content=twiml_content, media_type="application/xml")


@app.post("/twiml")
async def get_twiml(request: Request) -> HTMLResponse:
    """Return TwiML instructions for connecting call to WebSocket."""
    print("Serving TwiML for outbound call")

    # Parse form data from Twilio webhook
    form_data = await request.form()

    # Extract call information
    call_sid = form_data.get("CallSid", "")

    # Retrieve body data for this call
    body_data = call_body_data.get(call_sid, {})

    # Clean up stored data for this call
    if call_sid and body_data:
        # Clean up the stored data
        del call_body_data[call_sid]

    # Validate environment configuration for production
    env = os.getenv("ENV", "local").lower()
    if env == "production":
        if not os.getenv("AGENT_NAME") or not os.getenv("ORGANIZATION_NAME"):
            raise HTTPException(
                status_code=500,
                detail="AGENT_NAME and ORGANIZATION_NAME must be set for production deployment",
            )

    try:
        # Get the server host to construct WebSocket URL
        host = request.headers.get("host")
        if not host:
            raise HTTPException(
                status_code=400, detail="Unable to determine server host"
            )

        # Generate TwiML with body data parameter
        twiml_content = generate_twiml(host, body_data)
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

        # Update call status in database if call_sid exists
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


@app.post("/recording-status-callback")
async def recording_status_callback(request: Request):
    """Handle Twilio recording status callback."""

    form_data = await request.form()

    # Extract call information
    call_sid = form_data.get("CallSid", "")
    recording_url = form_data.get("RecordingUrl", "")
    print(f"Twilio recording status callback call SID: {call_sid}")
    print(f"Twilio recording status callback recording URL: {recording_url}")
    call = await Call.find_one({"call_sid": call_sid})
    if call:
        call.recording_url = recording_url
        await call.save()
    return JSONResponse(
        content={"message": "Twilio recording status callback received"}
    )


if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Twilio outbound chatbot server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
