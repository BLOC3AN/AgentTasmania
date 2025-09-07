import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import aiohttp

load_dotenv()

app = FastAPI(
    title="WebSocket Service",
    description="Real-time communication service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_mapping: Dict[str, Dict[str, str]] = {}  # connection_id -> session info
        self.agent_preferences: Dict[str, str] = {}  # connection_id -> agent_type

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket

        # Create session mapping - initially use connection_id as session_id
        self.session_mapping[connection_id] = {
            "session_id": connection_id,  # Will be updated if client restores session
            "connection_id": connection_id,
            "connected_at": datetime.now().isoformat(),
            "user_id": "user",  # Default user_id
            "message_count": 0
        }

        # Set default agent preference to academic writing
        self.agent_preferences[connection_id] = "academic_writing"

        print(f"✅ WebSocket connected: {connection_id}")
        print(f"🔗 Session created: {connection_id}")
        return connection_id

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            print(f"❌ WebSocket disconnected: {connection_id}")

        if connection_id in self.session_mapping:
            session_info = self.session_mapping[connection_id]
            print(f"🗑️ Session ended: {connection_id} (Messages: {session_info['message_count']})")
            del self.session_mapping[connection_id]

        if connection_id in self.agent_preferences:
            del self.agent_preferences[connection_id]

    def get_session_info(self, connection_id: str) -> Dict[str, str]:
        return self.session_mapping.get(connection_id, {})

    def restore_session(self, connection_id: str, session_id: str):
        """Restore an existing session for a connection"""
        if connection_id in self.session_mapping:
            self.session_mapping[connection_id]["session_id"] = session_id
            print(f"🔄 Session restored for connection {connection_id}: {session_id}")
            return True
        return False

    def increment_message_count(self, connection_id: str):
        if connection_id in self.session_mapping:
            self.session_mapping[connection_id]["message_count"] += 1

    def set_agent_preference(self, connection_id: str, agent_type: str):
        """Set agent preference for a connection"""
        self.agent_preferences[connection_id] = agent_type
        print(f"🤖 Agent preference set for {connection_id}: {agent_type}")

    def get_agent_preference(self, connection_id: str) -> str:
        """Get agent preference for a connection"""
        return self.agent_preferences.get(connection_id, "academic_writing")

    async def send_personal_message(self, message: dict, connection_id: str):
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"❌ Failed to send message to {connection_id}: {e}")
                self.disconnect(connection_id)

manager = ConnectionManager()

