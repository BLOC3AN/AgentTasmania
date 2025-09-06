import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.versions.router import router as versions_router
from src.utils.logger import Logger

load_dotenv()
logger = Logger(__name__)

app = FastAPI(
    title="AI Core Agent Service",
    description="AI Agent processing service with LLM and MCP integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(versions_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-core",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)