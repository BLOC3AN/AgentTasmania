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

class HealthResponse(BaseModel):
    status: str
    service: str
    model_status: Optional[str] = None
