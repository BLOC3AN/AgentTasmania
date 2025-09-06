# Embedding Service

Service để tạo embeddings từ text sử dụng model sentence-transformers/distiluse-base-multilingual-cased-v1.

## Tính năng

- **Text Embedding**: Chuyển đổi text thành vector embeddings
- **Batch Processing**: Xử lý nhiều text cùng lúc
- **Multilingual Support**: Hỗ trợ đa ngôn ngữ
- **Async Processing**: Xử lý bất đồng bộ để tránh blocking
- **Model Caching**: Cache model để tăng tốc độ khởi động

## API Endpoints

### Health Check
```
GET /health
```

### Embed Single Text
```
POST /embed
{
  "text": "Your text here"
}
```

Response:
```json
{
  "text": "Your text here",
  "embedding": [0.1, 0.2, ...],
  "dimension": 512
}
```

### Embed Multiple Texts
```
POST /embed-batch
{
  "texts": ["Text 1", "Text 2", "Text 3"]
}
```

Response:
```json
{
  "results": [
    {
      "text": "Text 1",
      "embedding": [0.1, 0.2, ...],
      "index": 0
    }
  ],
  "total_processed": 3,
  "dimension": 512
}
```

### Model Information
```
GET /model-info
```

Response:
```json
{
  "model_name": "sentence-transformers/distiluse-base-multilingual-cased-v1",
  "dimension": 512,
  "max_sequence_length": 512
}
```

## Model Details

- **Model**: sentence-transformers/distiluse-base-multilingual-cased-v1
- **Dimension**: 512
- **Languages**: Multilingual (15+ languages)
- **Max Sequence Length**: 512 tokens

## Environment Variables

- `API_PORT`: Port để chạy service (default: 8005)
- `MODEL_CACHE_DIR`: Thư mục cache model (default: /app/models)

## Docker Usage

Service được cấu hình trong docker-compose.yml và sẽ tự động khởi động cùng với các service khác.

```bash
docker-compose up embedding
```

## Integration với Qdrant

Service này được thiết kế để tích hợp với database service (Qdrant) để cung cấp embeddings cho text search functionality.
