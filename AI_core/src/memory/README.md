# Memory Management System

Hệ thống quản lý bộ nhớ cho Agent Education với kiến trúc Redis (ngắn hạn) + MongoDB (dài hạn).

## 🏗️ Kiến trúc

- **Redis**: Session hiện tại, tin nhắn gần đây (TTL auto-cleanup)
- **MongoDB**: Lịch sử vĩnh viễn, tóm tắt cuộc trò chuyện, user preferences

## 📁 Cấu trúc

```
memory/
├── config.py                   # Centralized configuration
├── memory_manager.py           # Unified interface
├── utils.py                    # Utility functions
└── conversation/
    ├── redisMemory.py         # Redis short-term
    └── mongoMemory.py         # MongoDB long-term
```

## 🔧 Environment Variables

```env
# Redis
REDIS_URL=redis://redis:6379
REDIS_DB=0
REDIS_PASSWORD=

# MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=multi_agent_system

# Settings
MESSAGE_CACHE_TTL=1800
MAX_CONTEXT_MESSAGES=50
CONTEXT_DAYS=30
```

## 🚀 Usage

```python
from src.memory.memory_manager import MemoryManager

# Initialize
memory_manager = MemoryManager(
    user_id="user_123",
    session_id="session_456"
)

# Add messages
memory_manager.add_message("user", "Hello!")
memory_manager.add_message("assistant", "Hi there!")

# Get context & create LangChain memory
context = memory_manager.get_conversation_context()
langchain_memory = memory_manager.create_langchain_memory()
```
