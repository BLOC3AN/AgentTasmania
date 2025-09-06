# Database Service - Qdrant Vector Database with Hybrid Search

## Overview

This service provides a comprehensive interface to Qdrant vector database with **True Hybrid Search** capabilities, supporting both local (Docker) and cloud deployments. The service combines dense embeddings with sparse BM25 vectors using Qdrant's native Reciprocal Rank Fusion (RRF) for superior search accuracy.

## 🚀 Key Features

- **True Hybrid Search**: Combines dense embeddings + sparse BM25 vectors with RRF
- **Statistical BM25**: No ML training required - pure statistical approach
- **Qdrant Native RRF**: Uses Qdrant's built-in Reciprocal Rank Fusion algorithm
- **Dual Configuration Support**: Seamlessly switch between local Qdrant (Docker) and Qdrant Cloud
- **Automatic Collection Management**: Auto-creates collections with dense + sparse vector support
- **Vector Document Model**: Structured document storage with metadata support
- **Comprehensive Search**: Dense, sparse, and hybrid search with filtering capabilities
- **File Management**: Check, delete, and manage user files efficiently
- **Health Monitoring**: Built-in health checks and connection status

## Configuration

### Environment Variables

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333          # Local Docker or Cloud URL
QDRANT_CLOUD_API_KEY=your_api_key_here    # Required for cloud, optional for local
QDRANT_COLLECTION=agent_data              # Collection name (default: agent_data)

# Hybrid Search Configuration
EMBEDDING_SERVICE_URL=http://embedding:8005  # Embedding service for dense vectors
BM25_MODEL_PATH=/app/data/bm25_model.pkl     # BM25 statistics cache (optional)
```

### Local Setup (Docker)

For local development using Docker Compose:

```bash
# Set environment variables
QDRANT_URL=http://localhost:6333
# QDRANT_CLOUD_API_KEY is not needed for local

# Start services
docker-compose up qdrant database
```

### Cloud Setup

For Qdrant Cloud deployment:

```bash
# Set environment variables
QDRANT_URL=https://your-cluster-url.qdrant.tech:6333
QDRANT_CLOUD_API_KEY=your_actual_api_key
QDRANT_COLLECTION=agent_data
```

## API Endpoints

### Health Check

```http
GET /health
```

### 🔥 Hybrid Search (NEW)

**True hybrid search combining dense embeddings + sparse BM25 vectors with RRF**

```http
POST /hybrid-search
```

```json
{
  "query_text": "your search query",
  "limit": 5,
  "score_threshold": 0.5,
  "user_id": "optional_user_id"
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "document_id",
      "score": 0.574,
      "payload": {
        "text": "document content...",
        "user_id": "user_id",
        "title": "document title"
      }
    }
  ],
  "total_found": 2,
  "search_type": "hybrid"
}
```

**Search Types:**
- `"hybrid"`: Dense + sparse vectors with RRF (best accuracy)
- `"dense_only"`: Fallback when BM25 not available
- `"error"`: When embedding service is down

### Vector Search

```http
POST /search
```

```json
{
  "query_vector": [0.1, 0.2, ...],
  "limit": 10,
  "score_threshold": 0.7
}
```

<!-- Text Search endpoint removed - use /hybrid-search for real text search functionality -->

### Upsert Points

```http
POST /upsert
```

```json
{
  "points": [
    {
      "id": "doc_1",
      "vector": [0.1, 0.2, ...],
      "payload": {"text": "content", "user_id": "user123"}
    }
  ]
}
```

### Delete Points

```http
POST /delete
```

```json
{
  "point_ids": ["doc_1", "doc_2"]
}
```

## Usage Examples

### 🔥 Hybrid Search Usage (Recommended)

```python
from src.services.vector_services import VectorServices

# Initialize vector services
vector_service = VectorServices(
    database_service_url="http://localhost:8002",
    embedding_service_url="http://localhost:8005"
)

# Perform hybrid search
results = vector_service.hybrid_search(
    query_text="dọn dẹp phòng khách sạn",
    qdrant_config=qdrant,
    limit=5,
    score_threshold=0.5,
    user_id="user123"  # Optional user filtering
)

print(f"Search type: {results['search_type']}")  # "hybrid", "dense_only", or "error"
print(f"Found {results['total_found']} results")

for result in results['results']:
    print(f"Score: {result['score']}")
    print(f"Text: {result['payload']['text']}")
