# AgentTasmania - AI Academic Writing Assistant

Một hệ thống AI Agent chuyên về Academic Writing được xây dựng theo kiến trúc microservices với Next.js frontend, Python backend services, và WebSocket real-time communication.

## 🏗️ Kiến trúc Microservices

```
AgentTasmania/
├── AI_core/                    # AI Agent Service (Port 8000)
│   ├── src/
│   │   ├── llms/              # LLM integrations (Gemini)
│   │   ├── mcp_client/        # MCP client tools
│   │   ├── utils/             # Utilities & Logger
│   │   └── versions/          # API versioning
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── MCP_server/                 # MCP API Service (Port 8001)
│   ├── schema/                # Tool schemas
│   ├── utils/                 # Logger utilities
│   ├── server.py
│   ├── requirements.txt
│   └── Dockerfile
├── database_service/           # Vector Database Service (Port 8002)
│   ├── src/
│   │   ├── database/          # Qdrant client
│   │   ├── models/            # Pydantic schemas
│   │   └── utils/             # Logger
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── websocket_service/          # WebSocket Service (Port 8003)
│   ├── main.py                # Academic Writing Assistant routing
│   ├── requirements.txt
│   └── Dockerfile
├── monitor_service/            # Monitor Service (Port 8004)
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── embedding_service/          # Embedding Service (Port 8005)
│   ├── src/
│   │   ├── embedding/         # Model management
│   │   └── models/            # Schemas
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── ASR_service/                # ASR Service (Port 8006)
│   ├── main.py                # FastAPI ASR service
│   ├── export_onnx.py         # Model export script
│   ├── nginx.conf             # Load balancer config
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── frontend_service/           # Next.js Frontend (Port 3000)
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   ├── components/        # React components
│   │   └── types/             # TypeScript types
│   ├── Dockerfile             # Production build
│   ├── Dockerfile.dev         # Development with hot reload
│   ├── package.json
│   └── next.config.ts
├── docker-compose.yml          # Orchestration
├── deploy.sh                   # Deployment script
└── .env                        # Environment variables
```

## 🚀 Cách chạy

### Yêu cầu hệ thống
- Docker & Docker Compose
- Git

### Quick Start

1. **Clone repository:**
```bash
git clone <repository-url>
cd AgentTasmania
```

2. **Cấu hình environment:**
```bash
# Đảm bảo file .env có đầy đủ thông tin:
# - GOOGLE_API_KEY (Gemini API)
# - QDRANT_URL & QDRANT_CLOUD_API_KEY (cho vector database)
# - NEXT_PUBLIC_API_URL & NEXT_PUBLIC_WEBSOCKET_URL (cho frontend)
```

3. **Deploy toàn bộ hệ thống:**
```bash
# Khởi động tất cả services
docker compose down -v && docker compose up -d --build

# Hoặc sử dụng script deploy
chmod +x deploy.sh
./deploy.sh
```

### Service URLs
- **Frontend**: http://localhost:3000 (Next.js Academic Writing Interface)
- **AI Core**: http://localhost:8000 (Academic Writing Assistant API)
- **MCP Server**: http://localhost:8001 (Tool Discovery & Execution)
- **Vector Database**: http://localhost:8002 (Qdrant + Hybrid Search)
- **WebSocket**: ws://localhost:8003 (Real-time Chat with Agent Routing)
- **Monitor**: http://localhost:8004 (System Health Dashboard)
- **Embedding**: http://localhost:8005 (Text Embedding Service)
- **ASR**: http://localhost:8006 (Automatic Speech Recognition with Load Balancing)
- **Logs**: http://localhost:5555 (Dozzle Log Viewer)

### Development Mode

Để chạy từng service riêng lẻ:

```bash
# AI Core
cd AI_core
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# MCP Server
cd MCP_server
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001

# Database Service
cd database_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002

# WebSocket Service
cd websocket_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8003

# Monitor Service
cd monitor_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8004

# Embedding Service
cd embedding_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8005

# Frontend (Next.js)
cd frontend_service
npm install
npm run dev
```

