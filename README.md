# UTAS Writing Practice - Frontend Service

A Next.js application for the University of Tasmania's Writing in Practice module (UPP014), featuring an interactive academic writing assistant.

## Project Structure

```
├── frontend/                 # Frontend Next.js application
│   ├── src/                 # Source code
│   │   ├── app/            # Next.js app directory
│   │   └── components/     # React components
│   ├── public/             # Static assets
│   ├── Dockerfile          # Production Docker configuration
│   ├── Dockerfile.dev      # Development Docker configuration
│   └── package.json        # Frontend dependencies
├── docker-compose.yml      # Production Docker Compose
├── docker-compose.dev.yml  # Development Docker Compose
└── README.md              # This file
```

## Prerequisites

- Docker and Docker Compose installed on your system
- Node.js 18+ (for local development)

## Quick Start with Docker

### Production Build

1. **Build and run the frontend service:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   - Frontend: http://localhost:3000

3. **Stop the services:**
   ```bash
   docker-compose down
   ```

### Development Mode

1. **Run in development mode with hot reloading:**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

2. **Access the application:**
   - Frontend: http://localhost:3000

## Manual Docker Commands

### Build Frontend Image
```bash
cd frontend
docker build -t utas-writing-practice-frontend .
```

### Run Frontend Container
```bash
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_UNIVERSITY_NAME="University of Tasmania" \
  -e NEXT_PUBLIC_MODULE_CODE="UPP014" \
  -e NEXT_PUBLIC_MODULE_NAME="Writing in Practice" \
  utas-writing-practice-frontend
```

## Local Development (without Docker)

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run development server:**
   ```bash
   npm run dev
   ```

4. **Build for production:**
   ```bash
   npm run build
   npm start
   ```

## Environment Variables

The following environment variables can be configured:

- `NEXT_PUBLIC_UNIVERSITY_NAME`: University name (default: "University of Tasmania")
- `NEXT_PUBLIC_MODULE_CODE`: Module code (default: "UPP014")
- `NEXT_PUBLIC_MODULE_NAME`: Module name (default: "Writing in Practice")

## Features

- **Interactive Learning Module**: Comprehensive content about academic writing and source integration
- **Chat Assistant**: AI-powered writing assistant for academic writing questions
- **Responsive Design**: Works on desktop and mobile devices
- **APA Style Guide**: Built-in guidance for APA referencing

## API Endpoints

- `GET /api/chat`: Health check for chat service
- `POST /api/chat`: Send message to writing assistant

## Adding a Backend Service

When you're ready to add a backend service:

1. **Create a backend directory:**
   ```bash
   mkdir backend
   ```

2. **Uncomment the backend service in docker-compose.yml**

3. **Update the frontend to connect to the backend API**

## Troubleshooting

### Port Already in Use
If port 3000 is already in use, modify the port mapping in docker-compose.yml:
```yaml
ports:
  - "3001:3000"  # Change 3001 to any available port
```

### Build Issues
Clear Docker cache and rebuild:
```bash
docker-compose down
docker system prune -f
docker-compose up --build
```

### Development Hot Reload Not Working
Ensure you're using the development compose file:
```bash
docker-compose -f docker-compose.dev.yml up --build
```

## Contributing

1. Make changes to the frontend code in the `frontend/` directory
2. Test locally using development mode
3. Build and test production image before deploying

## License

This project is for educational purposes as part of the University of Tasmania's UPP014 module.
