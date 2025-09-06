import json
import redis
from langchain.memory import ConversationBufferMemory, ConversationSummaryBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Dict, Any, Optional
from src.utils.logger import Logger
from datetime import datetime
from ..config import get_config

logger = Logger(__name__)

# At module level
redis_pool = None

def get_redis_connection():
    global redis_pool
    if redis_pool is None:
        config = get_config()
        redis_config = config.redis

        # Parse URL to get host and port
        url_parts = redis_config.url.replace("redis://", "").split(":")
        redis_host = url_parts[0] if len(url_parts) > 0 else "localhost"
        redis_port = int(url_parts[1]) if len(url_parts) > 1 else 6379

        redis_pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            password=redis_config.password,
            db=redis_config.db,
            decode_responses=redis_config.decode_responses
        )
    return redis.Redis(connection_pool=redis_pool)

class RedisConversationMemory:
    def __init__(self, session_id: str = "default"):
        """Initialize Redis-based conversation memory.
        
        Args:
            session_id: Unique identifier for the conversation session
        """
        self.session_id = session_id
        self.redis_client = get_redis_connection()
        self.redis_key = f"memory:{session_id}"
        logger.info(f"📦 Redis memory initialized for session: {session_id}")
        
    def conversation_buffer_memory(self):
        """Create a conversation buffer memory that uses Redis for storage."""
        try:
            logger.info(f"🔧 Starting conversation_buffer_memory() for session: {self.session_id}")
            # Use standard ConversationBufferMemory for now to avoid field issues
            from langchain.memory import ConversationBufferMemory
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="output"
            )
            # Load existing messages from Redis if they exist
            try:
                history = self.get_conversation_history()
                if history:
                    logger.info(f"🔄 Loading {len(history)} messages from Redis into memory")
                    for message in history:
                        if message["type"] == "human":
                            memory.chat_memory.add_user_message(message["content"])
                        elif message["type"] == "ai":
                            memory.chat_memory.add_ai_message(message["content"])
                    logger.info(f"✅ Successfully loaded conversation history for session: {self.session_id}")
                else:
                    logger.info(f"📭 No existing conversation history found for session: {self.session_id}")
            except Exception as e:
                logger.error(f"❌ Error loading messages from Redis: {str(e)}")
            return memory
        except Exception as e:
            logger.error(f"❌ Error in conversation_buffer_memory(): {str(e)}")
            raise e
    
    def conversation_summary_buffer_memory(self, llm):
        """Create a conversation summary buffer memory with Redis storage.
        Args:
            llm: Language model for summarization
        """
        summary_memory = ConversationSummaryBufferMemory(
            llm=llm,
            max_token_limit=1000,
            return_messages=True,
            memory_key="chat_history"
        )
        return summary_memory

    def get_conversation_history(self):
        """Get the full conversation history from Redis.

        Returns:
            List of message dictionaries or None if no history exists
        """
        try:
            data = self.redis_client.get(self.redis_key)
            logger.info(f"📊 Redis key: {self.redis_key}")
            if data:
                history = json.loads(data)
                logger.info(f"Found {len(history)} messages in history")
                return history
            else:
                logger.warning(f"No conversation history found for session {self.session_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting conversation history from Redis: {str(e)}")
            return None

    def get_conversation_summary(self, max_messages: int = 10):
        """Get a summary of recent conversation history.

        Args:
            max_messages: Maximum number of recent messages to return

        Returns:
            List of recent message dictionaries
        """
        try:
            history = self.get_conversation_history()
            if history and len(history) > 0:
                # Return the most recent messages
                recent_messages = history[-max_messages:] if len(history) > max_messages else history
                logger.info(f" Returning {len(recent_messages)} recent messages")
                return recent_messages
            return []
        except Exception as e:
            logger.error(f"❌ Error getting conversation summary: {str(e)}")
            return []


class RedisBackedMemory:
    """Custom memory class that uses Redis for storage and wraps ConversationBufferMemory."""

    def __init__(
        self,
        session_id: str,
        redis_client: redis.Redis,
        memory_key: str = "chat_history",
        return_messages: bool = True,
        human_prefix: str = "Human",
        ai_prefix: str = "AI",
        **kwargs
    ):
        # Store Redis-related attributes
        self.session_id = session_id
        self.redis_client = redis_client
        self.redis_key = f"memory:{session_id}"

        # Create the underlying ConversationBufferMemory
        self.memory = ConversationBufferMemory(
            memory_key=memory_key,
            return_messages=return_messages,
            human_prefix=human_prefix,
            ai_prefix=ai_prefix,
            **kwargs
        )
        self._load_from_redis()

    # Delegate all ConversationBufferMemory methods to the wrapped memory
    def __getattr__(self, name):
        """Delegate attribute access to the wrapped memory object."""
        return getattr(self.memory, name)
    
    def update_session_id(self, value):
        """Update session_id and sync all related attributes."""
        self.session_id = value
        self.redis_key = f"memory:{value}"

    def update_redis_client(self, value):
        """Update redis_client."""
        self.redis_client = value

    def _load_from_redis(self):
        """Load existing messages from Redis."""
        try:
            data = self.redis_client.get(self.redis_key)
            if data:
                messages = json.loads(data)
                for message in messages:
                    if message["type"] == "human":
                        self.memory.chat_memory.add_user_message(message["content"])
                    elif message["type"] == "ai":
                        self.memory.chat_memory.add_ai_message(message["content"])
        except Exception as e:
            logger.error(f"❌ Error loading messages from Redis: {str(e)}")
    
    def _save_to_redis(self):
        """Save current messages to Redis."""
        try:
            messages = []
            for message in self.memory.chat_memory.messages:
                if hasattr(message, "type") and hasattr(message, "content"):
                    msg_dict = {
                        "type": message.type,
                        "content": message.content,
                        "timestamp": datetime.now().isoformat()
                    }
                    messages.append(msg_dict)

            if messages:
                self.redis_client.set(self.redis_key, json.dumps(messages))
        except Exception as e:
            logger.error(f"❌ Error saving messages to Redis: {str(e)}")

    def save_context(self, inputs, outputs):
        """Save context to Redis after adding to memory."""
        self.memory.save_context(inputs, outputs)
        self._save_to_redis()

    def clear(self):
        """Clear Redis when memory is cleared."""
        self.memory.clear()
        try:
            self.redis_client.delete(self.redis_key)
        except Exception as e:
            logger.error(f"❌ Error clearing Redis memory: {str(e)}")