## 🎯 Tính năng

### Core Features
- ✅ **Academic Writing Assistant**: AI chuyên về viết học thuật
- ✅ **Real-time Chat**: WebSocket với agent routing
- ✅ **Multi-Agent Support**: Academic Writing, General Chat, Research Assistant
- ✅ **AI Agent**: Gemini LLM integration với context switching
- ✅ **Vector Database**: Qdrant với hybrid search (dense + sparse)
- ✅ **Microservices**: Scalable architecture
- ✅ **Health Monitoring**: Comprehensive service monitoring
- ✅ **Docker Ready**: Full containerization với hot reload

### Services
- ✅ **AI Core**: LLM processing & academic writing logic
- ✅ **MCP Server**: Tool discovery & execution
- ✅ **Vector Database**: Qdrant với hybrid search (BM25 + embeddings)
- ✅ **Embedding**: Text embedding service với model caching
- ✅ **WebSocket**: Real-time communication với agent routing
- ✅ **Monitor**: System health & logging dashboard
- ✅ **Frontend**: Next.js TypeScript UI với hot reload
- ✅ **Text-to-Speech**: OpenAI TTS service với voice response

### Academic Writing Features
- ✅ **Agent Routing**: Tự động route chat qua Academic Writing Assistant
- ✅ **Session Management**: Separate sessions cho từng agent type
- ✅ **Context Switching**: Chuyển đổi giữa academic writing và general chat
- ✅ **Vietnamese Support**: Hỗ trợ tiếng Việt cho academic writing

## 🔧 Công nghệ sử dụng

### Backend
- **Python 3.11**: Core language
- **FastAPI**: Web framework
- **WebSockets**: Real-time communication
- **Qdrant**: Vector database
- **Gemini**: LLM provider
- **Docker**: Containerization

### Frontend
- **Next.js 15**: React framework với App Router
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling framework
- **WebSocket API**: Real-time connection với agent routing

### Infrastructure
- **Docker Compose**: Orchestration với development/production modes
- **Dozzle**: Real-time log viewer
- **Health Checks**: Comprehensive service monitoring
- **Hot Reload**: Development mode với volume mounts

## 📊 Monitoring & Logs

### Health Check Endpoints
```bash
curl http://localhost:8000/health  # AI Core
curl http://localhost:8001/health  # MCP Server
curl http://localhost:8002/health  # Vector Database
curl http://localhost:8003/health  # WebSocket (với agent distribution)
curl http://localhost:8004/health  # Monitor
curl http://localhost:8005/health  # Embedding Service
curl http://localhost:8007/health  # Text-to-Speech Service
curl http://localhost:3000/api/chat # Frontend API Health
```

### System Health Dashboard
```bash
curl http://localhost:8004/system-health
```

### Hybrid Search API

**New Feature**: Hybrid search endpoint combining dense embeddings and sparse BM25 vectors for improved search accuracy.

**Flow**: Text Query → Embedding Service → BM25 Encoding → Qdrant Hybrid Search → Results

```bash
# Test hybrid search endpoint
curl -X POST http://localhost:8002/hybrid-search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "your search query",
    "limit": 5,
    "score_threshold": 0.5,
    "user_id": "optional_user_id"
  }'
```

**Response Format**:
```json
{
  "results": [
    {
      "id": "document_id",
      "score": 0.574,
      "payload": {
        "text": "document content...",
        "user_id": "user_id",
        "title": "document title",
        "source": "source_file"
      }
    }
  ],
  "total_found": 2,
  "search_type": "dense_only|hybrid|sparse_only"
}
```

**Features**:
- Automatic fallback to dense-only search if BM25 not available
- Error handling for embedding service downtime
- User-specific filtering support
- Configurable score thresholds and result limits

### Text-to-Speech API

**New Feature**: Text-to-Speech service using OpenAI TTS API for voice responses in UI popup mode.

