#!/bin/bash

# =============================================================================
# AgentTasmania - Start All Services Script (Non-Docker)
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT=$(pwd)
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$PROJECT_ROOT/services.pid"

# Service ports (matching docker-compose.yml)
AI_CORE_PORT=8000
MCP_SERVER_PORT=8001
DATABASE_PORT=8002
WEBSOCKET_PORT=8003
MONITOR_PORT=8004
EMBEDDING_PORT=8005
ASR_PORT=8006
FRONTEND_PORT=3000
POSTGRES_PORT=5433
REDIS_PORT=6389
QDRANT_PORT=6333

# Create logs directory
mkdir -p "$LOG_DIR"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_service() {
    echo -e "${BLUE}[SERVICE]${NC} $1"
}

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_error "Port $port is already in use!"
        return 1
    fi
    return 0
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_status "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within timeout!"
    return 1
}

# Function to install Python dependencies
install_python_deps() {
    local service_dir=$1
    local service_name=$2
    
    print_status "Installing dependencies for $service_name..."
    
    if [ -f "$service_dir/requirements.txt" ]; then
        cd "$service_dir"
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        source venv/bin/activate
        pip install -r requirements.txt
        cd "$PROJECT_ROOT"
    else
        print_warning "No requirements.txt found for $service_name"
    fi
}

# Function to start a Python service
start_python_service() {
    local service_dir=$1
    local service_name=$2
    local port=$3
    local main_file=$4
    
    print_service "Starting $service_name on port $port..."
    
    cd "$service_dir"
    source venv/bin/activate
    
    # Set environment variables
    export API_PORT=$port
    export PYTHONPATH="$service_dir:$PYTHONPATH"
    
    # Start service in background
    if [ "$main_file" = "server.py" ]; then
        uvicorn server:app --host 0.0.0.0 --port $port > "$LOG_DIR/$service_name.log" 2>&1 &
    else
        uvicorn main:app --host 0.0.0.0 --port $port > "$LOG_DIR/$service_name.log" 2>&1 &
    fi
    
    local pid=$!
    echo "$service_name:$pid" >> "$PID_FILE"
    
    cd "$PROJECT_ROOT"
    print_status "$service_name started with PID $pid"
}

# Function to check and install system dependencies
check_system_deps() {
    print_status "Checking system dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required but not installed!"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is required but not installed!"
        exit 1
    fi
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is required but not installed!"
        exit 1
    fi
    
    # Check if PostgreSQL is installed
    if ! command -v postgres &> /dev/null && ! command -v pg_ctl &> /dev/null; then
        print_warning "PostgreSQL not found. Please install PostgreSQL manually."
        print_warning "On macOS: brew install postgresql"
        print_warning "On Ubuntu:  apt-get install postgresql postgresql-contrib"
    fi
    
    # Check if Redis is installed
    if ! command -v redis-server &> /dev/null; then
        print_warning "Redis not found. Please install Redis manually."
        print_warning "On macOS: brew install redis"
        print_warning "On Ubuntu:  apt-get install redis-server"
    fi
    
    print_status "System dependencies check completed!"
}

# Function to start database services
start_databases() {
    print_status "Starting database services..."
    
    # Start PostgreSQL (if available)
    if command -v pg_ctl &> /dev/null; then
        print_service "Starting PostgreSQL..."
        # Try to start PostgreSQL on custom port
        if [ -d "/usr/local/var/postgres" ]; then
            pg_ctl -D /usr/local/var/postgres -l "$LOG_DIR/postgres.log" start
        elif [ -d "/var/lib/postgresql/data" ]; then
             -u postgres pg_ctl -D /var/lib/postgresql/data -l "$LOG_DIR/postgres.log" start
        fi
    fi
    
    # Start Redis (if available)
    if command -v redis-server &> /dev/null; then
        print_service "Starting Redis on port $REDIS_PORT..."
        redis-server --port $REDIS_PORT --daemonize yes --logfile "$LOG_DIR/redis.log"
        echo "redis:$(pgrep redis-server)" >> "$PID_FILE"
    fi
    
    # Note: Qdrant needs to be installed separately
    print_warning "Qdrant needs to be installed and started manually on port $QDRANT_PORT"
    print_warning "Download from: https://github.com/qdrant/qdrant/releases"
}

# Function to check required ports
check_ports() {
    print_status "Checking if required ports are available..."
    
    local ports=($AI_CORE_PORT $MCP_SERVER_PORT $DATABASE_PORT $WEBSOCKET_PORT $MONITOR_PORT $EMBEDDING_PORT $ASR_PORT $FRONTEND_PORT)
    
    for port in "${ports[@]}"; do
        if ! check_port $port; then
            print_error "Please free up port $port before starting services"
            exit 1
        fi
    done
    
    print_status "All required ports are available!"
}

