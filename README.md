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
- ✅ **Real-time Chat**: WebSocket-based communication
- ✅ **AI Agent**: Gemini LLM integration
- ✅ **Vector Database**: Qdrant cloud integration
- ✅ **Microservices**: Scalable architecture
- ✅ **Health Monitoring**: Service health tracking
- ✅ **Docker Ready**: Full containerization

### Services
- ✅ **AI Core**: LLM processing & agent logic
- ✅ **MCP Server**: Tool discovery & execution
- ✅ **Database**: Vector search & storage + **Hybrid Search**
- ✅ **Embedding**: Text embedding service
- ✅ **WebSocket**: Real-time communication
- ✅ **Monitor**: System health & logging
- ✅ **Frontend**: React TypeScript UI

## 🔧 Công nghệ sử dụng

### Backend
- **Python 3.11**: Core language
- **FastAPI**: Web framework
- **WebSockets**: Real-time communication
- **Qdrant**: Vector database
- **Gemini**: LLM provider
- **Docker**: Containerization

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool
- **WebSocket API**: Real-time connection

### Infrastructure
- **Docker Compose**: Orchestration
- **Nginx**: Reverse proxy
- **Health Checks**: Service monitoring

## 📊 Monitoring & Logs

### Health Check Endpoints
```bash
curl http://localhost:8000/health  # AI Core
curl http://localhost:8001/health  # MCP Server
curl http://localhost:8002/health  # Database
curl http://localhost:8003/health  # WebSocket
curl http://localhost:8004/health  # Monitor
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

### Service Logs
```bash
docker-compose logs -f ai-core
docker-compose logs -f mcp-server
docker-compose logs -f database
docker-compose logs -f websocket
docker-compose logs -f monitor
docker-compose logs -f frontend
```

## 🔧 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check if websocket service is running: `docker-compose ps`
   - Verify port 8003 is accessible

2. **Qdrant Connection Error**
   - Verify QDRANT_URL and QDRANT_CLOUD_API_KEY in .env
   - Check database service logs: `docker-compose logs database`

3. **Gemini API Error**
   - Verify GOOGLE_API_KEY in .env
   - Check AI Core service logs: `docker-compose logs ai-core`

### Restart Services
```bash
docker-compose restart [service-name]
# or restart all
docker-compose down && docker-compose up -d
```

## 📝 Development Notes

- **No Helper Functions**: Clean, direct implementation
- **Fixed Dependencies**: Locked versions for stability
- **Microservice Communication**: HTTP/WebSocket between services
- **Error Handling**: Comprehensive logging and monitoring
- **Scalable Design**: Easy to add new services
