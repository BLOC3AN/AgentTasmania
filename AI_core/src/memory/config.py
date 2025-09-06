"""
Memory System Configuration

Centralized configuration management for the memory system.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from src.utils.logger import Logger

logger = Logger(__name__)

@dataclass
class RedisConfig:
    """Redis configuration settings."""
    url: str
    db: int
    password: Optional[str]
    decode_responses: bool = True

@dataclass
class MongoConfig:
    """MongoDB configuration settings."""
    uri: str
    database: str
    collections: Dict[str, str]

@dataclass
class MemoryConfig:
    """Memory system configuration settings."""
    message_cache_ttl: int
    session_cache_ttl: int
    context_cache_ttl: int
    max_context_messages: int
    context_days: int
    auto_summarize_threshold: int
    context_window_size: int

class MemorySystemConfig:
    """Centralized configuration manager for the memory system."""

    def __init__(self):
        self.redis = self._load_redis_config()
        self.mongo = self._load_mongo_config()
        self.memory = self._load_memory_config()
        logger.info("🔧 Memory system configuration loaded")

    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration from environment variables."""
        return RedisConfig(
            url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD") or None
        )

    def _load_mongo_config(self) -> MongoConfig:
        """Load MongoDB configuration from environment variables."""
        collections = {
            "messages": os.getenv("MONGODB_COLLECTION_MESSAGES", "messages"),
            "conversations": os.getenv("MONGODB_COLLECTION_CONVERSATIONS", "conversations"),
            "user_profiles": os.getenv("MONGODB_COLLECTION_USER_PROFILES", "user_profiles")
        }

        return MongoConfig(
            uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
            database=os.getenv("MONGODB_DATABASE", "multi_agent_system"),
            collections=collections
        )

    def _load_memory_config(self) -> MemoryConfig:
        """Load memory system configuration from environment variables."""
        return MemoryConfig(
            message_cache_ttl=int(os.getenv("MESSAGE_CACHE_TTL", "1800")),
            session_cache_ttl=int(os.getenv("SESSION_CACHE_TTL", "7200")),
            context_cache_ttl=int(os.getenv("CONTEXT_CACHE_TTL", "1800")),
            max_context_messages=int(os.getenv("MAX_CONTEXT_MESSAGES", "50")),
            context_days=int(os.getenv("CONTEXT_DAYS", "30")),
            auto_summarize_threshold=int(os.getenv("AUTO_SUMMARIZE_THRESHOLD", "50")),
            context_window_size=int(os.getenv("CONTEXT_WINDOW_SIZE", "20"))
        )
# Global configuration instance
config = MemorySystemConfig()

def get_config() -> MemorySystemConfig:
    """Get the global configuration instance."""
    return config
