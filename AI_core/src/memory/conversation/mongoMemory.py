from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from langchain.memory import ConversationBufferMemory
from src.utils.logger import Logger
from bson import ObjectId
from ..config import get_config

logger = Logger(__name__)

def _get_mongodb_connection():
    """Get MongoDB connection with centralized config."""
    try:
        from src.utils.mongodb_utils import get_mongodb_connection
        return get_mongodb_connection()
    except ImportError:
        from pymongo import MongoClient
        config = get_config()
        mongo_config = config.mongo
        class MockConnection:
            def __init__(self):
                self.client = MongoClient(mongo_config.uri)
                self.sync_db = self.client[mongo_config.database]

        return MockConnection()

class MongoLongMemory:
    """MongoDB-based long-term memory for persistent conversation storage."""

    def __init__(self, user_id: str, channel_id: str):
        self.user_id = user_id
        self.channel_id = channel_id

        # Load centralized configuration
        config = get_config()

        # Initialize MongoDB connection
        self.mongodb_conn = _get_mongodb_connection()
        self.db = self.mongodb_conn.sync_db

        # Use centralized collection names
        collections = config.mongo.collections
        self.messages_collection = self.db[collections["messages"]]
        self.conversations_collection = self.db[collections["conversations"]]
        self.user_profiles_collection = self.db[collections["user_profiles"]]

        # Use centralized configuration
        self.max_context_messages = config.memory.max_context_messages
        self.context_days = config.memory.context_days

        logger.info(f"📚 MongoDB long memory initialized for user: {user_id}, channel: {channel_id}")

    def save_conversation_summary(self, summary: str, message_count: int):
        """Save conversation summary to MongoDB for long-term storage."""
        try:
            summary_doc = {
                "userId": ObjectId(self.user_id),
                "channelId": ObjectId(self.channel_id),
                "summary": summary,
                "message_count": message_count,
                "created_at": datetime.now(),
                "type": "conversation_summary"
            }

            result = self.conversations_collection.insert_one(summary_doc)
            logger.info(f"💾 Saved conversation summary: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"❌ Error saving conversation summary: {e}")
            return None

    def get_conversation_context(self, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation context from the last N days."""
        try:
            days = days or self.context_days
            cutoff_date = datetime.now() - timedelta(days=days)

            messages_cursor = self.messages_collection.find({
                "userId": ObjectId(self.user_id),
                "channelId": ObjectId(self.channel_id),
                "timestamp": {"$gte": cutoff_date}
            }).sort("timestamp", -1).limit(self.max_context_messages)

            messages = list(messages_cursor)
            messages.reverse()  # Chronological order

            logger.info(f"📖 Retrieved {len(messages)} context messages from last {days} days")
            return messages
        except Exception as e:
            logger.error(f"❌ Error getting conversation context: {e}")
            return []

    def get_conversation_summaries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation summaries for context."""
        try:
            summaries_cursor = self.conversations_collection.find({
                "userId": ObjectId(self.user_id),
                "channelId": ObjectId(self.channel_id),
                "type": "conversation_summary"
            }).sort("created_at", -1).limit(limit)

            summaries = list(summaries_cursor)
            logger.info(f"📋 Retrieved {len(summaries)} conversation summaries")
            return summaries
        except Exception as e:
            logger.error(f"❌ Error getting conversation summaries: {e}")
            return []

    def save_user_preference(self, preference_type: str, preference_data: Dict[str, Any]):
        """Save user preferences and learning data to MongoDB."""
        try:
            preference_doc = {
                "userId": ObjectId(self.user_id),
                "preference_type": preference_type,
                "data": preference_data,
                "updated_at": datetime.now()
            }

            result = self.user_profiles_collection.update_one(
                {"userId": ObjectId(self.user_id), "preference_type": preference_type},
                {"$set": preference_doc},
                upsert=True
            )

            logger.info(f"💾 Saved user preference: {preference_type}")
            return result.upserted_id or result.modified_count
        except Exception as e:
            logger.error(f"❌ Error saving user preference: {e}")
            return None

    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences and learning data."""
        try:
            preferences_cursor = self.user_profiles_collection.find({
                "userId": ObjectId(self.user_id)
            })

            preferences = {
                pref["preference_type"]: pref["data"]
                for pref in preferences_cursor
            }

            logger.info(f"📊 Retrieved {len(preferences)} user preferences")
            return preferences
        except Exception as e:
            logger.error(f"❌ Error getting user preferences: {e}")
            return {}

    def conversation_buffer_memory(self):
        """Create LangChain memory with long-term context from MongoDB."""
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        messages = self._get_recent_messages()
        for msg in messages:
            if msg.get("sender") == "user":
                memory.chat_memory.add_user_message(msg.get("message", ""))
            elif msg.get("sender") == "bot":
                memory.chat_memory.add_ai_message(msg.get("message", ""))

        return memory

    def _get_recent_messages(self, limit: int = 20):
        """Get recent messages from MongoDB for immediate context."""
        try:
            messages_cursor = self.messages_collection.find({
                "userId": ObjectId(self.user_id),
                "channelId": ObjectId(self.channel_id)
            }).sort("timestamp", -1).limit(limit)

            messages = list(messages_cursor)
            messages.reverse()  # Chronological order

            logger.info(f"📥 Loaded {len(messages)} recent messages from MongoDB")
            return messages
        except Exception as e:
            logger.error(f"❌ Error loading recent messages: {e}")
            return []

    def archive_old_conversations(self, days_old: int = 90):
        """Archive conversations older than specified days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)

            result = self.messages_collection.update_many(
                {
                    "userId": ObjectId(self.user_id),
                    "channelId": ObjectId(self.channel_id),
                    "timestamp": {"$lt": cutoff_date},
                    "archived": {"$ne": True}
                },
                {"$set": {"archived": True, "archived_at": datetime.now()}}
            )

            logger.info(f"📦 Archived {result.modified_count} old messages")
            return result.modified_count
        except Exception as e:
            logger.error(f"❌ Error archiving old conversations: {e}")
            return 0