```

### Basic Vector Usage

```python
from src.database.qdrant_client import get_qdrant_config, create_vector_document

# Get Qdrant configuration
qdrant = get_qdrant_config()

# Create a document
doc = create_vector_document(
    text="Sample document content",
    user_id="user123",
    title="Sample Document",
    file_name="sample.txt"
)

# Store document with dense + sparse vectors
dense_vector = [0.1, 0.2, 0.3, ...]  # Your embedding vector
sparse_vector = {"indices": [1, 5, 10], "values": [0.8, 0.6, 0.4]}  # BM25 sparse vector

success = qdrant.upsert_document(doc, dense_vector, sparse_vector)

# Search similar documents
results = qdrant.search_similar(
    query_vector=dense_vector,
    limit=5,
    score_threshold=0.7
)
```

### File Management

```python
# Check if file exists
existing_doc = qdrant.check_file_exists("user123", "document.pdf")

# Get all user files
user_files = qdrant.get_user_files("user123")

# Delete user file vectors
success = qdrant.delete_user_file_vectors("user123", "document.pdf")
```

## 🚀 Key Improvements & New Features

### Hybrid Search Implementation

1. **True Hybrid Search**: Combines dense embeddings + sparse BM25 vectors using Qdrant's native RRF
2. **Statistical BM25**: No ML training required - pure statistical approach based on corpus
3. **Qdrant Native RRF**: Uses Qdrant's built-in Reciprocal Rank Fusion for optimal results
4. **Lazy Initialization**: BM25 corpus statistics built on-demand from existing documents
5. **Graceful Fallback**: Automatically falls back to dense-only search when needed

### Architecture Improvements

1. **Removed QdrantService**: Eliminated redundant QdrantService class
2. **Unified Configuration**: Single QdrantConfig class handles both local and cloud
3. **Better Error Handling**: Consistent logging instead of mixed print/logger usage
4. **Modern FastAPI**: Updated to use lifespan events instead of deprecated on_event
5. **Cleaner Code**: Removed duplicate code and improved maintainability
6. **Flexible Deployment**: Easy switching between local and cloud configurations

### Collection Schema

The service now creates collections with both dense and sparse vector support:

```python
# Collection configuration
vectors_config = {
    "dense_vector": VectorParams(size=1024, distance=Distance.COSINE)
}
sparse_vectors_config = {
    "bm25_sparse_vector": SparseVectorParams(modifier=Modifier.IDF)
}
```

## Development

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run syntax check
python3 -m py_compile main.py
python3 -m py_compile src/database/qdrant_client.py
```

### Docker Development

```bash
# Build and run
docker-compose up database

# Check logs
docker-compose logs database
```

## 🔄 Migration Notes

### From Previous Version

- **QdrantService Removed**: Use `get_qdrant_config()` instead
- **Environment Variables**: QDRANT_CLOUD_API_KEY is now optional for local deployments
- **Automatic Detection**: System automatically detects local vs cloud based on URL
- **Backward Compatibility**: Existing data and collections remain compatible

### New Hybrid Search Features

- **New Endpoint**: `/hybrid-search` for true hybrid search capabilities
- **BM25 Integration**: Automatic corpus statistics building from existing documents
- **RRF Scoring**: Qdrant's native Reciprocal Rank Fusion for optimal results
- **Fallback Strategy**: Graceful degradation to dense-only search when needed

### Performance Considerations

- **First Search**: May take longer as BM25 corpus statistics are built
- **Subsequent Searches**: Fast hybrid search with cached statistics
- **Memory Usage**: BM25 vocabulary stored in memory for performance
- **Corpus Size**: Scales well with document count (tested with 1000+ documents)

## 🧪 Testing Hybrid Search

```bash
# Test hybrid search endpoint
curl -X POST http://localhost:8002/hybrid-search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "your search query",
    "limit": 5,
    "score_threshold": 0.5
  }'

# Expected response with search_type: "hybrid"
{
  "results": [...],
  "total_found": 3,
  "search_type": "hybrid"
}
```

## 📊 Search Quality Comparison

| Search Type | Use Case | Accuracy | Speed |
|-------------|----------|----------|-------|
| **Hybrid** | General search | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Dense Only | Semantic similarity | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Sparse Only | Keyword matching | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Recommendation**: Use hybrid search for best overall accuracy, especially for mixed semantic + keyword queries.
