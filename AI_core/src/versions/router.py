from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.versions.v1.worker import worker_execute_v1
from src.utils.logger import Logger
from src.memory.conversation.redisMemory import RedisConversationMemory

logger = Logger(__name__)

# Create FastAPI router
router = APIRouter()

VERSION_HANDLERS = {
    "v1.0": worker_execute_v1,
}

async def route_worker_by_version(
    version: str,
    query: str,
    session_id: str = "default",
    user_id: str = "",
    channel_id: str = "",
    llm_model: str = "",
    token: str = ""
    ):
    """Route worker execution based on version with optional streaming support"""
    version = version.strip() if version else "v1.0"
    
    if version not in VERSION_HANDLERS:
        logger.warning(f"⚠️ Unknown version '{version}', defaulting to v1.0")
        version = "v1.0"
    logger.info(f"🎯 Routing to version: {version}")
    handler = VERSION_HANDLERS[version]

    if version == "v1.0":
        return await handler(
            query=query,
            session_id=session_id,
            user_id=user_id,
            channel_id=channel_id,
            llm_model=llm_model,
            token=token
        )
    else:
        # For other versions (if any are added later)
        return await handler(
            query=query,
            session_id=session_id,
            user_id=user_id,
            channel_id=channel_id,
            llm_model=llm_model,
            token=token
        )

def get_available_versions():
    """Get list of available versions"""
    return [v for v in VERSION_HANDLERS.keys() if v]  

def get_version_info():
    """Get version information"""
    return {
        "available_versions": get_available_versions(),
        "default_version": "v1.0",
        "latest_version": "v1.0"
    }

# Add endpoints to router
@router.get("/versions")
async def get_versions():
    """Get available versions"""
    return get_version_info()

class ExecuteRequest(BaseModel):
    version: str = "v1.0"
    query: str = ""
    session_id: str = "default"
    user_id: str = ""
    channel_id: str = ""
    llm_model: str = ""
    token: str = ""

@router.post("/execute")
async def execute_worker(request: ExecuteRequest):
    """Execute worker by version"""
    logger.info(f"🔧 _session_id value: {request.session_id}")
    result = await route_worker_by_version(
        version=request.version,
        query=request.query,
        session_id=request.session_id,
        user_id=request.user_id,
        channel_id=request.channel_id,
        llm_model=request.llm_model,
        token=request.token
    )

    return result

@router.get("/conversation-history/{session_id}")
async def get_conversation_history(session_id: str):
    """Get conversation history for a specific session"""
    try:
        logger.info(f"📖 Getting conversation history for session: {session_id}")

        # Initialize Redis memory for the session
        redis_memory = RedisConversationMemory(session_id=session_id)

        # Get conversation history
        history = redis_memory.get_conversation_history()

        if history:
            logger.info(f"✅ Found {len(history)} messages for session {session_id}")
            return {
                "success": True,
                "session_id": session_id,
                "message_count": len(history),
                "history": history
            }
        else:
            logger.info(f"📭 No conversation history found for session {session_id}")
            return {
                "success": True,
                "session_id": session_id,
                "message_count": 0,
                "history": []
            }

    except Exception as e:
        logger.error(f"❌ Error getting conversation history for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation history: {str(e)}"
        )

@router.get("/conversation-summary/{session_id}")
async def get_conversation_summary(session_id: str, max_messages: int = 10):
    """Get a summary of recent conversation history"""
    try:
        logger.info(f"📋 Getting conversation summary for session: {session_id} (max: {max_messages})")

        # Initialize Redis memory for the session
        redis_memory = RedisConversationMemory(session_id=session_id)

        # Get conversation summary
        summary = redis_memory.get_conversation_summary(max_messages=max_messages)

        return {
            "success": True,
            "session_id": session_id,
            "max_messages": max_messages,
            "message_count": len(summary),
            "summary": summary
        }

    except Exception as e:
        logger.error(f"❌ Error getting conversation summary for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation summary: {str(e)}"
        )
