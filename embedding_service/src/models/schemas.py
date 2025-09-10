from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class EmbedTextRequest(BaseModel):
    text: str
    dimension: Optional[int] = 384

class EmbedTextResponse(BaseModel):
    text: str
    embedding: List[float]
    dimension: int

class EmbedBatchRequest(BaseModel):
    texts: List[str]

class EmbedBatchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_processed: int
    dimension: int

class EmbedHybridRequest(BaseModel):
    text: str
    dimension: Optional[int] = 384

class EmbedHybridResponse(BaseModel):
    text: str
    dense_vector: List[float]
    sparse_vector: Dict[int, float]  # BM25 sparse vector format {index: value}
    dense_dimension: int
    sparse_terms: int  # Number of non-zero terms in sparse vector

class EmbedHybridBatchRequest(BaseModel):
    texts: List[str]

class EmbedHybridBatchResponse(BaseModel):
    results: List[Dict[str, Any]]  # Each result contains text, dense_vector, sparse_vector
    total_processed: int
    dense_dimension: int

class HealthResponse(BaseModel):
    status: str
    service: str
    model_status: Optional[str] = None
