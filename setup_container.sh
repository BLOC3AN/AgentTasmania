#!/bin/bash

# =============================================================================
# AgentTasmania - Container Setup Script (No Sudo Required)
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "ubuntu"
        elif [ -f /etc/redhat-release ]; then
            echo "centos"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

# Install Node.js from binary (container-friendly)
install_nodejs_binary() {
    if ! command -v node &> /dev/null; then
        print_status "Installing Node.js from binary..."
        NODE_VERSION="18.19.0"
        
        # Create local bin directory
        mkdir -p ~/bin
        
        # Download and extract Node.js
        if command -v wget &> /dev/null; then
            wget "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" -O node.tar.xz
        elif command -v curl &> /dev/null; then
            curl -L "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" -o node.tar.xz
        else
            print_error "Neither wget nor curl available. Cannot download Node.js"
            return 1
        fi
        
        tar -xf node.tar.xz
        cp -r "node-v${NODE_VERSION}-linux-x64"/* ~/bin/
        rm -rf node.tar.xz "node-v${NODE_VERSION}-linux-x64"
        
        # Add to PATH
        export PATH="$HOME/bin/bin:$PATH"
        echo 'export PATH="$HOME/bin/bin:$PATH"' >> ~/.bashrc
        
        print_status "Node.js installed successfully"
    else
        print_status "Node.js already available"
    fi
}

# Install Redis from source (container-friendly)
install_redis_binary() {
    if ! command -v redis-server &> /dev/null; then
        print_status "Installing Redis from source..."
        REDIS_VERSION="7.2.4"
        
        # Create local bin directory
        mkdir -p ~/bin
        
        # Download and compile Redis
        if command -v wget &> /dev/null; then
            wget "http://download.redis.io/releases/redis-${REDIS_VERSION}.tar.gz" -O redis.tar.gz
        elif command -v curl &> /dev/null; then
            curl -L "http://download.redis.io/releases/redis-${REDIS_VERSION}.tar.gz" -o redis.tar.gz
        else
            print_warning "Cannot download Redis. wget/curl not available"
            return 1
        fi
        
        tar -xzf redis.tar.gz
        cd "redis-${REDIS_VERSION}"
        
        # Try to compile
        if command -v make &> /dev/null && command -v gcc &> /dev/null; then
            make
            cp src/redis-server ~/bin/
            cp src/redis-cli ~/bin/
            print_status "Redis compiled and installed successfully"
        else
            print_warning "Cannot compile Redis. make/gcc not available"
        fi
        
        cd ..
        rm -rf redis.tar.gz "redis-${REDIS_VERSION}"
        
        # Add to PATH
        export PATH="$HOME/bin:$PATH"
        echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
    else
        print_status "Redis already available"
    fi
}

# Install Qdrant binary (container-friendly)
install_qdrant_binary() {
    if ! command -v qdrant &> /dev/null; then
        print_status "Installing Qdrant binary..."
        QDRANT_VERSION="v1.7.4"
        
        # Create local bin directory
        mkdir -p ~/bin
        
        # Download Qdrant
        if command -v wget &> /dev/null; then
            wget "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-gnu.tar.gz" -O qdrant.tar.gz
        elif command -v curl &> /dev/null; then
            curl -L "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-gnu.tar.gz" -o qdrant.tar.gz
        else
            print_error "Cannot download Qdrant. wget/curl not available"
            return 1
        fi
        
        tar -xzf qdrant.tar.gz
        mv qdrant ~/bin/
        rm qdrant.tar.gz
        
        # Add to PATH
        export PATH="$HOME/bin:$PATH"
        echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
        
        print_status "Qdrant installed successfully"
    else
        print_status "Qdrant already available"
    fi
}

# Try package manager installation (if available)
try_package_install() {
    print_status "Trying package manager installation..."
    
    # Try apt-get (Ubuntu/Debian)
    if command -v apt-get &> /dev/null; then
        print_status "Using apt-get package manager..."
        
        # Update package list
        apt-get update 2>/dev/null || print_warning "Cannot update package list"
        
        # Install Python 3
        if ! command -v python3 &> /dev/null; then
            apt-get install -y python3 python3-pip python3-venv 2>/dev/null || print_warning "Cannot install Python3 via apt"
        fi
        
        # Install Node.js
        if ! command -v node &> /dev/null; then
            apt-get install -y nodejs npm 2>/dev/null || {
                print_warning "Cannot install Node.js via apt, will use binary"
                install_nodejs_binary
            }
        fi
        
        # Install PostgreSQL
        if ! command -v postgres &> /dev/null && ! command -v pg_ctl &> /dev/null; then
            apt-get install -y postgresql postgresql-contrib 2>/dev/null || print_warning "Cannot install PostgreSQL via apt"
        fi
        
        # Install Redis
        if ! command -v redis-server &> /dev/null; then
            apt-get install -y redis-server 2>/dev/null || {
                print_warning "Cannot install Redis via apt, will use binary"
                install_redis_binary
            }
        fi
        
    # Try yum (CentOS/RHEL)
    elif command -v yum &> /dev/null; then
        print_status "Using yum package manager..."
        
        yum update -y 2>/dev/null || print_warning "Cannot update package list"
        
        # Install Python 3
        if ! command -v python3 &> /dev/null; then
            yum install -y python3 python3-pip 2>/dev/null || print_warning "Cannot install Python3 via yum"
        fi
        
        # Install Node.js
        if ! command -v node &> /dev/null; then
            yum install -y nodejs npm 2>/dev/null || {
                print_warning "Cannot install Node.js via yum, will use binary"
                install_nodejs_binary
            }
        fi
        
        # Install PostgreSQL
        if ! command -v postgres &> /dev/null; then
            yum install -y postgresql-server postgresql-contrib 2>/dev/null || print_warning "Cannot install PostgreSQL via yum"
        fi
        
        # Install Redis
        if ! command -v redis-server &> /dev/null; then
            yum install -y redis 2>/dev/null || {
                print_warning "Cannot install Redis via yum, will use binary"
                install_redis_binary
            }
        fi
        
    else
        print_warning "No supported package manager found. Will use binary installations."
        install_nodejs_binary
        install_redis_binary
    fi
    
    # Always try to install Qdrant from binary
    install_qdrant_binary
}

# Setup PostgreSQL database (container-friendly)
setup_postgresql() {
    print_status "Setting up PostgreSQL database..."
    
    if command -v psql &> /dev/null; then
        # Try to create database without sudo
        psql -c "CREATE DATABASE mydb;" 2>/dev/null || print_warning "Cannot create database (may already exist)"
        psql -c "CREATE USER admin WITH PASSWORD 'Hai@30032000';" 2>/dev/null || print_warning "Cannot create user (may already exist)"
        psql -c "GRANT ALL PRIVILEGES ON DATABASE mydb TO admin;" 2>/dev/null || print_warning "Cannot grant privileges"
        
        print_status "PostgreSQL database setup completed!"
    else
        print_warning "PostgreSQL not found. Database setup skipped."
    fi
}

# Create Qdrant data directory
setup_qdrant() {
    print_status "Setting up Qdrant..."
    mkdir -p "./data/qdrant"
    print_status "Qdrant data directory created!"
}

# Main setup function
main() {
    print_status "Starting container-friendly setup for AgentTasmania..."
    
    OS=$(detect_os)
    print_status "Detected OS: $OS"
    
    # Check basic requirements
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required but not found!"
        print_error "Please install Python3 in your container first."
        exit 1
    fi
    
    # Try package manager installation
    try_package_install
    
    # Setup databases
    setup_postgresql
    setup_qdrant
    
    # Update PATH in current session
    export PATH="$HOME/bin:$HOME/bin/bin:$PATH"
    
    print_status "Container setup completed successfully!"
    print_status "You can now run: ./start_services.sh to start all services"
    
    # Show next steps
    echo ""
    echo "Next steps:"
    echo "1. Source your bashrc: source ~/.bashrc"
    echo "2. Make sure all services are properly configured in .env file"
    echo "3. Run: chmod +x start_services.sh"
    echo "4. Run: ./start_services.sh start"
    echo ""
    echo "To check service status: ./start_services.sh status"
    echo "To stop services: ./start_services.sh stop"
}

# Run main function
main "$@"
