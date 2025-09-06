"""
MongoDB Utilities for Agent Education

Provides MongoDB connection management for both sync and async operations.
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
from src.utils.logger import Logger

logger = Logger(__name__)

class MongoDBConnection:
    """MongoDB connection manager for both sync and async operations"""
    
    def __init__(self, mongodb_uri: str, database_name: str):
        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self._sync_client: Optional[MongoClient] = None
        self._async_client: Optional[AsyncIOMotorClient] = None
        self._sync_db = None
        self._async_db = None
    
    @property
    def sync_client(self) -> MongoClient:
        """Get synchronous MongoDB client"""
        if self._sync_client is None:
            self._sync_client = MongoClient(self.mongodb_uri)
            logger.info(f"📦 MongoDB sync client connected to: {self.mongodb_uri}")
        return self._sync_client
    
    @property
    def async_client(self) -> AsyncIOMotorClient:
        """Get asynchronous MongoDB client"""
        if self._async_client is None:
            self._async_client = AsyncIOMotorClient(self.mongodb_uri)
            logger.info(f"📦 MongoDB async client connected to: {self.mongodb_uri}")
        return self._async_client
    
    @property
    def sync_db(self):
        """Get synchronous database instance"""
        if self._sync_db is None:
            self._sync_db = self.sync_client[self.database_name]
            logger.info(f"📊 MongoDB sync database selected: {self.database_name}")
        return self._sync_db
    
    @property
    def async_db(self):
        """Get asynchronous database instance"""
        if self._async_db is None:
            self._async_db = self.async_client[self.database_name]
            logger.info(f"📊 MongoDB async database selected: {self.database_name}")
        return self._async_db
    
    def close_sync(self):
        """Close synchronous connection"""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
            self._sync_db = None
            logger.info("✅ MongoDB sync connection closed")
    
    def close_async(self):
        """Close asynchronous connection"""
        if self._async_client:
            self._async_client.close()
            self._async_client = None
            self._async_db = None
            logger.info("✅ MongoDB async connection closed")
    
    def close_all(self):
        """Close all connections"""
        self.close_sync()
        self.close_async()

# Global MongoDB connection instance
_mongodb_connection: Optional[MongoDBConnection] = None

def get_mongodb_connection(mongodb_uri: str = None, database_name: str = None) -> MongoDBConnection:
    """
    Get or create MongoDB connection instance
    
    Args:
        mongodb_uri: MongoDB connection URI (optional, uses env var if not provided)
        database_name: Database name (optional, uses env var if not provided)
        
    Returns:
        MongoDBConnection instance
    """
    global _mongodb_connection
    
    if _mongodb_connection is None:
        if not mongodb_uri or not database_name:
            # Use default values from environment
            mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
            database_name = os.getenv("MONGODB_DATABASE", "multi_agent_system")
        
        _mongodb_connection = MongoDBConnection(mongodb_uri, database_name)
        logger.info(f"🔗 MongoDB connection initialized: {database_name}")
    
    return _mongodb_connection

def close_mongodb_connection():
    """Close global MongoDB connection"""
    global _mongodb_connection
    if _mongodb_connection:
        _mongodb_connection.close_all()
        _mongodb_connection = None
        logger.info("🔒 Global MongoDB connection closed")

def test_mongodb_connection() -> bool:
    """
    Test MongoDB connection
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        conn = get_mongodb_connection()
        # Test sync connection
        conn.sync_client.admin.command('ping')
        logger.info("✅ MongoDB connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB connection test failed: {e}")
        return False

def get_collection(collection_name: str, use_async: bool = False):
    """
    Get a specific collection from MongoDB
    
    Args:
        collection_name: Name of the collection
        use_async: Whether to use async client
        
    Returns:
        MongoDB collection object
    """
    try:
        conn = get_mongodb_connection()
        if use_async:
            return conn.async_db[collection_name]
        else:
            return conn.sync_db[collection_name]
    except Exception as e:
        logger.error(f"❌ Failed to get collection {collection_name}: {e}")
        raise

def create_indexes():
    """Create necessary indexes for the memory system collections"""
    try:
        conn = get_mongodb_connection()
        db = conn.sync_db
        
        # Messages collection indexes
        messages_collection = db.messages
        messages_collection.create_index([("userId", 1), ("channelId", 1), ("timestamp", -1)])
        messages_collection.create_index([("timestamp", -1)])
        messages_collection.create_index([("userId", 1)])
        
        # Conversations collection indexes
        conversations_collection = db.conversations
        conversations_collection.create_index([("userId", 1), ("channelId", 1), ("created_at", -1)])
        conversations_collection.create_index([("type", 1), ("created_at", -1)])
        
        # User profiles collection indexes
        user_profiles_collection = db.user_profiles
        user_profiles_collection.create_index([("userId", 1), ("preference_type", 1)], unique=True)
        user_profiles_collection.create_index([("updated_at", -1)])
        
        logger.info("✅ MongoDB indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create MongoDB indexes: {e}")
        raise

def get_database_stats() -> dict:
    """
    Get database statistics
    
    Returns:
        Dictionary with database statistics
    """
    try:
        conn = get_mongodb_connection()
        db = conn.sync_db
        
        stats = {
            "database_name": db.name,
            "collections": {},
            "total_size": 0
        }
        
        # Get stats for each collection
        for collection_name in db.list_collection_names():
            collection_stats = db.command("collStats", collection_name)
            stats["collections"][collection_name] = {
                "count": collection_stats.get("count", 0),
                "size": collection_stats.get("size", 0),
                "avgObjSize": collection_stats.get("avgObjSize", 0)
            }
            stats["total_size"] += collection_stats.get("size", 0)
        
        logger.info(f"📊 Retrieved database stats for {db.name}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to get database stats: {e}")
        return {}

def cleanup_old_data(days_old: int = 90):
    """
    Cleanup old data from the database
    
    Args:
        days_old: Number of days to keep data
    """
    try:
        from datetime import datetime, timedelta
        
        conn = get_mongodb_connection()
        db = conn.sync_db
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Archive old messages
        messages_collection = db.messages
        result = messages_collection.update_many(
            {"timestamp": {"$lt": cutoff_date}, "archived": {"$ne": True}},
            {"$set": {"archived": True, "archived_at": datetime.now()}}
        )
        
        logger.info(f"📦 Archived {result.modified_count} old messages")
        
        # Clean up old processing status (if any)
        # Add more cleanup logic as needed
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup old data: {e}")
        raise
