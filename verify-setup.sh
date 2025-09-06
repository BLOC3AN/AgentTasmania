#!/bin/bash

# UTAS Writing Practice - Setup Verification Script
# This script verifies that the project structure is correct

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        print_success "✓ $1 exists"
        return 0
    else
        print_error "✗ $1 missing"
        return 1
    fi
}

# Function to check if directory exists
check_directory() {
    if [ -d "$1" ]; then
        print_success "✓ $1/ directory exists"
        return 0
    else
        print_error "✗ $1/ directory missing"
        return 1
    fi
}

print_status "Verifying UTAS Writing Practice project structure..."
echo ""

# Check root files
print_status "Checking root configuration files..."
check_file "README.md"
check_file "docker-compose.yml"
check_file "docker-compose.dev.yml"
check_file "build.sh"
echo ""

# Check frontend directory structure
print_status "Checking frontend directory structure..."
check_directory "frontend"
check_directory "frontend/src"
check_directory "frontend/src/app"
check_directory "frontend/src/components"
check_directory "frontend/public"
echo ""

# Check frontend configuration files
print_status "Checking frontend configuration files..."
check_file "frontend/package.json"
check_file "frontend/package-lock.json"
check_file "frontend/next.config.ts"
check_file "frontend/tsconfig.json"
check_file "frontend/Dockerfile"
check_file "frontend/Dockerfile.dev"
check_file "frontend/.dockerignore"
echo ""

# Check source files
print_status "Checking source files..."
check_file "frontend/src/app/page.tsx"
check_file "frontend/src/app/layout.tsx"
check_file "frontend/src/app/globals.css"
check_file "frontend/src/components/ChatBox.tsx"
check_file "frontend/src/app/api/chat/route.ts"
echo ""

# Check if old files are removed from root
print_status "Verifying cleanup (these should NOT exist in root)..."
if [ -d "src" ]; then
    print_warning "✗ Old src/ directory still exists in root"
else
    print_success "✓ Old src/ directory removed from root"
fi

if [ -f "package.json" ]; then
    print_warning "✗ Old package.json still exists in root"
else
    print_success "✓ Old package.json removed from root"
fi

if [ -f "next.config.ts" ]; then
    print_warning "✗ Old next.config.ts still exists in root"
else
    print_success "✓ Old next.config.ts removed from root"
fi
echo ""

# Validate Docker Compose files
print_status "Validating Docker Compose configuration..."
if command -v docker-compose > /dev/null 2>&1; then
    if docker-compose config > /dev/null 2>&1; then
        print_success "✓ docker-compose.yml is valid"
    else
        print_error "✗ docker-compose.yml has syntax errors"
    fi
    
    if docker-compose -f docker-compose.dev.yml config > /dev/null 2>&1; then
        print_success "✓ docker-compose.dev.yml is valid"
    else
        print_error "✗ docker-compose.dev.yml has syntax errors"
    fi
else
    print_warning "⚠ docker-compose not available, skipping validation"
fi
echo ""

# Check Node.js configuration
print_status "Checking Node.js configuration..."
cd frontend
if [ -f "package.json" ]; then
    if command -v node > /dev/null 2>&1; then
        print_success "✓ Node.js is available"
        if command -v npm > /dev/null 2>&1; then
            print_success "✓ npm is available"
            # Check if dependencies can be resolved
            if npm ls > /dev/null 2>&1 || [ ! -d "node_modules" ]; then
                print_success "✓ Package configuration is valid"
            else
                print_warning "⚠ Some dependency issues detected (run 'npm install' in frontend/)"
            fi
        else
            print_warning "⚠ npm not available"
        fi
    else
        print_warning "⚠ Node.js not available"
    fi
fi
cd ..
echo ""

print_status "Verification complete!"
echo ""
print_status "Next steps:"
echo "1. Start Docker on your system"
echo "2. Run: ./build.sh dev    (for development)"
echo "3. Run: ./build.sh prod   (for production)"
echo "4. Access: http://localhost:3000"
