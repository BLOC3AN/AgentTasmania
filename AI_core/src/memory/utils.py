"""
Memory System Utilities

Common utility functions for the memory management system.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from src.utils.logger import Logger

logger = Logger(__name__)

def validate_message_format(message: Dict[str, Any]) -> bool:
    """Validate message format for memory storage."""
    required_fields = ["role", "content"]

    for field in required_fields:
        if field not in message:
            logger.error(f"Missing required field: {field}")
            return False

    valid_roles = ["user", "assistant", "system"]
    if message["role"] not in valid_roles:
        logger.error(f"Invalid role: {message['role']}")
        return False

    if not isinstance(message["content"], str) or not message["content"].strip():
        logger.error("Content must be a non-empty string")
        return False

    return True

def generate_message_hash(message: Dict[str, Any]) -> str:
    """Generate a unique hash for a message for deduplication."""
    content = message.get("content", "")
    role = message.get("role", "")
    timestamp = message.get("timestamp", "")

    hash_input = f"{role}:{content}:{timestamp}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

def deduplicate_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate messages based on content and timestamp."""
    seen_hashes = set()
    deduplicated = []

    for message in messages:
        message_hash = generate_message_hash(message)
        if message_hash not in seen_hashes:
            seen_hashes.add(message_hash)
            deduplicated.append(message)

    return deduplicated

def filter_messages_by_timeframe(
    messages: List[Dict[str, Any]],
    days: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Filter messages by timeframe."""
    if not messages or not days:
        return messages

    cutoff = datetime.now() - timedelta(days=days)
    filtered = []

    for message in messages:
        if "timestamp" not in message:
            continue

        try:
            msg_time = datetime.fromisoformat(message["timestamp"])
            if msg_time >= cutoff:
                filtered.append(message)
        except ValueError:
            continue

    return filtered

def safe_json_loads(data: Union[str, bytes, None]) -> Optional[Dict[str, Any]]:
    """Safely load JSON data with error handling."""
    if not data:
        return None

    try:
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to parse JSON data: {e}")
        return None
