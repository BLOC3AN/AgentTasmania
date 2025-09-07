from typing import Dict, Any, Optional
from enum import Enum
import time
from src.utils.logger import Logger

logger = Logger(__name__)

class AgentState(Enum):
    """Trạng thái của agent"""
    CONVERSATION = "conversation"

class SessionManager:
    """
    Quản lý session và trạng thái conversation
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = 3600  # 1 hour
    
    def create_session(self, session_id: str, user_id: str = "", channel_id: str = "") -> Dict[str, Any]:
        """
        Tạo session mới
        """
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "channel_id": channel_id,
            "current_agent": AgentState.CONVERSATION,  # V1 only uses conversation agent
            "conversation_history": [],
            "created_at": time.time(),
            "last_activity": time.time()
        }

        self.sessions[session_id] = session_data
        logger.info(f"✅ Created new session: {session_id}")
        return session_data
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin session
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check timeout
        if time.time() - session["last_activity"] > self.session_timeout:
            logger.info(f"⏰ Session {session_id} expired, removing...")
            del self.sessions[session_id]
            return None
        
        return session
    
    def update_session_activity(self, session_id: str):
        """
        Cập nhật thời gian hoạt động cuối
        """
        if session_id in self.sessions:
            self.sessions[session_id]["last_activity"] = time.time()
    
    def set_agent_state(self, session_id: str, agent_state: AgentState):
        """
        Thay đổi trạng thái agent
        """
        if session_id in self.sessions:
            old_state = self.sessions[session_id]["current_agent"]
            self.sessions[session_id]["current_agent"] = agent_state
            self.update_session_activity(session_id)
        
            logger.info(f"Session {session_id}: Agent state changed from {old_state.value} to {agent_state.value}")
    
    def get_current_agent(self, session_id: str) -> AgentState:
        """
        Lấy trạng thái agent hiện tại
        """
        session = self.get_session(session_id)
        if session:
            return session["current_agent"]
        return AgentState.CONVERSATION
    
    def add_conversation_turn(self, session_id: str, user_query: str, agent_response: str):
        """
        Thêm lượt hội thoại vào lịch sử
        """
        if session_id not in self.sessions:
            return

        turn = {
            "timestamp": time.time(),
            "user_query": user_query,
            "agent_response": agent_response,
            "agent_state": self.sessions[session_id]["current_agent"].value
        }

        self.sessions[session_id]["conversation_history"].append(turn)
        self.update_session_activity(session_id)

        # Keep only last 20 turns to prevent memory bloat
        if len(self.sessions[session_id]["conversation_history"]) > 20:
            self.sessions[session_id]["conversation_history"] = self.sessions[session_id]["conversation_history"][-20:]
    
    
    def get_conversation_context(self, session_id: str, last_n_turns: int = 5) -> str:
        """
        Lấy context từ conversation history
        """
        session = self.get_session(session_id)
        if not session:
            return ""
        
        history = session.get("conversation_history", [])
        recent_history = history[-last_n_turns:] if history else []
        
        context_parts = []
        for turn in recent_history:
            context_parts.append(f"User: {turn['user_query']}")
            context_parts.append(f"Agent: {turn['agent_response']}")
        
        return "\n".join(context_parts)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Lấy thống kê session
        """
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            "session_id": session_id,
            "current_agent": session["current_agent"].value,
            "conversation_turns": len(session["conversation_history"]),
            "session_duration": time.time() - session["created_at"],
            "last_activity": session["last_activity"]
        }
    
    def cleanup_expired_sessions(self):
        """
        Dọn dẹp các session đã hết hạn
        """
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session["last_activity"] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"🗑️ Removed expired session: {session_id}")
        
        if expired_sessions:
            logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_all_sessions_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê tất cả sessions
        """
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": [sid for sid in self.sessions.keys()],
            "agent_distribution": {
                "conversation": len([s for s in self.sessions.values() if s["current_agent"] == AgentState.CONVERSATION])
            }
        }

# Global session manager instance
session_manager = SessionManager()
