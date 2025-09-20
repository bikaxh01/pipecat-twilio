from typing import Optional, List
from pydantic import Field, BaseModel
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from enum import Enum
from beanie import Document, Link, init_beanie
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()
import os
from loguru import logger

# Get MongoDB URI and database name from environment variables
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "toothsi-v2")  # Default to "toothsi" if not set

# Global client variable to store the Motor client
client: Optional[AsyncIOMotorClient] = None


class CallStatus(str, Enum):
    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BUSY = "busy"
    FAILED = "failed"
    NO_ANSWER = "no-answer"
    CANCELED = "canceled"


class STTProvider(str, Enum):
    """Speech-to-Text provider options"""

    AWS_TRANSCRIBE = "aws_transcribe"
    AZURE = "azure"
    CARTESIA = "cartesia"
    DEEPGRAM = "deepgram"
    FAL_WIZPER = "fal_wizper"
    GLADIA = "gladia"
    GOOGLE = "google"
    SONIOX = "soniox"
    GROQ = "groq"

    @classmethod
    def from_string(
        cls, value: str, default: "STTProvider" = None
    ) -> Optional["STTProvider"]:
        """
        Convert string to STTProvider enum with fallback options.

        Args:
            value: String value to convert
            default: Default value to return if conversion fails

        Returns:
            STTProvider enum or None if conversion fails and no default provided
        """
        if not value:
            return default

        # Method 1: Direct mapping by value
        try:
            return cls(value)
        except ValueError:
            pass

        # Method 2: Case-insensitive mapping
        value_lower = value.lower()
        for provider in cls:
            if provider.value.lower() == value_lower:
                return provider

        # Method 3: Partial matching (e.g., "google" matches "GOOGLE")
        for provider in cls:
            if provider.name.lower() == value_lower:
                return provider

        return default


class TTSProvider(str, Enum):
    """Text-to-Speech provider options"""

    CARTESIA = "cartesia"

    ELEVENLABS = "elevenlabs"

    SARVAM_AI = "sarvam_ai"

    @classmethod
    def from_string(
        cls, value: str, default: "TTSProvider" = None
    ) -> Optional["TTSProvider"]:
        """
        Convert string to TTSProvider enum with fallback options.

        Args:
            value: String value to convert
            default: Default value to return if conversion fails

        Returns:
            TTSProvider enum or None if conversion fails and no default provided
        """
        if not value:
            return default

        # Method 1: Direct mapping by value
        try:
            return cls(value)
        except ValueError:
            pass

        # Method 2: Case-insensitive mapping
        value_lower = value.lower()
        for provider in cls:
            if provider.value.lower() == value_lower:
                return provider

        # Method 3: Partial matching (e.g., "google" matches "GOOGLE")
        for provider in cls:
            if provider.name.lower() == value_lower:
                return provider

        return default





class organization(Document):
    prompt: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PincodeData(Document):
    pincode: str
    home_scan: str
    clinic_1: Optional[str] = None
    clinic_2: Optional[str] = None
    city: str


class Call(Document):
    call_sid: str
    status: CallStatus = CallStatus.RINGING
    phone_number: str
    name: Optional[str] = None  # Add name field for dynamic prompts
    multimodel: bool = True  # Add multimodel field with default value True
    recording_url: Optional[str] = None
    stt_provider: Optional[STTProvider] = None
    tts_provider: Optional[TTSProvider] = None
    llm_provider: Optional[str] = None  # LLM provider (gemini or openai)
    call_cost: Optional[float] = None
    call_duration: Optional[int] = None  # Call duration in seconds
    transcript: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


async def connect_to_db():
    """
    Connect to MongoDB using Motor async client and initialize Beanie ODM.
    This function handles connection establishment and error handling.
    """
    global client

    try:
        # Validate environment variables
        if not MONGO_URI:
            raise ValueError("MONGO_URI is not set in environment variables")

        logger.info("🟢🟢Connecting to MongoDB using Motor...")

        # Create Motor async client with optimized connection parameters
        client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=2000,  # Reduced from 5000
            connectTimeoutMS=5000,  # Reduced from 10000
            socketTimeoutMS=10000,  # Reduced from 20000
            maxPoolSize=20,  # Increased from 10
            minPoolSize=5,  # Increased from 1
            maxIdleTimeMS=30000,  # Add idle timeout
            retryWrites=True,  # Enable retryable writes
            retryReads=True,  # Enable retryable reads
        )

        # Test the connection with a ping command
        await client.admin.command("ping")

        # Get the database instance
        database = client[DB_NAME]

        # Initialize Beanie with the Motor database and document models
        await init_beanie(
            database=database,
            document_models=[
                Call,
                PincodeData,
                organization,
            ],
        )

        logger.info("✅ Successfully connected to MongoDB using Motor")

    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {str(e)}")
        # Close the client if it was created
        if client:
            client.close()
        raise e


async def close_db_connection():
    """
    Close the MongoDB connection gracefully.
    This function should be called when the application shuts down.
    """
    global client

    if client:
        logger.info("🔴 Closing MongoDB connection...")
        client.close()
        logger.info("✅ MongoDB connection closed")


def get_database():
    """
    Get the database instance for direct operations if needed.
    Returns the database instance from the global client.
    """
    global client

    if not client:
        raise RuntimeError("Database not connected. Call connect_to_db() first.")

    return client[DB_NAME]
