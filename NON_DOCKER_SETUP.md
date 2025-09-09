# AgentTasmania - Non-Docker Setup Guide

Hướng dẫn chạy toàn bộ hệ thống AgentTasmania mà không cần Docker.

## Tổng quan

Hệ thống bao gồm các service sau:

### Python Services (FastAPI)
- **AI Core** (Port 8000): Service AI chính
- **MCP Server** (Port 8001): Server MCP 
- **Database Service** (Port 8002): Service quản lý vector database
- **WebSocket Service** (Port 8003): Service WebSocket real-time
- **Monitor Service** (Port 8004): Service monitoring
- **Embedding Service** (Port 8005): Service embedding
- **ASR Service** (Port 8006): Service nhận dạng giọng nói

### Frontend Service
- **Frontend** (Port 3000): Next.js application

### Database Services
- **PostgreSQL** (Port 5433): Database chính
- **Redis** (Port 6389): Cache
- **Qdrant** (Port 6333): Vector database

## Cài đặt

### Bước 1: Cài đặt dependencies hệ thống

```bash
# Cấp quyền thực thi cho script
chmod +x setup_system.sh

# Chạy script cài đặt
./setup_system.sh
```

Script này sẽ tự động cài đặt:
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis
- Qdrant

### Bước 2: Cấu hình environment

Đảm bảo file `.env` đã được cấu hình đúng. Các biến quan trọng:

```env
# API Keys
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# Database
MONGODB_URI=your_mongodb_uri
REDIS_URL=redis://localhost:6389
QDRANT_LOCAL_URL=http://localhost:6333

# Service URLs (for local development)
AI_CORE_URL=http://localhost:8000
MCP_SERVER_URL=http://localhost:8001
DATABASE_URL=http://localhost:8002
WEBSOCKET_URL=http://localhost:8003
EMBEDDING_URL=http://localhost:8005
```

### Bước 3: Khởi động services

```bash
# Cấp quyền thực thi
chmod +x start_services.sh

# Khởi động tất cả services
./start_services.sh start
```

## Sử dụng

### Các lệnh cơ bản

```bash
# Khởi động tất cả services
./start_services.sh start

# Dừng tất cả services  
./start_services.sh stop

# Khởi động lại tất cả services
./start_services.sh restart

# Kiểm tra trạng thái services
./start_services.sh status
```

### Truy cập services

Sau khi khởi động thành công, bạn có thể truy cập:

- **Frontend**: http://localhost:3000
- **AI Core API**: http://localhost:8000
- **MCP Server**: http://localhost:8001
- **Database Service**: http://localhost:8002
- **WebSocket**: http://localhost:8003
- **Monitor**: http://localhost:8004
- **Embedding**: http://localhost:8005
- **ASR**: http://localhost:8006

### Kiểm tra logs

Logs của tất cả services được lưu trong thư mục `logs/`:

```bash
# Xem log của AI Core
tail -f logs/ai-core.log

# Xem log của Frontend
tail -f logs/frontend.log

# Xem tất cả logs
ls -la logs/
```

## Troubleshooting

### Lỗi port đã được sử dụng

```bash
# Kiểm tra process đang sử dụng port
lsof -i :8000

# Kill process theo PID
kill -9 <PID>

# Hoặc dừng tất cả services
./start_services.sh stop
```

### Lỗi dependencies

```bash
# Cài đặt lại dependencies cho service cụ thể
cd AI_core
source venv/bin/activate
pip install -r requirements.txt

# Cài đặt lại dependencies cho frontend
cd frontend_service
npm install
```

### Lỗi database connection

1. Kiểm tra PostgreSQL đang chạy:
```bash
# macOS
brew services list | grep postgresql

# Ubuntu
sudo systemctl status postgresql
```

2. Kiểm tra Redis đang chạy:
```bash
# macOS  
brew services list | grep redis

# Ubuntu
sudo systemctl status redis-server
```

3. Kiểm tra Qdrant đang chạy:
```bash
# Kiểm tra port 6333
lsof -i :6333
```

### Lỗi Python virtual environment

```bash
# Xóa và tạo lại virtual environment
cd AI_core
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Cấu trúc thư mục

```
AgentTasmania/
├── start_services.sh      # Script khởi động chính
├── setup_system.sh        # Script cài đặt hệ thống
├── NON_DOCKER_SETUP.md    # Hướng dẫn này
├── logs/                  # Thư mục logs
├── data/                  # Thư mục data
│   └── qdrant/           # Qdrant data
├── AI_core/              # Service AI Core
├── MCP_server/           # Service MCP Server
├── database_service/     # Service Database
├── websocket_service/    # Service WebSocket
├── embedding_service/    # Service Embedding
├── monitor_service/      # Service Monitor
├── ASR_service/          # Service ASR
└── frontend_service/     # Service Frontend
```

## Lưu ý quan trọng

1. **Thứ tự khởi động**: Script tự động khởi động services theo đúng thứ tự dependency
2. **Virtual environments**: Mỗi Python service có virtual environment riêng
3. **Logs**: Tất cả logs được lưu trong thư mục `logs/`
4. **PID tracking**: Script theo dõi PID của tất cả services trong file `services.pid`
5. **Port conflicts**: Script kiểm tra port conflicts trước khi khởi động
6. **Graceful shutdown**: Script dừng services một cách an toàn

## Hỗ trợ

Nếu gặp vấn đề, hãy:

1. Kiểm tra logs trong thư mục `logs/`
2. Chạy `./start_services.sh status` để xem trạng thái services
3. Đảm bảo tất cả dependencies đã được cài đặt đúng
4. Kiểm tra file `.env` có đầy đủ cấu hình

## Performance Tips

1. **Memory**: Hệ thống cần ít nhất 8GB RAM
2. **CPU**: Khuyến nghị 4+ cores
3. **Storage**: Cần ít nhất 10GB free space
4. **Network**: Đảm bảo các port không bị firewall block
