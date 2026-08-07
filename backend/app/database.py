import logging
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger(__name__)

class DatabaseProvider:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

db_provider = DatabaseProvider()

async def connect_to_mongo():
    """Connect to MongoDB on app startup."""
    try:
        db_provider.client = AsyncIOMotorClient(settings.MONGO_URI)
        db_provider.db = db_provider.client[settings.MONGO_DB_NAME]
        logger.info(f"Connected to MongoDB at {settings.MONGO_URI}")
        await create_indexes()
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close MongoDB connection on app shutdown."""
    if db_provider.client:
        db_provider.client.close()
        logger.info("MongoDB connection closed")

def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    if db_provider.db is None:
        raise RuntimeError("Database not initialized")
    return db_provider.db

async def insert_one(collection: str, document: dict) -> str:
    """Insert a single document into a collection."""
    db = get_database()
    result = await db[collection].insert_one(document)
    return str(result.inserted_id)

async def find_one(collection: str, filter_dict: dict) -> Optional[dict]:
    """Find a single document."""
    db = get_database()
    return await db[collection].find_one(filter_dict)

async def find_many(collection: str, filter_dict: dict, limit: int = 100, sort: Optional[List[tuple]] = None) -> List[dict]:
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
    db = get_database()
    
    # Indexes on transactions
    await db["transactions"].create_index([("timestamp", -1)])
    await db["transactions"].create_index([("account_id", 1)])
    
    # Indexes on fraud_events
    await db["fraud_events"].create_index([("round", -1)])
    await db["fraud_events"].create_index([("persona", 1)])
    
    # Indexes on decisions
    await db["decisions"].create_index([("txn_id", 1)])
    await db["decisions"].create_index([("created_at", -1)])
    
    logger.info("Database indexes created successfully.")
