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


class PincodeData(Document):
    pincode: str
    home_scan: str
    clinic_1: Optional[str] = None
    clinic_2: Optional[str] = None
    city: str


class Call(Document):
    call_sid: str
    status: str = CallStatus.RINGING
    phone_number: str
    recording_url: Optional[str] = None
    call_cost: Optional[float] = None
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

        # Create Motor async client with proper connection parameters
        client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,  # 5 second timeout for server selection
            connectTimeoutMS=10000,  # 10 second timeout for connection
            socketTimeoutMS=20000,  # 20 second timeout for socket operations
            maxPoolSize=10,  # Maximum number of connections in the pool
            minPoolSize=1,  # Minimum number of connections in the pool
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
