from dotenv import load_dotenv
load_dotenv()

import asyncio
from src.versions.v1.agents.teacher_agent import TaskerAgent
from src.versions.v1.utils.session_manager import session_manager, AgentState
from src.utils.logger import Logger
from typing import Dict, Any

logger = Logger(__name__)

async def worker_execute_v1(
    query: str,
    session_id: str = "default",
    user_id: str = "",
    channel_id: str = "",
    llm_model: str = "",
    token: str = ""
    ):
    """Version 1.0 worker execution logic - simplified without intent classification"""
    try:
        logger.info(f"📝 [V1] Query: {query}")
        logger.info(f"👤 [V1] User: {user_id},\nChannel: {channel_id}")

        _ensure_session_exists(session_id, user_id, channel_id)
        session_manager.set_agent_state(session_id, AgentState.CONVERSATION)
        current_agent = session_manager.get_current_agent(session_id)
        result = await _execute_tasker_agent(query, session_id, user_id, llm_model, token)
        _update_session_and_result(session_id, query, result, current_agent)
        return result

    except Exception as e:
        logger.error(f"❌ [V1] Session {session_id}: Error in worker execution: {str(e)}")
        return _create_error_response(str(e))

def _ensure_session_exists(session_id: str, user_id: str, channel_id: str):
    """Ensure session exists, create if not"""
    session = session_manager.get_session(session_id)
    if not session:
        session_manager.create_session(session_id, user_id, channel_id)


def _update_session_and_result(session_id: str, query: str, result: Dict[str, Any], current_agent: AgentState):
    """Update session history and add metadata to result - simplified without intent"""
    # Add conversation turn without intent (V1 doesn't use intent classification)
    session_manager.add_conversation_turn(session_id, query, result.get("llmOutput", ""))
    result.update({
        "session_id": session_id,
        "current_agent": current_agent.value,
        "session_stats": session_manager.get_session_stats(session_id)
    })
    
def _create_error_response(error_msg: str, agent: str = "conversational") -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "llmOutput": f"Sorry, I encountered an error: {error_msg}",
        "success": False,
        "error": error_msg,
        "version": "1.0",
        "agent": agent,
        "model": "Error",
        "response_time_ms": 0
    }

async def _execute_tasker_agent(query: str, session_id: str, user_id: str, llm_model: str, token: str) -> Dict:
    """Execute with conversational tasker agent"""
    try:
        # Initialize conversational tasker agent with user-selected model
        tasker_agent = TaskerAgent(llm_model=llm_model, token=token, user_id=user_id)

        # Process conversation through TaskerAgent
        result = await asyncio.get_event_loop().run_in_executor(
            None, tasker_agent.run, query, session_id
        )

        return {
            "llmOutput": result.get("llmOutput", "Sorry, I encountered an error:"),
            "success": result.get("success", False),
            "version": "1.0",
            "agent": "conversational",
            "model": result.get("model", "Unknown"),
            "response_time_ms": result.get("response_time_ms", 0)
        }

    except Exception as e:
        logger.error(f"❌ [V1] Error in conversational agent execution: {str(e)}")
        return _create_error_response(f"Lỗi khi xử lý yêu cầu: {str(e)}", "conversational")

def get_v1_capabilities():
    """Get V1 specific capabilities and features"""
    return {
        "version": "1.0",
        "features": [
            "enhanced_rag",
            "reranking",
            "query_preprocessing", 
            "response_enhancement",
            "advanced_error_handling",
            "performance_monitoring"
        ],
        "tools": [
            # "tasker_knowledge"  # Removed old tool
        ],
        "enhancements": {
            "reranking": "External rerank service with configurable threshold",
            "query_preprocessing": "Intent detection and query enhancement",
            "response_enhancement": "Advanced response formatting and validation"
        }
    }
