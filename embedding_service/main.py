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
from src.embedding.hybrid_model_manager import HybridModelManager
from src.models.schemas import (
    EmbedTextRequest, EmbedTextResponse,
    EmbedBatchRequest, EmbedBatchResponse,
    EmbedHybridRequest, EmbedHybridResponse,
    HealthResponse
)

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model managers
model_manager = None
hybrid_model_manager = None

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    global model_manager, hybrid_model_manager
    try:
        # Load legacy dense-only model manager
        model_manager = EmbeddingModelManager()
        await model_manager.load_model()

        # Load hybrid model manager (dense + sparse)
        hybrid_model_manager = HybridModelManager()
        await hybrid_model_manager.load_models()

        logger.info("Embedding service started successfully")
        logger.info("✅ Both legacy and hybrid models loaded")
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
        legacy_loaded = model_manager and model_manager.is_loaded()
        hybrid_loaded = hybrid_model_manager and hybrid_model_manager.is_loaded()

        if legacy_loaded and hybrid_loaded:
            model_status = "hybrid_ready"
        elif legacy_loaded:
            model_status = "legacy_only"
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

@app.post("/embed-hybrid", response_model=EmbedHybridResponse)
async def embed_hybrid(request: EmbedHybridRequest):
    """
    Create both dense and sparse vectors for hybrid search.
    Fallback to dense-only if BM25 fails.
    """
    try:
        if not hybrid_model_manager or not hybrid_model_manager.is_loaded():
            raise HTTPException(status_code=503, detail="Hybrid models not loaded")

        try:
            # Try to get both dense and sparse vectors
            dense_vector, sparse_vector = await hybrid_model_manager.encode_hybrid(request.text)

            return EmbedHybridResponse(
                text=request.text,
                dense_vector=dense_vector.tolist(),
                sparse_vector=sparse_vector,
                dense_dimension=len(dense_vector),
                sparse_terms=len(sparse_vector)
            )

        except Exception as sparse_error:
            # If hybrid fails, fallback to dense-only
            logger.warning(f"Hybrid encoding failed, falling back to dense-only: {sparse_error}")

            try:
                dense_vector = await hybrid_model_manager.encode_dense(request.text)

                return EmbedHybridResponse(
                    text=request.text,
                    dense_vector=dense_vector.tolist(),
                    sparse_vector={},  # Empty sparse vector for fallback
                    dense_dimension=len(dense_vector),
                    sparse_terms=0
                )

            except Exception as dense_error:
                logger.error(f"Both hybrid and dense encoding failed: {dense_error}")
                raise HTTPException(status_code=500, detail="All embedding methods failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in hybrid embedding: {e}")
        raise HTTPException(status_code=500, detail="Failed to create hybrid embedding")

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
    """Get information about loaded models (legacy format for compatibility)."""
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

@app.get("/hybrid-model-info")
async def get_hybrid_model_info():
    """Get information about hybrid models (dense + sparse)."""
    try:
        if not hybrid_model_manager:
            raise HTTPException(status_code=503, detail="Hybrid models not initialized")

        return hybrid_model_manager.get_model_info()

    except Exception as e:
        logger.error(f"Error getting hybrid model info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get hybrid model info")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
