import os
import sys
from contextlib import asynccontextmanager
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.embedding.model_manager import EmbeddingModelManager
from src.models.schemas import (
    EmbedTextRequest, EmbedTextResponse,
    EmbedBatchRequest, EmbedBatchResponse,
    HealthResponse
)

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model manager
model_manager = None

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    global model_manager
    try:
        model_manager = EmbeddingModelManager()
        await model_manager.load_model()
        logger.info("Embedding service started successfully")
    except Exception as e:
        logger.error(f"Failed to start embedding service: {e}")
        raise

    yield

    # Shutdown
    logger.info("Embedding service shutting down")

app = FastAPI(
    title="Embedding Service",
    description="Text embedding service using sentence-transformers",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        if model_manager and model_manager.is_loaded():
            model_status = "loaded"
        else:
            model_status = "not_loaded"
    except Exception:
        model_status = "error"

    return HealthResponse(
        status="healthy",
        service="embedding",
        model_status=model_status
    )

@app.post("/embed", response_model=EmbedTextResponse)
async def embed_text(request: EmbedTextRequest):
    try:
        if not model_manager or not model_manager.is_loaded():
            raise HTTPException(status_code=503, detail="Model not loaded")

        embedding = await model_manager.encode_text(request.text)
        
        return EmbedTextResponse(
            text=request.text,
            embedding=embedding.tolist(),
            dimension=request.dimension
        )
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        raise HTTPException(status_code=500, detail="Failed to embed text")

@app.post("/embed-batch", response_model=EmbedBatchResponse)
async def embed_batch(request: EmbedBatchRequest):
    try:
        if not model_manager or not model_manager.is_loaded():
            raise HTTPException(status_code=503, detail="Model not loaded")

        embeddings = await model_manager.encode_batch(request.texts)
        
        results = []
        for i, (text, embedding) in enumerate(zip(request.texts, embeddings)):
            results.append({
                "text": text,
                "embedding": embedding.tolist(),
                "index": i
            })
        
        return EmbedBatchResponse(
            results=results,
            total_processed=len(results),
            dimension=len(embeddings[0]) if embeddings else 0
        )
    except Exception as e:
        logger.error(f"Error embedding batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to embed batch")

@app.get("/model-info")
async def get_model_info():
    try:
        if not model_manager or not model_manager.is_loaded():
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        return {
            "model_name": model_manager.model_name,
            "dimension": model_manager.get_dimension(),
            "max_sequence_length": model_manager.get_max_sequence_length()
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model info")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
