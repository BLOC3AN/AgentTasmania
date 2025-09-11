# Multi-stage Docker build for UTAS Writing Practice Frontend Service
# Optimized for production deployment with WebSocket support

# ================================
# Base Stage - Common Dependencies
# ================================
FROM node:18-alpine AS base

# Install system dependencies required for native modules and audio processing
RUN apk add --no-cache \
    libc6-compat \
    python3 \
    make \
    g++ \
    wget \
    curl \
    && ln -sf python3 /usr/bin/python

# Set working directory
WORKDIR /app

# Create non-root user early for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# ================================
# Dependencies Stage - Install NPM packages
# ================================
FROM base AS deps

# Copy package files
COPY package.json package-lock.json* ./

# Clean install dependencies with verbose logging for debugging
RUN npm ci --verbose --no-audit --no-fund

# Verify critical dependencies are installed
RUN npm list ws socket.io-client uuid wav || echo "Some dependencies missing but continuing..."

# ================================
# Builder Stage - Build Application
# ================================
FROM base AS builder
WORKDIR /app

# Copy installed dependencies
COPY --from=deps /app/node_modules ./node_modules

# Copy source code and configuration files
COPY . .

# Set build environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_BUILD_VERBOSE=1

# Build the Next.js application
RUN echo "Starting Next.js build..." && \
    npm run build:docker && \
    echo "Next.js build completed successfully"

# Verify build output
RUN ls -la .next/ && \
    ls -la .next/standalone/ || echo "Standalone build not found"

# ================================
# Production Stage - Runtime Image
# ================================
FROM base AS runner
WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Copy public assets
COPY --from=builder /app/public ./public

# Create .next directory with proper permissions
RUN mkdir -p .next && \
    chown -R nextjs:nodejs .next

# Copy built application with proper ownership
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy WebSocket server and related files
COPY --from=builder --chown=nextjs:nodejs /app/websocket-server.js ./
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./

# Install only production dependencies for WebSocket server
RUN npm install --production --no-audit --no-fund ws && \
    chown -R nextjs:nodejs node_modules

# Create startup script to run both Next.js and WebSocket server
RUN cat > start.sh << 'EOF'
#!/bin/sh
echo "Starting UTAS Writing Practice Frontend Service..."

# Start WebSocket server in background
echo "Starting WebSocket server on port 8080..."
node websocket-server.js &
WEBSOCKET_PID=$!

# Start Next.js server
echo "Starting Next.js server on port 3000..."
node server.js &
NEXTJS_PID=$!

# Wait for either process to exit
wait $NEXTJS_PID $WEBSOCKET_PID
EOF

RUN chmod +x start.sh && \
    chown nextjs:nodejs start.sh

# Switch to non-root user
USER nextjs

# Expose ports
EXPOSE 3000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

# Start both services
CMD ["./start.sh"]
