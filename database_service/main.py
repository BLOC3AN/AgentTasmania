import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.database.qdrant_client import get_qdrant_config
from qdrant_client.models import PointStruct
from src.models.schemas_vectordb import (
    VectorSearchRequest, VectorSearchResponse,
    UpsertPointsRequest, UpsertPointsResponse,
    DeletePointsRequest, DeletePointsResponse,
    HybridSearchRequest, HybridSearchResponse,
    HealthResponse
)
from src.utils.logger import Logger
from src.services.vector_services import VectorServices

load_dotenv()
logger = Logger(__name__)

# Initialize Qdrant configuration and vector services
qdrant_config = None
vector_services = None

@asynccontextmanager
async def lifespan(_app: FastAPI):  # noqa: ARG001
    # Startup
    global qdrant_config, vector_services
    try:
        qdrant_config = get_qdrant_config()
        vector_services = VectorServices(
            database_service_url="http://localhost:8002",
            embedding_service_url=os.getenv("EMBEDDING_SERVICE_URL", "http://embedding:8005")
        )
        logger.info("Database service started successfully")
    except Exception as e:
        logger.log_exception("startup", e)

    yield

    # Shutdown
    logger.info("Database service shutting down")

app = FastAPI(
    title="Database Service",
    description="Vector database service using Qdrant",
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
        if qdrant_config:
            qdrant_config.client.get_collections()
            qdrant_status = "connected"
        else:
            qdrant_status = "not_initialized"
    except Exception:
        qdrant_status = "disconnected"

    return HealthResponse(
        status="healthy",
        service="database",
        qdrant_status=qdrant_status
    )

@app.get("/collection-info")
async def get_collection_info():
    try:
        if not qdrant_config:
            raise HTTPException(status_code=503, detail="Qdrant not initialized")

        info = qdrant_config.get_collection_info()
        return info
    except Exception as e:
        logger.log_exception("get_collection_info", e)
        raise HTTPException(status_code=500, detail="Failed to get collection info")

@app.get("/debug/bm25-status")
async def get_bm25_status():
    """Debug endpoint to check BM25 corpus status"""
    try:
        if not vector_services:
            raise HTTPException(status_code=503, detail="Vector services not initialized")

        # Force initialize BM25 corpus
        if not vector_services._corpus_initialized:
            vector_services._initialize_bm25_corpus(qdrant_config)

        # Get BM25 encoder status
        bm25_status = {
            "corpus_initialized": vector_services._corpus_initialized,
            "encoder_ready": vector_services.bm25_encoder.corpus_stats_ready if vector_services.bm25_encoder else False,
            "corpus_info": vector_services.bm25_encoder.get_corpus_info() if vector_services.bm25_encoder else None
        }

        return bm25_status
    except Exception as e:
        logger.log_exception("get_bm25_status", e)
        raise HTTPException(status_code=500, detail="Failed to get BM25 status")

@app.post("/debug/test-bm25-encode")
async def test_bm25_encode(request: dict):
    """Debug endpoint to test BM25 encoding directly"""
    try:
        if not vector_services:
            raise HTTPException(status_code=503, detail="Vector services not initialized")

        query_text = request.get("query_text", "test")

        # Force initialize BM25 corpus
        if not vector_services._corpus_initialized:
            vector_services._initialize_bm25_corpus(qdrant_config)

        # Test encoding
        sparse_vector = vector_services.bm25_encoder.encode(query_text)

        # Get detailed info
        tokens = vector_services.bm25_encoder.tokenize(query_text)

        result = {
            "query_text": query_text,
            "tokens": tokens,
            "sparse_vector": sparse_vector,
            "sparse_vector_size": len(sparse_vector),
            "corpus_ready": vector_services.bm25_encoder.corpus_stats_ready,
            "vocabulary_size": len(vector_services.bm25_encoder.vocabulary),
            "sample_vocabulary": list(vector_services.bm25_encoder.vocabulary.keys())[:10]
        }

        return result
    except Exception as e:
        logger.log_exception("test_bm25_encode", e)
        raise HTTPException(status_code=500, detail="Failed to test BM25 encoding")

@app.post("/search", response_model=VectorSearchResponse)
async def search_vectors(request: VectorSearchRequest):
    try:
        if not qdrant_config:
            raise HTTPException(status_code=503, detail="Qdrant not initialized")

        results = qdrant_config.search_similar(
            query_vector=request.query_vector,
            limit=request.limit,
            score_threshold=request.score_threshold
        )

        # Convert results to expected format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result["id"],
                "score": result["score"],
                "payload": result["document"].to_payload()
            })

        return VectorSearchResponse(
            results=formatted_results,
            total_found=len(formatted_results)
        )
    except Exception as e:
        logger.log_exception("search_vectors", e)
        raise HTTPException(status_code=500, detail="Vector search failed")

# Removed mock /search-text endpoint - use /hybrid-search for real text search functionality

@app.post("/upsert", response_model=UpsertPointsResponse)
async def upsert_points(request: UpsertPointsRequest):
    try:
        if not qdrant_config:
            raise HTTPException(status_code=503, detail="Qdrant not initialized")

        points = []
        for point_data in request.points:
            # Convert vector to named vector format
            vector_data = point_data["vector"]
            if isinstance(vector_data, list):
                # If vector is a list, wrap it in dense_vector
                vectors = {"dense_vector": vector_data}
                logger.info(f"Auto-converted vector to named format: {len(vector_data)} dimensions")
            else:
                # If vector is already a dict, use as is
                vectors = vector_data
                logger.info(f"Using provided named vector format: {vectors.keys()}")

            point = PointStruct(
                id=point_data["id"],
                vector=vectors,
                payload=point_data.get("payload", {})
            )
            points.append(point)

        # Use client directly for upsert
        result = qdrant_config.client.upsert(
            collection_name=qdrant_config.collection_name,
            points=points
        )
        success = result is not None

        return UpsertPointsResponse(
            success=success,
            message="Points upserted successfully" if success else "Failed to upsert points",
            points_count=len(points)
        )
    except Exception as e:
        logger.log_exception("upsert_points", e)
        raise HTTPException(status_code=500, detail="Failed to upsert points")

@app.post("/delete", response_model=DeletePointsResponse)
async def delete_points(request: DeletePointsRequest):
    try:
        if not qdrant_config:
            raise HTTPException(status_code=503, detail="Qdrant not initialized")

        # Use client directly for delete
        qdrant_config.client.delete(
            collection_name=qdrant_config.collection_name,
            points_selector=request.point_ids
        )
        success = True

        return DeletePointsResponse(
            success=success,
            message="Points deleted successfully" if success else "Failed to delete points",
            deleted_count=len(request.point_ids)
        )
    except Exception as e:
        logger.log_exception("delete_points", e)
        raise HTTPException(status_code=500, detail="Failed to delete points")

@app.post("/hybrid-search", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    try:
        if not qdrant_config:
            raise HTTPException(status_code=503, detail="Qdrant not initialized")

        if not vector_services:
            raise HTTPException(status_code=503, detail="Vector services not initialized")

        results = vector_services.hybrid_search(
            query_text=request.query_text,
            qdrant_config=qdrant_config,
            limit=request.limit,
            score_threshold=request.score_threshold,
            subject=getattr(request, 'subject', None),
            title=getattr(request, 'title', None),
            week=getattr(request, 'week', None)
        )

        return HybridSearchResponse(
            results=results["results"],
            total_found=results["total_found"],
            search_type=results["search_type"]
        )

    except Exception as e:
        logger.log_exception("hybrid_search", e)
        raise HTTPException(status_code=500, detail="Hybrid search failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