async def call_ai_core_api(user_input: str, session_id: str, user_id: str, connection_id: str, agent_type: str = "academic_writing") -> dict:
    ai_core_url = os.getenv("AI_CORE_URL", "http://ai-core:8000")

    try:
        async with aiohttp.ClientSession() as session:
            # Configure payload based on agent type
            if agent_type == "academic_writing":
                payload = {
                    "version": "v1.0",
                    "query": f"[Academic Writing Assistant] {user_input}",
                    "session_id": f"academic_{session_id}",  # Prefix for academic writing sessions
                    "user_id": user_id,
                    "channel_id": f"academic_{session_id}",
                    "llm_model": "gemini-2.0-flash",
                    "token": "",
                    "agent_context": "academic_writing"
                }
            else:
                # Default general conversation
                payload = {
                    "version": "v1.0",
                    "query": user_input,
                    "session_id": session_id,
                    "user_id": user_id,
                    "channel_id": session_id,
                    "llm_model": "gemini-2.0-flash",
                    "token": ""
                }

            print(f"🚀 Calling AI Core with agent_type: {agent_type}, session_id: {payload['session_id']} (connection: {connection_id})")
            print(f"📦 Payload: {payload}")

            async with session.post(f"{ai_core_url}/api/execute", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ AI Core response received for session: {session_id}")
                    return {
                        "success": result.get("success", True),
                        "agent_response": result.get("llmOutput", "Response received from AI Core"),
                        "processing_time": result.get("response_time_ms", 1000) / 1000.0  # Convert ms to seconds
                    }
                else:
                    error_text = await response.text()
                    print(f"❌ AI Core API error {response.status} for session {session_id}: {error_text}")
                    return {
                        "success": False,
                        "agent_response": "Sorry, I'm having trouble processing your request.",
                        "processing_time": 0.5
                    }
    except Exception as e:
        print(f"❌ AI Core API call failed for session {session_id}: {e}")
        return {
            "success": False,
            "agent_response": "Sorry, I encountered an error processing your message.",
            "processing_time": 0.5
        }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "websocket",
        "active_connections": len(manager.active_connections),
        "active_sessions": len(manager.session_mapping),
        "session_details": {
            conn_id: {
                "session_id": info.get("session_id"),
                "connected_at": info.get("connected_at"),
                "message_count": info.get("message_count", 0),
                "agent_type": manager.get_agent_preference(conn_id)
            }
            for conn_id, info in manager.session_mapping.items()
        },
        "agent_distribution": {
            agent_type: sum(1 for pref in manager.agent_preferences.values() if pref == agent_type)
            for agent_type in ["academic_writing", "general_conversation", "research_assistant"]
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection_id = await manager.connect(websocket)
    session_info = manager.get_session_info(connection_id)

    # Send connection acknowledgment with session info
    await manager.send_personal_message({
        "type": "connection_ack",
        "data": {
            "connection_id": connection_id,
            "session_id": session_info.get("session_id", connection_id),
            "connected_at": session_info.get("connected_at"),
            "agent_type": manager.get_agent_preference(connection_id),
            "available_agents": ["academic_writing", "general_conversation", "research_assistant"]
        },
        "timestamp": datetime.now().isoformat()
    }, connection_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "restore_session":
                # Handle session restoration
                message_data = message.get("data", {})
                requested_session_id = message_data.get("session_id")

                if requested_session_id:
                    success = manager.restore_session(connection_id, requested_session_id)
                    if success:
                        session_info = manager.get_session_info(connection_id)
                        await manager.send_personal_message({
                            "type": "session_restored",
                            "data": {
                                "connection_id": connection_id,
                                "session_id": requested_session_id,
                                "restored_at": datetime.now().isoformat()
                            },
                            "timestamp": datetime.now().isoformat()
                        }, connection_id)

            elif message.get("type") == "set_agent":
                # Handle agent type switching
                message_data = message.get("data", {})
                new_agent_type = message_data.get("agent_type", "academic_writing")

                # Validate agent type
                valid_agents = ["academic_writing", "general_conversation", "research_assistant"]
                if new_agent_type not in valid_agents:
                    new_agent_type = "academic_writing"

                manager.set_agent_preference(connection_id, new_agent_type)

                await manager.send_personal_message({
                    "type": "agent_switched",
                    "data": {
                        "agent_type": new_agent_type,
                        "message": f"Switched to {new_agent_type.replace('_', ' ').title()} mode"
                    },
                    "timestamp": datetime.now().isoformat()
                }, connection_id)

            elif message.get("type") == "user_message":
                message_data = message.get("data", {})
                user_input = message_data.get("user_input", "")
                # Get agent type from message or use connection preference
                agent_type = message_data.get("agent_type", manager.get_agent_preference(connection_id))
                # Use the session_id from session mapping (could be restored or new)
                session_info = manager.get_session_info(connection_id)
                session_id = session_info.get("session_id", connection_id)
                user_id = message_data.get("user_id", "test_user")

                print(f"📨 Message received - Connection: {connection_id}, Session: {session_id}, Agent: {agent_type}")
                manager.increment_message_count(connection_id)

                # Send typing indicator
                await manager.send_personal_message({
                    "type": "typing_start",
                    "data": {},
                    "timestamp": datetime.now().isoformat()
                }, connection_id)

                # Process message via AI Core API with agent type
                result = await call_ai_core_api(user_input, session_id, user_id, connection_id, agent_type)

                # Send response
                await manager.send_personal_message({
                    "type": "agent_response",
                    "data": {
                        "message_id": str(uuid.uuid4()),
                        "session_id": session_id,
                        "user_id": user_id,
                        "user_input": user_input,
                        "agent_response": result["agent_response"],
                        "agent_type": agent_type,
                        "processing_time": result["processing_time"],
                        "success": result["success"],
                        "created_at": datetime.now().isoformat()
                    },
                    "timestamp": datetime.now().isoformat()
                }, connection_id)

                # Stop typing indicator
                await manager.send_personal_message({
                    "type": "typing_stop",
                    "data": {},
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
                
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        manager.disconnect(connection_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