# Main start function
start_services() {
    print_status "Starting AgentTasmania services..."
    
    # Clean up any existing PID file
    rm -f "$PID_FILE"
    
    # Check system dependencies
    check_system_deps
    
    # Check ports
    check_ports
    
    # Start databases
    start_databases
    
    # Install dependencies for all Python services
    print_status "Installing Python dependencies..."
    install_python_deps "$PROJECT_ROOT/AI_core" "AI Core"
    install_python_deps "$PROJECT_ROOT/MCP_server" "MCP Server"
    install_python_deps "$PROJECT_ROOT/database_service" "Database Service"
    install_python_deps "$PROJECT_ROOT/websocket_service" "WebSocket Service"
    install_python_deps "$PROJECT_ROOT/embedding_service" "Embedding Service"
    install_python_deps "$PROJECT_ROOT/monitor_service" "Monitor Service"
    install_python_deps "$PROJECT_ROOT/ASR_service" "ASR Service"
    
    # Install frontend dependencies
    print_status "Installing frontend dependencies..."
    cd "$PROJECT_ROOT/frontend_service"
    npm install
    cd "$PROJECT_ROOT"
    
    # Start Python services in order
    print_status "Starting Python services..."
    
    # Start core services first
    start_python_service "$PROJECT_ROOT/embedding_service" "embedding" $EMBEDDING_PORT "main.py"
    sleep 3
    
    start_python_service "$PROJECT_ROOT/database_service" "database" $DATABASE_PORT "main.py"
    sleep 3
    
    start_python_service "$PROJECT_ROOT/MCP_server" "mcp-server" $MCP_SERVER_PORT "server.py"
    sleep 3
    
    start_python_service "$PROJECT_ROOT/AI_core" "ai-core" $AI_CORE_PORT "main.py"
    sleep 3
    
    start_python_service "$PROJECT_ROOT/websocket_service" "websocket" $WEBSOCKET_PORT "main.py"
    sleep 3
    
    start_python_service "$PROJECT_ROOT/ASR_service" "asr" $ASR_PORT "main.py"
    sleep 3
    
    start_python_service "$PROJECT_ROOT/monitor_service" "monitor" $MONITOR_PORT "main.py"
    sleep 3
    
    # Start frontend service
    print_service "Starting Frontend service on port $FRONTEND_PORT..."
    cd "$PROJECT_ROOT/frontend_service"
    npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    local frontend_pid=$!
    echo "frontend:$frontend_pid" >> "$PID_FILE"
    cd "$PROJECT_ROOT"
    print_status "Frontend started with PID $frontend_pid"
    
    # Wait for services to be ready
    sleep 5
    print_status "All services started! Check logs in $LOG_DIR/"
    print_status "Services are running on the following ports:"
    echo "  - AI Core: http://localhost:$AI_CORE_PORT"
    echo "  - MCP Server: http://localhost:$MCP_SERVER_PORT"
    echo "  - Database: http://localhost:$DATABASE_PORT"
    echo "  - WebSocket: http://localhost:$WEBSOCKET_PORT"
    echo "  - Monitor: http://localhost:$MONITOR_PORT"
    echo "  - Embedding: http://localhost:$EMBEDDING_PORT"
    echo "  - ASR: http://localhost:$ASR_PORT"
    echo "  - Frontend: http://localhost:$FRONTEND_PORT"
    
    print_status "To stop all services, run: ./start_services.sh stop"
}

# Function to stop all services
stop_services() {
    print_status "Stopping all services..."
    
    if [ -f "$PID_FILE" ]; then
        while IFS=':' read -r service_name pid; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                print_status "Stopping $service_name (PID: $pid)..."
                kill "$pid"
                sleep 2
                # Force kill if still running
                if kill -0 "$pid" 2>/dev/null; then
                    kill -9 "$pid"
                fi
            fi
        done < "$PID_FILE"
        
        rm -f "$PID_FILE"
    fi
    
    # Stop any remaining processes on our ports
    local ports=($AI_CORE_PORT $MCP_SERVER_PORT $DATABASE_PORT $WEBSOCKET_PORT $MONITOR_PORT $EMBEDDING_PORT $ASR_PORT $FRONTEND_PORT)
    
    for port in "${ports[@]}"; do
        local pid=$(lsof -ti:$port)
        if [ -n "$pid" ]; then
            print_status "Killing process on port $port (PID: $pid)..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    
    print_status "All services stopped!"
}

# Function to show service status
show_status() {
    print_status "Service Status:"
    
    local ports=($AI_CORE_PORT $MCP_SERVER_PORT $DATABASE_PORT $WEBSOCKET_PORT $MONITOR_PORT $EMBEDDING_PORT $ASR_PORT $FRONTEND_PORT)
    local names=("AI Core" "MCP Server" "Database" "WebSocket" "Monitor" "Embedding" "ASR" "Frontend")
    
    for i in "${!ports[@]}"; do
        local port=${ports[$i]}
        local name=${names[$i]}
        local pid=$(lsof -ti:$port 2>/dev/null)
        
        if [ -n "$pid" ]; then
            echo -e "  ${GREEN}✓${NC} $name (Port $port) - PID: $pid"
        else
            echo -e "  ${RED}✗${NC} $name (Port $port) - Not running"
        fi
    done
}

# Main script logic
case "${1:-start}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 3
        start_services
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo "  start   - Start all services (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show service status"
        exit 1
        ;;
esac
