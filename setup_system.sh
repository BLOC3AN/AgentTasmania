#!/bin/bash

# =============================================================================
# AgentTasmania - System Setup Script
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

# Install Homebrew on macOS
install_homebrew() {
    if ! command -v brew &> /dev/null; then
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        print_status "Homebrew already installed"
    fi
}

# Install dependencies on macOS
install_macos_deps() {
    print_status "Installing dependencies on macOS..."
    
    install_homebrew
    
    # Update Homebrew
    brew update
    
    # Install Python 3
    if ! command -v python3 &> /dev/null; then
        print_status "Installing Python 3..."
        brew install python@3.11
    fi
    
    # Install Node.js
    if ! command -v node &> /dev/null; then
        print_status "Installing Node.js..."
        brew install node
    fi
    
    # Install PostgreSQL
    if ! command -v postgres &> /dev/null; then
        print_status "Installing PostgreSQL..."
        brew install postgresql@15
        brew services start postgresql@15
    fi
    
    # Install Redis
    if ! command -v redis-server &> /dev/null; then
        print_status "Installing Redis..."
        brew install redis
        brew services start redis
    fi
    
    # Install Qdrant
    if ! command -v qdrant &> /dev/null; then
        print_status "Installing Qdrant..."
        brew install qdrant
    fi
    
    print_status "macOS dependencies installed successfully!"
}

# Install dependencies on Ubuntu/Debian
install_ubuntu_deps() {
    print_status "Installing dependencies on Ubuntu/Debian..."
    
    # Update package list
    sudo apt-get update
    
    # Install Python 3 and pip
    if ! command -v python3 &> /dev/null; then
        print_status "Installing Python 3..."
        sudo apt-get install -y python3 python3-pip python3-venv
    fi
    
    # Install Node.js
    if ! command -v node &> /dev/null; then
        print_status "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    
    # Install PostgreSQL
    if ! command -v postgres &> /dev/null; then
        print_status "Installing PostgreSQL..."
        sudo apt-get install -y postgresql postgresql-contrib
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    fi
    
    # Install Redis
    if ! command -v redis-server &> /dev/null; then
        print_status "Installing Redis..."
        sudo apt-get install -y redis-server
        sudo systemctl start redis-server
        sudo systemctl enable redis-server
    fi
    
    # Install Qdrant
    if ! command -v qdrant &> /dev/null; then
        print_status "Installing Qdrant..."
        # Download and install Qdrant binary
        QDRANT_VERSION="v1.7.4"
        wget "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-gnu.tar.gz"
        tar -xzf "qdrant-x86_64-unknown-linux-gnu.tar.gz"
        sudo mv qdrant /usr/local/bin/
        rm "qdrant-x86_64-unknown-linux-gnu.tar.gz"
    fi
    
    print_status "Ubuntu dependencies installed successfully!"
}

# Install dependencies on CentOS/RHEL
install_centos_deps() {
    print_status "Installing dependencies on CentOS/RHEL..."
    
    # Update package list
    sudo yum update -y
    
    # Install Python 3
    if ! command -v python3 &> /dev/null; then
        print_status "Installing Python 3..."
        sudo yum install -y python3 python3-pip
    fi
    
    # Install Node.js
    if ! command -v node &> /dev/null; then
        print_status "Installing Node.js..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        sudo yum install -y nodejs
    fi
    
    # Install PostgreSQL
    if ! command -v postgres &> /dev/null; then
        print_status "Installing PostgreSQL..."
        sudo yum install -y postgresql-server postgresql-contrib
        sudo postgresql-setup initdb
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    fi
    
    # Install Redis
    if ! command -v redis-server &> /dev/null; then
        print_status "Installing Redis..."
        sudo yum install -y redis
        sudo systemctl start redis
        sudo systemctl enable redis
    fi
    
    print_status "CentOS dependencies installed successfully!"
}

# Setup PostgreSQL database
setup_postgresql() {
    print_status "Setting up PostgreSQL database..."
    
    # Create database and user (matching .env file)
    if command -v psql &> /dev/null; then
        # Try to create database
        sudo -u postgres psql -c "CREATE DATABASE mydb;" 2>/dev/null || true
        sudo -u postgres psql -c "CREATE USER admin WITH PASSWORD 'Hai@30032000';" 2>/dev/null || true
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mydb TO admin;" 2>/dev/null || true
        
        print_status "PostgreSQL database setup completed!"
    else
        print_warning "PostgreSQL not found. Please install it manually."
    fi
}

# Create Qdrant data directory
setup_qdrant() {
    print_status "Setting up Qdrant..."
    
    # Create data directory
    mkdir -p "./data/qdrant"
    
    print_status "Qdrant setup completed!"
}

# Main setup function
main() {
    print_status "Starting system setup for AgentTasmania..."
    
    OS=$(detect_os)
    print_status "Detected OS: $OS"
    
    case $OS in
        macos)
            install_macos_deps
            ;;
        ubuntu)
            install_ubuntu_deps
            ;;
        centos)
            install_centos_deps
            ;;
        *)
            print_error "Unsupported operating system: $OS"
            print_error "Please install the following manually:"
            echo "  - Python 3.11+"
            echo "  - Node.js 18+"
            echo "  - PostgreSQL 15+"
            echo "  - Redis"
            echo "  - Qdrant"
            exit 1
            ;;
    esac
    
    # Setup databases
    setup_postgresql
    setup_qdrant
    
    print_status "System setup completed successfully!"
    print_status "You can now run: ./start_services.sh to start all services"
    
    # Show next steps
    echo ""
    echo "Next steps:"
    echo "1. Make sure all services are properly configured in .env file"
    echo "2. Run: chmod +x start_services.sh"
    echo "3. Run: ./start_services.sh start"
    echo ""
    echo "To check service status: ./start_services.sh status"
    echo "To stop services: ./start_services.sh stop"
}

# Run main function
main "$@"
