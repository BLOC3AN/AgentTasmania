# 🐳 **Docker Build Instructions - UTAS Writing Practice Frontend**

## 📋 **Overview**

This document provides comprehensive instructions for building and deploying the UTAS Writing Practice Frontend Service using Docker.

---

## 🚀 **Quick Start**

### **1. Production Build & Run**
```bash
# Build production image
npm run docker:build

# Run production container
npm run docker:run

# Or use docker-compose
docker-compose up frontend
```

### **2. Development Build & Run**
```bash
# Build and run development container with hot reload
npm run docker:dev

# Or use docker-compose
docker-compose --profile dev up frontend-dev
```

---

## 🏗️ **Build Process Details**

### **Multi-Stage Build Architecture**

1. **Base Stage**: Common dependencies and system packages
2. **Dependencies Stage**: NPM package installation
3. **Builder Stage**: Next.js application build
4. **Production Stage**: Optimized runtime image

### **Key Features**

- ✅ **Multi-service Support**: Runs both Next.js app (port 3000) and WebSocket server (port 8080)
- ✅ **Native Dependencies**: Supports audio processing libraries (wav, WebSocket)
- ✅ **Security**: Non-root user execution
- ✅ **Health Checks**: Built-in health monitoring
- ✅ **Optimized Size**: Multi-stage build reduces final image size
- ✅ **Production Ready**: Standalone Next.js output for better performance

---

## 🔧 **Build Commands**

### **Manual Docker Commands**
```bash
# Build production image
docker build -t utas-writing-practice .

# Build development image
docker build -f Dockerfile.dev -t utas-writing-practice-dev .

# Run production container
docker run -p 3000:3000 -p 8080:8080 utas-writing-practice

# Run development container with volume mounting
docker run -p 3000:3000 -v $(pwd):/app utas-writing-practice-dev
```

### **Docker Compose Commands**
```bash
# Production deployment
docker-compose up -d frontend

# Development with hot reload
docker-compose --profile dev up frontend-dev

# Build and run
docker-compose up --build

# Stop services
docker-compose down

# View logs
docker-compose logs -f frontend
```

---

## 🌐 **Environment Variables**

### **Production Environment**
```env
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
PORT=3000
HOSTNAME=0.0.0.0
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8080
```

### **Development Environment**
```env
NODE_ENV=development
NEXT_TELEMETRY_DISABLED=1
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8080
```

---

## 🔍 **Health Monitoring**

### **Health Check Endpoint**
- **URL**: `http://localhost:3000/api/health`
- **Method**: GET
- **Response**: JSON with service status, uptime, memory usage

### **Docker Health Check**
```bash
# Check container health
docker ps

# View health check logs
docker inspect <container_id> | grep Health -A 10
```

---

## 🐛 **Troubleshooting**

### **Common Build Issues**

1. **Native Dependencies Fail**
   ```bash
   # Solution: Ensure build tools are installed
   RUN apk add --no-cache python3 make g++
   ```

2. **Permission Errors**
   ```bash
   # Solution: Check file ownership
   docker exec -it <container> ls -la /app
   ```

3. **WebSocket Connection Issues**
   ```bash
   # Solution: Ensure both ports are exposed
   EXPOSE 3000 8080
   ```

4. **Build Cache Issues**
   ```bash
   # Solution: Clean build
   docker build --no-cache -t utas-writing-practice .
   ```

### **Debug Commands**
```bash
# Enter running container
docker exec -it <container_name> sh

# Check running processes
docker exec -it <container_name> ps aux

# View application logs
docker logs -f <container_name>

# Check network connectivity
docker exec -it <container_name> wget -O- http://localhost:3000/api/health
```

---

## 📊 **Performance Optimization**

### **Image Size Optimization**
- Multi-stage build reduces final image size
- `.dockerignore` excludes unnecessary files
- Standalone Next.js output for better performance

### **Runtime Optimization**
- Non-root user for security
- Health checks for monitoring
- Proper signal handling for graceful shutdown

---

## 🔒 **Security Considerations**

1. **Non-root User**: Application runs as `nextjs` user (UID 1001)
2. **Minimal Base Image**: Alpine Linux for smaller attack surface
3. **No Secrets in Image**: Environment variables for configuration
4. **Health Monitoring**: Regular health checks for early issue detection

---

## 📝 **File Structure**

```
frontend_service/
├── Dockerfile              # Production build
├── Dockerfile.dev          # Development build
├── docker-compose.yml      # Multi-service orchestration
├── .dockerignore           # Build exclusions
├── package.json            # Dependencies and scripts
├── next.config.ts          # Next.js configuration
├── websocket-server.js     # WebSocket server
└── src/
    └── app/
        └── api/
            └── health/
                └── route.ts # Health check endpoint
```

---

## ✅ **Verification Steps**

After successful build and deployment:

1. **Check Services**:
   - Next.js app: http://localhost:3000
   - Health check: http://localhost:3000/api/health
   - WebSocket server: ws://localhost:8080

2. **Test Functionality**:
   - Open chat interface
   - Test voice input functionality
   - Verify WebSocket connection

3. **Monitor Health**:
   - Check container status: `docker ps`
   - View logs: `docker logs <container>`
   - Test health endpoint: `curl http://localhost:3000/api/health`

---

## 🎯 **Production Deployment**

For production deployment, consider:

1. **Environment Variables**: Set appropriate values for production
2. **Reverse Proxy**: Use nginx or similar for SSL termination
3. **Monitoring**: Implement proper logging and monitoring
4. **Scaling**: Use orchestration tools like Kubernetes for scaling
5. **Security**: Regular security updates and vulnerability scanning

**🎉 Docker Build System Ready for Production!** 🚀
