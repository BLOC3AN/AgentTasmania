"""
Memory Manager - Unified interface for managing both short-term and long-term memory.

Coordinates between Redis (short-term) and MongoDB (long-term) storage.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from langchain.memory import ConversationBufferMemory

from .config import get_config
from .conversation.redisMemory import RedisConversationMemory, RedisBackedMemory
from .conversation.mongoMemory import MongoLongMemory
from src.utils.logger import Logger

logger = Logger(__name__)

class MemoryManager:
    """Unified memory manager coordinating Redis and MongoDB storage."""

    def __init__(self, user_id: str, session_id: str, channel_id: Optional[str] = None):
        self.user_id = user_id
        self.session_id = session_id
        self.channel_id = channel_id or session_id

        # Load centralized configuration
        self.config = get_config()

        # Initialize memory systems
        try:
            self.short_memory = RedisConversationMemory(session_id=session_id)
            self.long_memory = MongoLongMemory(user_id=user_id, channel_id=self.channel_id)
        except Exception as e:
            logger.warning(f"⚠️ Memory systems initialization failed: {e}")
            self.short_memory = None
            self.long_memory = None

        logger.info(f"🧠 Memory Manager initialized for user: {user_id}, session: {session_id}")
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to short-term memory."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "metadata": metadata or {}
        }

        if self.short_memory:
            self.short_memory.add_message(message)
            logger.debug(f"📝 Added message to memory: {role}")
        else:
            logger.warning(f"⚠️ Short memory not available, message not stored: {role}")

    def get_conversation_context(self, include_long_term: bool = True) -> List[Dict[str, Any]]:
        """Get conversation context combining short-term and long-term memory."""
        try:
            short_term_messages = self.short_memory.get_messages(limit=self.context_window_size)

            if include_long_term and len(short_term_messages) < self.context_window_size:
                remaining_slots = self.context_window_size - len(short_term_messages)
                long_term_context = self.long_memory.get_conversation_context()

                all_messages = long_term_context + short_term_messages
                context_messages = self._deduplicate_messages(all_messages)[-self.context_window_size:]
            else:
                context_messages = short_term_messages

            logger.debug(f"📖 Retrieved {len(context_messages)} messages for context")
            return context_messages
        except Exception as e:
            logger.error(f"❌ Error getting conversation context: {e}")
            return []
    
    def create_langchain_memory(self, memory_type: str = "buffer") -> ConversationBufferMemory:
        """Create a LangChain memory object with appropriate backing storage."""
        try:
            if memory_type == "redis_backed":
                memory = RedisBackedMemory(
                    session_id=self.session_id,
                    redis_client=self.short_memory.redis_client
                )
            else:
                memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )

                # Load recent context into memory
                context_messages = self.get_conversation_context()
                for msg in context_messages:
                    if msg.get("role") == "user":
                        memory.chat_memory.add_user_message(msg.get("content", ""))
                    elif msg.get("role") == "assistant":
                        memory.chat_memory.add_ai_message(msg.get("content", ""))

            return memory
        except Exception as e:
            logger.error(f"❌ Error creating LangChain memory: {e}")
            return ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    def save_conversation_summary(self, summary: str, message_count: int):
        """Save conversation summary to long-term storage."""
        try:
            summary_id = self.long_memory.save_conversation_summary(summary, message_count)
            logger.info(f"💾 Saved conversation summary: {summary_id}")
            return summary_id
        except Exception as e:
            logger.error(f"❌ Error saving conversation summary: {e}")
            return None

    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences from long-term storage."""
        try:
            return self.long_memory.get_user_preferences()
        except Exception as e:
            logger.error(f"❌ Error getting user preferences: {e}")
            return {}

    def save_user_preference(self, preference_type: str, preference_data: Dict[str, Any]):
        """Save user preference to long-term storage."""
        try:
            result = self.long_memory.save_user_preference(preference_type, preference_data)
            logger.info(f"💾 Saved user preference: {preference_type}")
            return result
        except Exception as e:
            logger.error(f"❌ Error saving user preference: {e}")
            return None

    def clear_session(self):
        """Clear current session from short-term memory."""
        try:
            self.short_memory.clear_session()
        except Exception as e:
            logger.error(f"❌ Error clearing session: {e}")

    def extend_session(self):
        """Extend the TTL for current session."""
        try:
            self.short_memory.extend_session()
        except Exception as e:
            logger.error(f"❌ Error extending session: {e}")

    def is_session_active(self) -> bool:
        """Check if current session is active."""
        try:
            return self.short_memory.is_session_active()
        except Exception as e:
            logger.error(f"❌ Error checking session status: {e}")
            return False

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about memory usage."""
        try:
            short_term_messages = len(self.short_memory.get_messages())
            long_term_summaries = len(self.long_memory.get_conversation_summaries())

            return {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "short_term_messages": short_term_messages,
                "long_term_summaries": long_term_summaries,
                "session_active": self.is_session_active(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Error getting memory stats: {e}")
            return {}

    def _deduplicate_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate messages based on content and timestamp."""
        seen = set()
        deduplicated = []

        for msg in messages:
            key = f"{msg.get('content', '')}_{msg.get('timestamp', '')}"
            if key not in seen:
                seen.add(key)
                deduplicated.append(msg)

        return deduplicated

    def __repr__(self):
        return f"MemoryManager(user_id='{self.user_id}', session_id='{self.session_id}', channel_id='{self.channel_id}')"
