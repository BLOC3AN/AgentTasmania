#!/bin/bash

# =============================================================================
# AgentTasmania - Start All Services Script (Container-Friendly, No Sudo)
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

# Function to fix Python module structure
fix_python_modules() {
    local service_dir=$1
    local service_name=$2

    print_status "Fixing Python modules for $service_name..."

    # Create __init__.py files if missing
    find "$service_dir" -type d -name "src" -o -name "utils" -o -name "versions" -o -name "v1" | while read dir; do
        if [ ! -f "$dir/__init__.py" ]; then
            touch "$dir/__init__.py"
        fi
    done

    # Special handling for AI_core
    if [ "$service_name" = "AI Core" ]; then
        # Ensure all subdirectories have __init__.py
        find "$service_dir/src" -type d | while read dir; do
            if [ ! -f "$dir/__init__.py" ]; then
                touch "$dir/__init__.py"
            fi
        done
    fi
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

        # Fix Python modules after installing dependencies
        cd "$PROJECT_ROOT"
        fix_python_modules "$service_dir" "$service_name"

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
    # Fix PYTHONPATH to include both service directory and current directory
    export PYTHONPATH="$service_dir:$PWD:$PYTHONPATH"

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

# Function to install Node.js binary if needed
install_nodejs_if_needed() {
    if ! command -v node &> /dev/null || ! node --version &> /dev/null; then
        print_warning "Node.js not working properly. Installing from binary..."

        # Create bin directory
        mkdir -p ~/bin

        # Download Node.js v18 LTS
        NODE_VERSION="18.20.4"
        NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz"

        if command -v wget &> /dev/null; then
            wget "$NODE_URL" -O node.tar.xz
        elif command -v curl &> /dev/null; then
            curl -L "$NODE_URL" -o node.tar.xz
        else
            print_error "Cannot download Node.js. wget/curl not available"
            return 1
        fi

        # Extract and install
        tar -xf node.tar.xz
        cp -r "node-v${NODE_VERSION}-linux-x64"/* ~/bin/
        rm -rf node.tar.xz "node-v${NODE_VERSION}-linux-x64"

        # Update PATH
        export PATH="$HOME/bin/bin:$PATH"

        print_status "Node.js installed successfully!"
    fi
}

# Function to fix frontend package.json if needed
fix_frontend_package() {
    if [ -f "$PROJECT_ROOT/frontend_service/package.json" ]; then
        cd "$PROJECT_ROOT/frontend_service"

        # Check if we have problematic packages
        if grep -q "tailwindcss.*4" package.json || grep -q "next.*15" package.json; then
            print_warning "Fixing package.json for compatibility..."

            # Backup original
            cp package.json package.json.backup

            # Create compatible package.json
            cat > package.json << 'EOF'
{
  "name": "utas-writing-practice",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  },
  "dependencies": {
    "@types/ws": "^8.5.10",
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "socket.io-client": "^4.7.5",
    "uuid": "^9.0.1",
    "ws": "^8.17.1"
  },
  "devDependencies": {
    "@types/node": "^20.14.10",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@types/uuid": "^9.0.8",
    "autoprefixer": "^10.4.19",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.5",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.5.3"
  }
}
EOF
            print_status "Package.json fixed for compatibility"
        fi

        # Fix Next.js config file (convert .ts to .js)
        if [ -f "next.config.ts" ]; then
            print_warning "Converting next.config.ts to next.config.js..."

            # Backup original
            cp next.config.ts next.config.ts.backup

            # Create simple next.config.js
            cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  },
}

module.exports = nextConfig
EOF
            print_status "next.config.js created"
        fi

        # Fix postcss config
        if [ -f "postcss.config.mjs" ]; then
            print_warning "Converting postcss.config.mjs to postcss.config.js..."
            cat > postcss.config.js << 'EOF'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF
        fi

        # Create simple tailwind config
        cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

        # Fix layout.tsx font issue
        if [ -f "src/app/layout.tsx" ]; then
            print_warning "Fixing layout.tsx font issue..."

            # Backup original
            cp src/app/layout.tsx src/app/layout.tsx.backup

            # Create compatible layout.tsx
            cat > src/app/layout.tsx << 'EOF'
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UTAS Writing Practice",
  description: "AI-powered writing practice application",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
EOF
            print_status "layout.tsx fixed (removed Geist font)"
        fi

        # Fix globals.css if it has font imports
        if [ -f "src/app/globals.css" ]; then
            print_warning "Fixing globals.css..."

            # Create simple globals.css
            cat > src/app/globals.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-start-rgb: 214, 219, 220;
  --background-end-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-start-rgb: 0, 0, 0;
    --background-end-rgb: 0, 0, 0;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}
EOF
            print_status "globals.css fixed"
        fi

        cd "$PROJECT_ROOT"
    fi
}

# Function to check system dependencies
check_system_deps() {
    print_status "Checking system dependencies..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required but not installed!"
        print_error "Run: ./setup_container.sh to install dependencies"
        exit 1
    fi

    # Try to fix Node.js if needed
    install_nodejs_if_needed

    # Check Node.js again
    if ! command -v node &> /dev/null || ! node --version &> /dev/null; then
        print_warning "Node.js not available. Frontend service will be skipped."
        export SKIP_FRONTEND=true
    else
        print_status "Node.js version: $(node --version)"
        export SKIP_FRONTEND=false
    fi

    print_status "System dependencies check completed!"
}

# Function to start database services (Container-friendly)
start_databases() {
    print_status "Starting database services..."
    
    # Start PostgreSQL (if available)
    if command -v pg_ctl &> /dev/null; then
        print_service "Starting PostgreSQL..."
        
        # Create user postgres data directory if needed
        if [ ! -d ~/postgres_data ]; then
            mkdir -p ~/postgres_data
            print_status "Initializing PostgreSQL database..."
            initdb -D ~/postgres_data
        fi
        
        # Start PostgreSQL in user mode
        pg_ctl -D ~/postgres_data -l "$LOG_DIR/postgres.log" start
        echo "postgres:$(pgrep postgres)" >> "$PID_FILE"
        print_status "PostgreSQL started"
    else
        print_warning "PostgreSQL not found. Install with: ./setup_container.sh"
    fi
    
    # Start Redis (if available)
    if command -v redis-server &> /dev/null; then
        print_service "Starting Redis on port $REDIS_PORT..."
        redis-server --port $REDIS_PORT --daemonize yes --logfile "$LOG_DIR/redis.log" --dir ~/
        echo "redis:$(pgrep redis-server)" >> "$PID_FILE"
        print_status "Redis started"
    else
        print_warning "Redis not found. Install with: ./setup_container.sh"
    fi
    
    # Start Qdrant (if available)
    if command -v qdrant &> /dev/null; then
        print_service "Starting Qdrant on port $QDRANT_PORT..."
        mkdir -p ./data/qdrant
        qdrant --uri http://0.0.0.0:$QDRANT_PORT --storage-path ./data/qdrant > "$LOG_DIR/qdrant.log" 2>&1 &
        local qdrant_pid=$!
        echo "qdrant:$qdrant_pid" >> "$PID_FILE"
        print_status "Qdrant started with PID $qdrant_pid"
    else
        print_warning "Qdrant not found. Install with: ./setup_container.sh"
    fi
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
    print_status "Starting AgentTasmania services (Container mode)..."
    
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
    
    # Install frontend dependencies (if Node.js is available)
    if [ "$SKIP_FRONTEND" != "true" ]; then
        print_status "Installing frontend dependencies..."

        # Fix package.json first
        fix_frontend_package

        cd "$PROJECT_ROOT/frontend_service"

        # Clean up first
        rm -rf node_modules package-lock.json 2>/dev/null || true

        # Make sure we're using the right npm
        export PATH="$HOME/bin/bin:$PATH"

        # Try npm install with fallback options
        npm install --legacy-peer-deps --no-optional 2>/dev/null || {
            print_warning "npm install failed. Trying with different options..."
            npm install --force --no-optional 2>/dev/null || {
                print_warning "Standard npm install failed. Trying basic install..."
                npm install --no-optional --ignore-engines 2>/dev/null || {
                    print_error "Frontend dependencies installation failed. Skipping frontend service."
                    export SKIP_FRONTEND=true
                }
            }
        }
        cd "$PROJECT_ROOT"
    else
        print_warning "Skipping frontend dependencies installation (Node.js not available)"
    fi
    
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
    
    # Start frontend service (if available)
    if [ "$SKIP_FRONTEND" != "true" ]; then
        print_service "Starting Frontend service on port $FRONTEND_PORT..."
        cd "$PROJECT_ROOT/frontend_service"

        # Make sure we're using the right node/npm
        export PATH="$HOME/bin/bin:$PATH"

        # Try to start frontend with fallback
        npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
        local frontend_pid=$!
        echo "frontend:$frontend_pid" >> "$PID_FILE"
        cd "$PROJECT_ROOT"
        print_status "Frontend started with PID $frontend_pid"
    else
        print_warning "Skipping Frontend service (Node.js issues)"
    fi
    
    # Wait for services to be ready
    sleep 5
    print_status "Services started! Check logs in $LOG_DIR/"
    print_status "Services are running on the following ports:"
    echo "  - AI Core: http://localhost:$AI_CORE_PORT"
    echo "  - MCP Server: http://localhost:$MCP_SERVER_PORT"
    echo "  - Database: http://localhost:$DATABASE_PORT"
    echo "  - WebSocket: http://localhost:$WEBSOCKET_PORT"
    echo "  - Monitor: http://localhost:$MONITOR_PORT"
    echo "  - Embedding: http://localhost:$EMBEDDING_PORT"
    echo "  - ASR: http://localhost:$ASR_PORT"

    if [ "$SKIP_FRONTEND" != "true" ]; then
        echo "  - Frontend: http://localhost:$FRONTEND_PORT"
    else
        echo "  - Frontend: SKIPPED (Node.js issues)"
    fi
    
    print_status "To stop all services, run: ./start_services_container.sh stop"
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
        local pid=$(lsof -ti:$port 2>/dev/null)
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
