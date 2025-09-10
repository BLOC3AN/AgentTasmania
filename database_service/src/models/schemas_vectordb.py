from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class VectorSearchRequest(BaseModel):
    query_vector: List[float]
    limit: Optional[int] = 5
    score_threshold: Optional[float] = 0.7

class VectorSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_found: int

class UpsertPointsRequest(BaseModel):
    points: List[Dict[str, Any]]

class UpsertPointsResponse(BaseModel):
    success: bool
    message: str
    points_count: int

class DeletePointsRequest(BaseModel):
    point_ids: List[str]

class DeletePointsResponse(BaseModel):
    success: bool
    message: str
    deleted_count: int

# TextSearchRequest removed - use HybridSearchRequest for real text search

class HealthResponse(BaseModel):
    status: str
    service: str
    qdrant_status: str

class HybridSearchRequest(BaseModel):
    query_text: str
    limit: Optional[int] = 5
    dense_weight: Optional[float] = 0.7
    sparse_weight: Optional[float] = 0.3
    score_threshold: Optional[float] = 0.5
    subject: Optional[str] = None
    title: Optional[str] = None
    week: Optional[str] = None

class HybridSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_found: int
    search_type: str  # "hybrid", "dense_only", "sparse_only"

class HybridSearchWithVectorsRequest(BaseModel):
    dense_vector: List[float]
    sparse_vector: Optional[Dict[int, float]] = {}  # Empty dict means dense-only
    limit: Optional[int] = 5
    score_threshold: Optional[float] = 0.5
    subject: Optional[str] = None
    title: Optional[str] = None
    week: Optional[str] = None
