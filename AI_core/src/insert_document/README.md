# DOCX Document Processing Pipeline

Hệ thống xử lý tài liệu DOCX tự động từ đọc file → làm sạch → chia nhỏ → embedding → lưu trữ với **Hybrid Search** (Dense + Sparse Vectors).

## 🎯 Tính năng chính

- **Đọc DOCX**: Sử dụng LangChain Docx2txtLoader để extract text
- **Làm sạch dữ liệu**: Loại bỏ ký tự đặc biệt, normalize whitespace
- **Chia nhỏ (Chunking)**: Chia document thành chunks với TokenTextSplitter
- **Metadata extraction**: Tự động extract subject, week từ tên file
- **Dense Embedding**: Tích hợp với embedding service để tạo dense vector (512-dim)
- **Sparse Vectors**: BM25 encoder để tạo sparse vectors cho hybrid search
- **Hybrid Storage**: Lưu cả dense và sparse vectors vào Qdrant database
- **Batch processing**: Xử lý nhiều files cùng lúc
- **Error handling**: Xử lý lỗi graceful và logging chi tiết

## 📁 Cấu trúc files

```
AI_core/src/insert_document/
├── docx_data_processor.py    # Main processor class
├── test_docx_processor.py    # Unit tests
├── example_usage.py          # Usage examples
├── requirements.txt          # Dependencies
├── README.md                # Documentation
└── data/                    # Test data directory
    └── Module 6 S2 2025.docx
```

## 🚀 Quick Start

### 1. Cài đặt dependencies

```bash
cd AI_core/src/insert_document
pip install -r requirements.txt
```

### 2. Khởi động services

```bash
# Từ root directory
docker-compose up embedding vectordb
```

### 3. Chạy processor

```python
from docx_data_processor import DocxDataProcessor

# Initialize processor với hybrid search
processor = DocxDataProcessor(
    embed_service_url="http://localhost:8005",
    database_service_url="http://localhost:8002",
    enable_bm25=True  # Enable BM25 sparse vectors
)

# Process một file với hybrid vectors
result = processor.process_file("./data/Module 6 S2 2025.docx")
print(f"Processed {result['successful_chunks']}/{result['total_chunks']} chunks")
print(f"BM25 enabled: {result['bm25_enabled']}")

# Process cả thư mục
results = processor.process_directory("./data")
print(f"Processed {len(results)} files")
```

### 4. Chạy tests

```bash
python3 test_docx_processor.py
```

### 5. Xem examples

```bash
python3 example_usage.py
```

## 📖 API Reference

### DocxDataProcessor Class

#### Constructor

```python
DocxDataProcessor(
    embed_service_url="http://localhost:8005",
    database_service_url="http://localhost:8002",
    chunk_size=500,
    chunk_overlap=50,
    enable_bm25=True  # Enable hybrid search
)
```

#### Methods

- `process_file(file_path: str) -> Dict[str, Any]`: Xử lý một file DOCX
- `process_directory(directory_path: str) -> List[Dict[str, Any]]`: Xử lý tất cả file DOCX trong thư mục
- `load_docx(file_path: str) -> str`: Load nội dung từ file DOCX
- `clean_text(text: str) -> str`: Làm sạch text
- `chunk_text(text: str) -> List[str]`: Chia text thành chunks
- `extract_metadata(file_path: str) -> Dict[str, str]`: Extract metadata từ tên file
- `embed_text(text: str) -> Optional[List[float]]`: Tạo embedding
- `upsert_document(payload: Dict[str, Any]) -> bool`: Lưu vào database
- `get_stats() -> Dict[str, int]`: Lấy thống kê
- `reset_stats()`: Reset thống kê

## 🔧 Configuration

### Environment Variables

```bash
# Service URLs
EMBED_SERVICE_URL=http://localhost:8005
DATABASE_SERVICE_URL=http://localhost:8002

# Processing settings
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

### Payload Format (Hybrid Vectors)

```json
{
  "id": "uuid-string",
  "vector": {
    "dense_vector": [0.1, 0.2, ...],  // 512-dim embedding
    "bm25_sparse_vector": {
      "indices": [1, 5, 10, ...],     // Term indices
      "values": [0.8, 0.6, 0.4, ...]  // BM25 scores
    }
  },
  "payload": {
    "content": "chunk text content",
    "subject": "module",
    "title": "Module 6 S2 2025",
    "week": "week06",
    "chunk_id": 0,
    "file_path": "/path/to/file.docx"
  }
}
```

## 🧪 Testing

### Unit Tests

```bash
# Chạy tất cả tests
python3 test_docx_processor.py

# Test với coverage
python3 -m coverage run test_docx_processor.py
python3 -m coverage report
```

### Integration Tests

```bash
# Test với real file
python3 example_usage.py
```

## 📊 Performance

- **Processing speed**: ~10-15 chunks/second
- **Memory usage**: ~50MB cho file 20MB
- **Chunk size**: 300-500 tokens optimal
- **Batch size**: 1-5 files optimal

## 🔍 Troubleshooting

### Common Issues

1. **Service connection errors**
   ```bash
   # Check services
   curl http://localhost:8005/health
   curl http://localhost:8002/health
   ```

2. **Memory issues với large files**
   ```python
   # Reduce chunk size
   processor = DocxDataProcessor(chunk_size=300)
   ```

3. **Encoding issues**
   - Đảm bảo file DOCX không bị corrupt
   - Kiểm tra encoding UTF-8

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

processor = DocxDataProcessor()
result = processor.process_file("file.docx")
```

## 🚀 Production Usage

### Batch Processing

```python
import os
from pathlib import Path

processor = DocxDataProcessor()

# Process tất cả files trong thư mục
for root, dirs, files in os.walk("documents/"):
    for file in files:
        if file.endswith('.docx'):
            file_path = os.path.join(root, file)
            result = processor.process_file(file_path)
            print(f"Processed: {file} - {result['successful_chunks']} chunks")
```

### Error Handling

```python
try:
    result = processor.process_file("file.docx")
    if result["success"]:
        print(f"✅ Success: {result['successful_chunks']} chunks")
    else:
        print(f"❌ Failed: {result['error']}")
except Exception as e:
    print(f"❌ Exception: {e}")
```

## 📈 Monitoring

```python
# Check stats
stats = processor.get_stats()
print(f"Files processed: {stats['files_processed']}")
print(f"Success rate: {stats['successful_upserts']}/{stats['total_chunks']}")
```

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch
3. Thêm tests cho new features
4. Chạy tất cả tests
5. Submit pull request

## 📄 License

MIT License - see LICENSE file for details.
