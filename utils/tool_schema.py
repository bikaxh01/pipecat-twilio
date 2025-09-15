from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from utils.tools import get_near_by_clinic_data


async def _handle_get_nearby_clinics(params: FunctionCallParams):
    """
    Handler function for getting nearby clinic data based on pincode and/or city.
    """
    pincode = params.arguments.get("pincode")
    city = params.arguments.get("city")

    # Call the actual function
    clinic_data = await get_near_by_clinic_data(pincode=pincode, city=city)

    # Return the result through the callback
    await params.result_callback(
        {"pincode": pincode, "city": city, "clinic_data": clinic_data}
    )


from pipecat.frames.frames import EndTaskFrame, LLMMessagesAppendFrame
from pipecat.processors.frame_processor import FrameDirection


# End call
async def _handle_end_call(params: FunctionCallParams):
    """
    Handler function for ending the call.
    """
    messages = [
        {
            "role": "user",
            "content": "Response with EndCall Message: Thanks for calling, goodbye!",
        },
    ]
    await params.llm.push_frame(LLMMessagesAppendFrame(messages=messages, run_llm=True))
    await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)


# Function schema for getting nearby clinic data
fs_get_nearby_clinics = FunctionSchema(
    name="get_nearby_clinics",
    description="Get nearby clinic information based on pincode and/or city. Can search by pincode only, city only, or both. Supports fuzzy matching for city names.",
    properties={
        "pincode": {
            "type": "string",
            "description": "6-digit Indian pincode to search for clinics. Optional if city is provided.",
            "pattern": "^[1-9][0-9]{5}$",
        },
        "city": {
            "type": "string",
            "description": "City name to search for clinics. Optional if pincode is provided. Supports fuzzy matching for similar city names.",
            "minLength": 2,
            "maxLength": 50,
        },
    },
    required=[],  # At least one of pincode or city must be provided
)

# Function schema for ending the call
fs_end_call = FunctionSchema(
    name="end_call",
    description="End the current call session. Use this when the user wants to hang up or when the conversation is complete.",
    properties={},
    required=[],
)