**Endpoints**:
```bash
# Synthesize speech from text
curl -X POST "http://localhost:8007/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "coral", "response_format": "mp3"}'

# Synthesize from AI response format
curl -X POST "http://localhost:8007/synthesize-from-ai-response" \
  -H "Content-Type: application/json" \
  -d '{"llmOutput": "AI response text"}'

# Get available voices
curl http://localhost:8007/voices
```

**Features**:
- Multiple voice options (alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer)
- Multiple audio formats (mp3, opus, aac, flac, wav, pcm)
- Speed control (0.25x to 4.0x)
- Automatic integration with voice modal in frontend
- Real-time audio playback in UI popup mode

### Service Logs
```bash
# Individual service logs
docker compose logs -f ai-core
docker compose logs -f mcp-server
docker compose logs -f vectordb
docker compose logs -f websocket
docker compose logs -f monitor
docker compose logs -f frontend
docker compose logs -f embedding
docker compose logs -f tts

# Real-time log viewer (recommended)
# Access: http://localhost:5555
```

## 🤖 Academic Writing Assistant Usage

### WebSocket Connection
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8003/ws');

// Switch to Academic Writing Assistant
ws.send(JSON.stringify({
  type: "set_agent",
  data: { agent_type: "academic_writing" }
}));

// Send academic writing query
ws.send(JSON.stringify({
  type: "user_message",
  data: {
    user_input: "Help me write an introduction for my research paper",
    agent_type: "academic_writing",
    user_id: "student123"
  }
}));
```

### Available Agent Types
- **`academic_writing`**: Academic Writing Assistant (default)
- **`general_conversation`**: General conversation
- **`research_assistant`**: Research assistant

### Frontend API
```bash
# Test chat API
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-conversation-id: test-session" \
  -d '{"message": "Help me write an academic essay"}'
```

## 🔧 Troubleshooting

### Common Issues

1. **Frontend API Connection Failed**
   - Check if AI Core service is running: `docker compose ps`
   - Verify internal Docker network: `docker compose logs frontend`
   - Test API directly: `curl http://localhost:8000/health`

2. **WebSocket Connection Failed**
   - Check if websocket service is running: `docker compose ps`
   - Verify port 8003 is accessible
   - Check agent routing: `curl http://localhost:8003/health`

3. **Qdrant Connection Error**
   - Verify QDRANT_URL and QDRANT_CLOUD_API_KEY in .env
   - Check database service logs: `docker compose logs vectordb`
   - Test hybrid search: `curl http://localhost:8002/health`

4. **Gemini API Error**
   - Verify GOOGLE_API_KEY in .env
   - Check AI Core service logs: `docker compose logs ai-core`

5. **Frontend Hot Reload Not Working**
   - Check volume mounts in docker-compose.yml
   - Verify file permissions: `docker compose logs frontend`

### Restart Services
```bash
# Restart specific service
docker compose restart [service-name]

# Restart all services
docker compose down && docker compose up -d

# Full rebuild (recommended after code changes)
docker compose down -v && docker compose up -d --build

# Restart only frontend (quick development)
docker compose stop frontend && docker compose up -d --build frontend
```

## 📝 Development Notes

### Architecture Decisions
- **Academic Writing Focus**: Specialized AI agent cho academic writing
- **Agent Routing**: WebSocket tự động route qua Academic Writing Assistant
- **Hot Reload**: Development mode với volume mounts cho rapid development
- **Microservice Communication**: HTTP/WebSocket between services
- **Error Handling**: Comprehensive logging và monitoring
- **Scalable Design**: Easy to add new agent types và services

### Development Workflow
```bash
# Development mode (recommended)
docker compose down -v && docker compose up -d --build

# Check all services
docker compose ps

# View logs in real-time
# Browser: http://localhost:5555

# Test Academic Writing Assistant
# Browser: http://localhost:3000
```

### Code Structure
- **Clean Implementation**: No helper functions, direct approach
- **Fixed Dependencies**: Locked versions for stability
- **TypeScript**: Full type safety trong frontend
- **Pydantic**: Schema validation trong backend services
- **Environment Variables**: Flexible configuration

## License
This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).  
See the [LICENSE](./LICENSE) file for details.
