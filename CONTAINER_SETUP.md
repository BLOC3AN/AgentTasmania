# AgentTasmania - Container Setup Guide (No Sudo Required)

Hướng dẫn chạy toàn bộ hệ thống AgentTasmania trong container mà không cần sudo.

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
- **PostgreSQL** (Port 5433): Database chính (user mode)
- **Redis** (Port 6389): Cache
- **Qdrant** (Port 6333): Vector database

## Cài đặt trong Container

### Bước 1: Cài đặt dependencies hệ thống

```bash
# Cấp quyền thực thi cho script
chmod +x setup_container.sh

# Chạy script cài đặt (không cần sudo)
./setup_container.sh
```

Script này sẽ tự động:
- Thử cài đặt qua package manager (nếu có quyền)
- Tải và cài đặt binary nếu package manager không khả dụng
- Cài đặt Node.js, Redis, Qdrant từ binary
- Thiết lập PostgreSQL ở user mode

### Bước 2: Cấu hình environment

Đảm bảo file `.env` đã được cấu hình đúng:

```env
# API Keys
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# Database (Container-friendly URLs)
MONGODB_URI=your_mongodb_uri
REDIS_URL=redis://localhost:6389
QDRANT_LOCAL_URL=http://localhost:6333

# Service URLs (for container development)
AI_CORE_URL=http://localhost:8000
MCP_SERVER_URL=http://localhost:8001
DATABASE_URL=http://localhost:8002
WEBSOCKET_URL=http://localhost:8003
EMBEDDING_URL=http://localhost:8005
```

### Bước 3: Khởi động services

```bash
# Cấp quyền thực thi
chmod +x start_services_container.sh

# Khởi động tất cả services
./start_services_container.sh start
```

## Sử dụng

### Các lệnh cơ bản

```bash
# Khởi động tất cả services
./start_services_container.sh start

# Dừng tất cả services  
./start_services_container.sh stop

# Khởi động lại tất cả services
./start_services_container.sh restart

# Kiểm tra trạng thái services
./start_services_container.sh status
```

### Truy cập services

Sau khi khởi động thành công:

- **Frontend**: http://localhost:3000
- **AI Core API**: http://localhost:8000
- **MCP Server**: http://localhost:8001
- **Database Service**: http://localhost:8002
- **WebSocket**: http://localhost:8003
- **Monitor**: http://localhost:8004
- **Embedding**: http://localhost:8005
- **ASR**: http://localhost:8006

### Kiểm tra logs

```bash
# Xem log của AI Core
tail -f logs/ai-core.log

# Xem log của Frontend
tail -f logs/frontend.log

# Xem tất cả logs
ls -la logs/
```

## Đặc điểm Container-Friendly

### 1. Không cần sudo
- Tất cả cài đặt và chạy service không cần quyền root
- Sử dụng user home directory cho data và binaries

### 2. Binary installations
- Node.js: Tải và giải nén binary vào ~/bin
- Redis: Compile từ source hoặc dùng binary
- Qdrant: Tải binary từ GitHub releases
- PostgreSQL: Chạy ở user mode với data trong ~/postgres_data

### 3. Flexible package management
- Thử package manager trước (apt-get, yum)
- Fallback sang binary installation nếu không có quyền
- Tự động thêm PATH vào ~/.bashrc

### 4. Container-aware paths
- Logs: ./logs/
- Data: ./data/ và ~/
- Binaries: ~/bin/
- Virtual environments: service_dir/venv/

## Troubleshooting

### Lỗi không tìm thấy command

```bash
# Reload PATH
source ~/.bashrc

# Kiểm tra PATH
echo $PATH

# Kiểm tra binary location
ls -la ~/bin/
```

### Lỗi PostgreSQL

```bash
# Kiểm tra PostgreSQL data directory
ls -la ~/postgres_data/

# Khởi động lại PostgreSQL
pg_ctl -D ~/postgres_data restart
```

### Lỗi Redis

```bash
# Kiểm tra Redis process
ps aux | grep redis

# Khởi động lại Redis
redis-server --port 6389 --daemonize yes
```

### Lỗi dependencies

```bash
# Cài đặt lại dependencies cho service cụ thể
cd AI_core
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Lỗi port đã được sử dụng

```bash
# Kiểm tra process đang sử dụng port
lsof -i :8000

# Kill process theo PID
kill -9 <PID>

# Hoặc dừng tất cả services
./start_services_container.sh stop
```

## Container Environment Variables

Các biến môi trường hữu ích trong container:

```bash
# Thêm vào ~/.bashrc
export PATH="$HOME/bin:$HOME/bin/bin:$PATH"
export PYTHONPATH="$PWD:$PYTHONPATH"
export NODE_ENV=development
```

## Performance trong Container

### Memory Usage
- Mỗi Python service: ~200-500MB
- Frontend (Node.js): ~300-800MB
- PostgreSQL: ~100-300MB
- Redis: ~50-100MB
- Qdrant: ~200-500MB
- **Total**: ~1.5-3GB RAM

### CPU Usage
- Khuyến nghị: 2+ cores
- AI services có thể sử dụng nhiều CPU khi xử lý

### Storage
- Logs: ~100MB/day
- Database: ~500MB-2GB
- Models: ~1-5GB
- **Total**: ~2-8GB storage

## Lưu ý quan trọng

1. **Container restart**: Services sẽ cần khởi động lại sau khi container restart
2. **Data persistence**: Sử dụng volumes để persist data
3. **Network**: Đảm bảo ports được expose từ container
4. **Environment**: Source ~/.bashrc sau khi cài đặt
5. **Logs rotation**: Thiết lập log rotation để tránh đầy disk

## Script Files

- `setup_container.sh`: Cài đặt dependencies (no sudo)
- `start_services_container.sh`: Quản lý services
- `CONTAINER_SETUP.md`: Hướng dẫn này

## Next Steps

1. Chạy setup: `./setup_container.sh`
2. Source bashrc: `source ~/.bashrc`
3. Start services: `./start_services_container.sh start`
4. Check status: `./start_services_container.sh status`
5. Access frontend: http://localhost:3000
