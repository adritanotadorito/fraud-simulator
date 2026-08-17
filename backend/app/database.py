import logging
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseProvider:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    connected: bool = False


db_provider = DatabaseProvider()


async def connect_to_mongo():
    """Connect to MongoDB on app startup. Non-fatal if unavailable."""
    try:
        db_provider.client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        db_provider.db = db_provider.client[settings.MONGO_DB_NAME]
        # Verify connection with a ping
        await db_provider.client.admin.command("ping")
        db_provider.connected = True
        logger.info(f"Connected to MongoDB at {settings.MONGO_URI}")
        await create_indexes()
    except Exception as e:
        logger.warning(f"MongoDB not available: {e}. Running in degraded mode.")
        db_provider.connected = False


async def close_mongo_connection():
    """Close MongoDB connection on app shutdown."""
    if db_provider.client:
        db_provider.client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    if db_provider.db is None:
        raise RuntimeError("Database not initialized. Is MongoDB running?")
    return db_provider.db


def is_connected() -> bool:
    """Check if MongoDB is connected."""
    return db_provider.connected


async def insert_one(collection: str, document: dict) -> str:
    """Insert a single document into a collection."""
    db = get_database()
    result = await db[collection].insert_one(document)
    return str(result.inserted_id)


async def find_one(collection: str, filter_dict: dict) -> Optional[dict]:
    """Find a single document."""
    db = get_database()
    return await db[collection].find_one(filter_dict)


async def find_many(
    collection: str, filter_dict: dict,
    limit: int = 100, sort: Optional[List[tuple]] = None
) -> List[dict]:
    """Find multiple documents."""
    db = get_database()
    cursor = db[collection].find(filter_dict)
    if sort:
        cursor = cursor.sort(sort)
    if limit > 0:
        cursor = cursor.limit(limit)
    return await cursor.to_list(length=limit if limit > 0 else None)


async def update_one(collection: str, filter_dict: dict, update_dict: dict) -> bool:
    """Update a single document."""
    db = get_database()
    result = await db[collection].update_one(filter_dict, update_dict)
    return result.modified_count > 0


async def count_documents(collection: str, filter_dict: dict) -> int:
    """Count documents matching a filter."""
    db = get_database()
    return await db[collection].count_documents(filter_dict)


async def create_indexes() -> None:
    """Create necessary database indexes."""
    try:
        db = get_database()
        await db["transactions"].create_index([("timestamp", -1)])
        await db["transactions"].create_index([("account_id", 1)])
        await db["transactions"].create_index([("user_id", 1)])
        await db["transactions"].create_index([("txn_id", 1)], unique=True)
        await db["fraud_events"].create_index([("round", -1)])
        await db["fraud_events"].create_index([("persona", 1)])
        await db["fraud_events"].create_index([("event_id", 1)], unique=True)
        await db["decisions"].create_index([("txn_id", 1)])
        await db["decisions"].create_index([("created_at", -1)])
        await db["decisions"].create_index([("decision_id", 1)], unique=True)
        await db["sessions"].create_index([("user_id", 1)])
        await db["sessions"].create_index([("session_id", 1)], unique=True)
        await db["users"].create_index([("user_id", 1)], unique=True)
        await db["devices"].create_index([("device_id", 1)], unique=True)
        # Auth indexes
        await db["app_users"].create_index([("email", 1)], unique=True)
        await db["app_users"].create_index([("id", 1)], unique=True)
        logger.info("Database indexes created successfully.")
    except Exception as e:
        logger.warning(f"Index creation failed: {e}")
