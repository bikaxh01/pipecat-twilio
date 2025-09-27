from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse
import os
from loguru import logger

def generate_twiml(host: str, body_data: dict = None, multimodel: bool = True) -> str:
    """Generate TwiML response with WebSocket streaming using Twilio SDK."""

    websocket_url = get_websocket_url(host, multimodel)

    # Create TwiML response
    response = VoiceResponse()
    connect = Connect()
    stream = Stream(url=websocket_url)

    
    # Add body parameter (if provided)
    if body_data:
        # Pass each key-value pair as separate parameters instead of JSON string
        for key, value in body_data.items():
            stream.parameter(name=key, value=value)
            
    if not multimodel:
        agent_name = os.getenv("AGENT_NAME")
        org_name = os.getenv("ORGANIZATION_NAME")
        service_host = f"{agent_name}.{org_name}"
        logger.info(f"Service host: {service_host}")
        stream.parameter(name="_pipecatCloudServiceHost", value=service_host)

    connect.append(stream)
    response.append(connect)
    response.pause(length=20)

    return str(response)


def get_websocket_url(host: str, multimodel: bool = True) -> str:
    """Get the appropriate WebSocket URL based on environment and multimodel setting."""
    if multimodel:
        return f"wss://{host}/ws"
    else:
        return "wss://api.pipecat.daily.co/ws/twilio"


def make_twilio_call(
    to_number: str, from_number: str, twiml_url: str, status_callback_url: str = None
):
    """Make an outbound call using Twilio's REST API."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        raise ValueError("Missing Twilio credentials")

    # Create Twilio client and make the call
    client = TwilioClient(account_sid, auth_token)

    # Prepare call parameters
    call_params = {
        "to": to_number,
        "from_": from_number,
        "url": f"{twiml_url}?user_name={"Bikash"}",
        "method": "POST",
    }
    
    
    # Add status callback if provided
    if status_callback_url:
        call_params.update(
            {
                "status_callback": status_callback_url,
                "status_callback_method": "POST",
                "status_callback_event": [
                    "queued",
                    "ringing",
                    "in-progress",
                    "completed",
                    "busy",
                    "failed",
                    "no-answer",
                    "canceled",
                ],
            }
        )

    call = client.calls.create(
        **call_params,
    )

    return {"sid": call.sid, "status": call.status}
