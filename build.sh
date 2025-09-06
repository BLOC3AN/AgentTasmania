#!/bin/bash

# UTAS Writing Practice - Build Script
# This script provides easy commands to build and run the frontend service

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

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to build and run production
build_production() {
    print_status "Building and starting production environment..."
    check_docker
    docker-compose down
    docker-compose up --build -d
    print_success "Production environment is running at http://localhost:3000"
}

# Function to build and run development
build_development() {
    print_status "Building and starting development environment..."
    check_docker
    docker-compose -f docker-compose.dev.yml down
    docker-compose -f docker-compose.dev.yml up --build
}

# Function to stop all services
stop_services() {
    print_status "Stopping all services..."
    docker-compose down
    docker-compose -f docker-compose.dev.yml down
    print_success "All services stopped"
}

# Function to clean up Docker resources
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down
    docker-compose -f docker-compose.dev.yml down
    docker system prune -f
    print_success "Cleanup completed"
}

# Function to show logs
show_logs() {
    print_status "Showing logs for frontend service..."
    docker-compose logs -f frontend
}

# Function to build frontend image only
build_frontend() {
    print_status "Building frontend Docker image..."
    cd frontend
    docker build -t utas-writing-practice-frontend .
    cd ..
    print_success "Frontend image built successfully"
}

# Function to show help
show_help() {
    echo "UTAS Writing Practice - Build Script"
    echo ""
    echo "Usage: ./build.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  prod, production    Build and run production environment"
    echo "  dev, development    Build and run development environment"
    echo "  stop               Stop all running services"
    echo "  clean, cleanup     Clean up Docker resources"
    echo "  logs               Show logs for frontend service"
    echo "  build              Build frontend Docker image only"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./build.sh prod     # Start production environment"
    echo "  ./build.sh dev      # Start development environment"
    echo "  ./build.sh stop     # Stop all services"
}

# Main script logic
case "${1:-help}" in
    "prod"|"production")
        build_production
        ;;
    "dev"|"development")
        build_development
        ;;
    "stop")
        stop_services
        ;;
    "clean"|"cleanup")
        cleanup
        ;;
    "logs")
        show_logs
        ;;
    "build")
        build_frontend
        ;;
    "help"|*)
        show_help
        ;;
esac
