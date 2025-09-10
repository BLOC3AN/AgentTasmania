# PostgreSQL Database Schema cho Document Storage và Vector Database Integration

## 1. Thiết lập PostgreSQL trong Docker Compose

**Thông tin kết nối:**

```yml
- Host: localhost
- Port: 5433
- Username: admin
- Password: Hai@30032000
- Database: mydb
```

**Docker Compose Configuration:**

```yaml
postgres:
  image: postgres:15
  container_name: postgres
  ports:
    - "5433:5432"
  environment:
    POSTGRES_USER: admin
    POSTGRES_PASSWORD: Hai@30032000
    POSTGRES_DB: mydb
```

---

## 2. Database Schema Design

### 2.1 Core Tables

#### Documents Table - Lưu metadata chính của document

```sql
CREATE TABLE IF NOT EXISTS documents (
    doc_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    user_id TEXT NOT NULL,
    file_id TEXT UNIQUE,                    -- Unique identifier cho file
    source TEXT,                            -- Nguồn gốc file (upload, url, etc.)
    file_type TEXT,                         -- pdf, txt, docx, etc.
    file_size BIGINT,                       -- Kích thước file (bytes)
    total_pages INTEGER,                    -- Tổng số trang (nếu có)
    status TEXT DEFAULT 'processing',       -- processing, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_file_id ON documents(file_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
```

#### Document Content Table - Lưu nội dung chunks

```sql
CREATE TABLE IF NOT EXISTS document_content (
    chunk_id SERIAL PRIMARY KEY,
    doc_id INTEGER REFERENCES documents(doc_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,                    -- Thứ tự chunk trong document
    chunk_size INTEGER,                     -- Số ký tự trong chunk
    vector_id TEXT,                         -- ID tương ứng trong Qdrant
    embedding_status TEXT DEFAULT 'pending', -- pending, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_doc_id ON document_content(doc_id);
CREATE INDEX IF NOT EXISTS idx_content_vector_id ON document_content(vector_id);
CREATE INDEX IF NOT EXISTS idx_content_embedding_status ON document_content(embedding_status);
```

#### Vector Metadata Table - Mapping giữa PostgreSQL và Qdrant
```sql
CREATE TABLE IF NOT EXISTS vector_metadata (
    id SERIAL PRIMARY KEY,
    vector_id TEXT UNIQUE NOT NULL,         -- ID trong Qdrant
    doc_id INTEGER REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_id INTEGER REFERENCES document_content(chunk_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    collection_name TEXT DEFAULT 'agent_data',
    vector_dimension INTEGER DEFAULT 512,
    embedding_model TEXT DEFAULT 'sentence-transformers',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vector_metadata_vector_id ON vector_metadata(vector_id);
CREATE INDEX IF NOT EXISTS idx_vector_metadata_doc_id ON vector_metadata(doc_id);
CREATE INDEX IF NOT EXISTS idx_vector_metadata_user_id ON vector_metadata(user_id);
```

### 2.2 Extended Tables cho Advanced Features

#### Document Processing Log

```sql
CREATE TABLE IF NOT EXISTS processing_logs (
    log_id SERIAL PRIMARY KEY,
    doc_id INTEGER REFERENCES documents(doc_id) ON DELETE CASCADE,
    step TEXT NOT NULL,                     -- parsing, chunking, embedding, indexing
    status TEXT NOT NULL,                   -- started, completed, failed
    message TEXT,                           -- Chi tiết hoặc error message
    processing_time_ms INTEGER,             -- Thời gian xử lý (milliseconds)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processing_logs_doc_id ON processing_logs(doc_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_status ON processing_logs(status);
```

#### User Document Statistics

```sql
CREATE TABLE IF NOT EXISTS user_document_stats (
    user_id TEXT PRIMARY KEY,
    total_documents INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 0,
    total_storage_bytes BIGINT DEFAULT 0,
    last_upload_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Integration với Qdrant Vector Database

### 3.1 Data Flow Architecture

```txt
Document Upload → PostgreSQL (metadata) → Text Processing → Embedding → Qdrant (vectors)
                     ↓                                                      ↓
              Document Content Table ←------ Vector Metadata Table -------→ Vector Storage
```

### 3.2 Synchronization Strategy

#### Insert Document Workflow

1. **PostgreSQL**: Lưu document metadata vào `documents` table
2. **Text Processing**: Chia document thành chunks, lưu vào `document_content`
3. **Embedding**: Tạo vector embeddings cho mỗi chunk
4. **Qdrant**: Lưu vectors với payload metadata
5. **Mapping**: Lưu mapping vào `vector_metadata` table

#### Search Workflow:

1. **Query Processing**: Tạo embedding cho search query
2. **Qdrant Search**: Tìm similar vectors
3. **PostgreSQL Lookup**: Lấy full metadata từ PostgreSQL
4. **Result Enrichment**: Kết hợp vector scores với metadata

### 3.3 Qdrant Collection Configuration

```python
# Tương ứng với VectorDocument model trong codebase
collection_config = {
    "vectors": {
        "dense_vector": {
            "size": 384,  # all-MiniLM-L6-v2 model dimension
            "distance": "Cosine"
        }
    },
    "sparse_vectors": {
        "bm25_sparse_vector": {
            "modifier": "idf"  # Inverse Document Frequency
        }
    }
}
```

---

## 4. SQL Functions và Procedures

### 4.1 Document Management Functions

#### Insert Document với Transaction Safety

```sql
CREATE OR REPLACE FUNCTION insert_document_with_content(
    p_title TEXT,
    p_user_id TEXT,
    p_file_id TEXT,
    p_source TEXT DEFAULT NULL,
    p_file_type TEXT DEFAULT NULL,
    p_file_size BIGINT DEFAULT NULL,
    p_content_chunks TEXT[] DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_doc_id INTEGER;
    v_chunk_text TEXT;
    v_chunk_index INTEGER := 1;
BEGIN
    -- Insert document metadata
    INSERT INTO documents (title, user_id, file_id, source, file_type, file_size, status)
    VALUES (p_title, p_user_id, p_file_id, p_source, p_file_type, p_file_size, 'processing')
    RETURNING doc_id INTO v_doc_id;

    -- Insert content chunks if provided
    IF p_content_chunks IS NOT NULL THEN
        FOREACH v_chunk_text IN ARRAY p_content_chunks
        LOOP
            INSERT INTO document_content (doc_id, content, chunk_index, chunk_size)
            VALUES (v_doc_id, v_chunk_text, v_chunk_index, LENGTH(v_chunk_text));

            v_chunk_index := v_chunk_index + 1;
        END LOOP;
    END IF;

    -- Update user statistics
    INSERT INTO user_document_stats (user_id, total_documents, last_upload_at)
    VALUES (p_user_id, 1, CURRENT_TIMESTAMP)
    ON CONFLICT (user_id) DO UPDATE SET
        total_documents = user_document_stats.total_documents + 1,
        last_upload_at = CURRENT_TIMESTAMP;

    RETURN v_doc_id;
END;
$$ LANGUAGE plpgsql;
```

#### Get Document với Content

```sql
CREATE OR REPLACE FUNCTION get_document_with_content(p_doc_id INTEGER)
RETURNS TABLE(
    doc_id INTEGER,
    title TEXT,
    user_id TEXT,
    file_id TEXT,
    source TEXT,
    created_at TIMESTAMP,
    chunk_id INTEGER,
    content TEXT,
    page_number INTEGER,
    chunk_index INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.doc_id,
        d.title,
        d.user_id,
        d.file_id,
        d.source,
        d.created_at,
        dc.chunk_id,
        dc.content,
        dc.page_number,
        dc.chunk_index
    FROM documents d
    LEFT JOIN document_content dc ON d.doc_id = dc.doc_id
    WHERE d.doc_id = p_doc_id
    ORDER BY dc.chunk_index;
END;
$$ LANGUAGE plpgsql;
```

### 4.2 Vector Synchronization Functions

#### Sync Vector Metadata

```sql
CREATE OR REPLACE FUNCTION sync_vector_metadata(
    p_vector_id TEXT,
    p_doc_id INTEGER,
    p_chunk_id INTEGER,
    p_user_id TEXT,
    p_collection_name TEXT DEFAULT 'agent_data'
) RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO vector_metadata (vector_id, doc_id, chunk_id, user_id, collection_name)
    VALUES (p_vector_id, p_doc_id, p_chunk_id, p_user_id, p_collection_name)
    ON CONFLICT (vector_id) DO UPDATE SET
        doc_id = EXCLUDED.doc_id,
        chunk_id = EXCLUDED.chunk_id,
        user_id = EXCLUDED.user_id,
        collection_name = EXCLUDED.collection_name;

    -- Update embedding status
    UPDATE document_content
    SET embedding_status = 'completed', vector_id = p_vector_id
    WHERE chunk_id = p_chunk_id;

    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;
```

#### Cleanup Orphaned Records

```sql
CREATE OR REPLACE FUNCTION cleanup_orphaned_records() RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    -- Delete orphaned document_content
    DELETE FROM document_content
    WHERE doc_id NOT IN (SELECT doc_id FROM documents);

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    -- Delete orphaned vector_metadata
    DELETE FROM vector_metadata
    WHERE doc_id NOT IN (SELECT doc_id FROM documents);

    -- Update user statistics
    UPDATE user_document_stats
    SET
        total_documents = (SELECT COUNT(*) FROM documents WHERE user_id = user_document_stats.user_id),
        total_chunks = (SELECT COUNT(*) FROM document_content dc
                       JOIN documents d ON dc.doc_id = d.doc_id
                       WHERE d.user_id = user_document_stats.user_id),
        updated_at = CURRENT_TIMESTAMP;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;
```

---

## 5. Performance Optimization

### 5.1 Indexing Strategy

```sql
-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_documents_user_status ON documents(user_id, status);
CREATE INDEX IF NOT EXISTS idx_content_doc_page ON document_content(doc_id, page_number);
CREATE INDEX IF NOT EXISTS idx_vector_user_collection ON vector_metadata(user_id, collection_name);

-- Full-text search index cho PostgreSQL search
CREATE INDEX IF NOT EXISTS idx_content_fulltext ON document_content
USING gin(to_tsvector('english', content));

-- Partial indexes for active documents
CREATE INDEX IF NOT EXISTS idx_documents_active ON documents(user_id, created_at)
WHERE status = 'completed';
```

### 5.2 Query Optimization Examples

#### Efficient Document Search

```sql
-- Tìm documents của user với pagination
SELECT d.doc_id, d.title, d.created_at, d.status,
       COUNT(dc.chunk_id) as total_chunks
FROM documents d
LEFT JOIN document_content dc ON d.doc_id = dc.doc_id
WHERE d.user_id = $1
  AND d.status = 'completed'
GROUP BY d.doc_id, d.title, d.created_at, d.status
ORDER BY d.created_at DESC
LIMIT $2 OFFSET $3;
```

#### Search Content với Full-text

```sql
-- Tìm kiếm trong nội dung document
SELECT d.title, dc.content, dc.page_number,
       ts_rank(to_tsvector('english', dc.content), plainto_tsquery('english', $2)) as rank
FROM documents d
JOIN document_content dc ON d.doc_id = dc.doc_id
WHERE d.user_id = $1
  AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', $2)
ORDER BY rank DESC
LIMIT 20;
```

---

## 6. Usage Examples và Best Practices

### 6.1 Complete Document Processing Workflow

#### Python Example với Database Service Integration

```python
import psycopg2
import requests
from typing import List, Dict, Any

class DocumentProcessor:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': 5433,
            'user': 'admin',
            'password': 'Hai@30032000',
            'database': 'mydb'
        }
        self.database_service_url = "http://localhost:8002"
        self.embedding_service_url = "http://localhost:8001"

    def process_document(self, title: str, user_id: str, content: str,
                        file_id: str = None, source: str = None) -> Dict[str, Any]:
        """
        Complete workflow: PostgreSQL → Embedding → Qdrant
        """
        try:
            # 1. Insert document metadata vào PostgreSQL
            doc_id = self._insert_document_metadata(title, user_id, file_id, source)

            # 2. Chia content thành chunks
            chunks = self._chunk_content(content)

            # 3. Insert chunks vào PostgreSQL
            chunk_ids = self._insert_document_chunks(doc_id, chunks)

            # 4. Tạo embeddings và lưu vào Qdrant
            vector_results = []
            for chunk_id, chunk_text in zip(chunk_ids, chunks):
                vector_result = self._process_chunk_to_vector(
                    chunk_id, doc_id, user_id, chunk_text, title
                )
                vector_results.append(vector_result)

            # 5. Update document status
            self._update_document_status(doc_id, 'completed')

            return {
                'success': True,
                'doc_id': doc_id,
                'chunks_processed': len(chunks),
                'vectors_created': len([r for r in vector_results if r['success']])
            }

        except Exception as e:
            self._log_error(doc_id if 'doc_id' in locals() else None, str(e))
            return {'success': False, 'error': str(e)}

    def _insert_document_metadata(self, title: str, user_id: str,
                                 file_id: str, source: str) -> int:
        """Insert document metadata và return doc_id"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT insert_document_with_content(%s, %s, %s, %s, %s, %s, %s)
                """, (title, user_id, file_id, source, 'txt', len(content), None))

                doc_id = cur.fetchone()[0]
                return doc_id

    def _chunk_content(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Chia content thành chunks"""
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            chunks.append(chunk)
        return chunks

    def _insert_document_chunks(self, doc_id: int, chunks: List[str]) -> List[int]:
        """Insert chunks vào PostgreSQL và return chunk_ids"""
        chunk_ids = []
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                for idx, chunk in enumerate(chunks):
                    cur.execute("""
                        INSERT INTO document_content
                        (doc_id, content, chunk_index, chunk_size)
                        VALUES (%s, %s, %s, %s)
                        RETURNING chunk_id
                    """, (doc_id, chunk, idx + 1, len(chunk)))

                    chunk_id = cur.fetchone()[0]
                    chunk_ids.append(chunk_id)

        return chunk_ids

    def _process_chunk_to_vector(self, chunk_id: int, doc_id: int,
                               user_id: str, content: str, title: str) -> Dict[str, Any]:
        """Tạo embedding và lưu vào Qdrant"""
        try:
            # 1. Tạo embedding
            embedding_response = requests.post(
                f"{self.embedding_service_url}/embed",
                json={"text": content}
            )
            embedding = embedding_response.json()["embedding"]

            # 2. Tạo vector document cho Qdrant
            vector_doc = {
                "id": f"chunk_{chunk_id}",
                "vector": embedding,
                "payload": {
                    "text": content,
                    "user_id": user_id,
                    "title": title,
                    "doc_id": doc_id,
                    "chunk_id": chunk_id
                }
            }

            # 3. Upsert vào Qdrant
            qdrant_response = requests.post(
                f"{self.database_service_url}/upsert",
                json={"points": [vector_doc]}
            )

            # 4. Sync metadata trong PostgreSQL
            if qdrant_response.json()["success"]:
                self._sync_vector_metadata(
                    f"chunk_{chunk_id}", doc_id, chunk_id, user_id
                )

            return {"success": True, "vector_id": f"chunk_{chunk_id}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _sync_vector_metadata(self, vector_id: str, doc_id: int,
                            chunk_id: int, user_id: str):
        """Sync vector metadata trong PostgreSQL"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sync_vector_metadata(%s, %s, %s, %s, %s)
                """, (vector_id, doc_id, chunk_id, user_id, 'agent_data'))

# Usage example
processor = DocumentProcessor()
result = processor.process_document(
    title="Sample Document",
    user_id="user123",
    content="This is a sample document content...",
    file_id="file_001",
    source="upload"
)
print(result)
```

### 6.2 Search Integration Example

#### Hybrid Search: PostgreSQL + Qdrant

```python
class HybridSearchService:
    def search_documents(self, user_id: str, query: str, limit: int = 10) -> List[Dict]:
        """
        Hybrid search combining PostgreSQL full-text và Qdrant vector search
        """
        # 1. Vector search trong Qdrant
        embedding_response = requests.post(
            f"{self.embedding_service_url}/embed",
            json={"text": query}
        )
        query_vector = embedding_response.json()["embedding"]

        vector_results = requests.post(
            f"{self.database_service_url}/search",
            json={
                "query_vector": query_vector,
                "limit": limit * 2,  # Get more for reranking
                "score_threshold": 0.5
            }
        ).json()["results"]

        # 2. Full-text search trong PostgreSQL
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.doc_id, d.title, dc.chunk_id, dc.content, dc.page_number,
                           ts_rank(to_tsvector('english', dc.content),
                                  plainto_tsquery('english', %s)) as text_rank
                    FROM documents d
                    JOIN document_content dc ON d.doc_id = dc.doc_id
                    WHERE d.user_id = %s
                      AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', %s)
                    ORDER BY text_rank DESC
                    LIMIT %s
                """, (query, user_id, query, limit))

                text_results = cur.fetchall()

        # 3. Combine và rank results
        combined_results = self._combine_search_results(vector_results, text_results)

        return combined_results[:limit]
```

### 6.3 Maintenance và Monitoring

#### Database Health Check
```sql
-- Check database health
SELECT
    'documents' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))/3600) as avg_age_hours
FROM documents
UNION ALL
SELECT
    'document_content' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT doc_id) as unique_documents,
    AVG(chunk_size) as avg_chunk_size
FROM document_content
UNION ALL
SELECT
    'vector_metadata' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT collection_name) as unique_collections
FROM vector_metadata;
```

#### Cleanup Script
```bash
#!/bin/bash
# cleanup_database.sh

echo "🧹 Starting database cleanup..."

# 1. Cleanup orphaned records
psql -h localhost -p 5433 -U admin -d mydb -c "SELECT cleanup_orphaned_records();"

# 2. Update statistics
psql -h localhost -p 5433 -U admin -d mydb -c "ANALYZE documents, document_content, vector_metadata;"

# 3. Vacuum tables
psql -h localhost -p 5433 -U admin -d mydb -c "VACUUM documents, document_content, vector_metadata;"

echo "✅ Database cleanup completed!"
```

---

## 7. Backup và Recovery

### 7.1 Backup Strategy

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/backup/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)

# Full database backup
pg_dump -h localhost -p 5433 -U admin -d mydb \
    --format=custom \
    --compress=9 \
    --file="${BACKUP_DIR}/full_backup_${DATE}.dump"

# Schema-only backup
pg_dump -h localhost -p 5433 -U admin -d mydb \
    --schema-only \
    --file="${BACKUP_DIR}/schema_backup_${DATE}.sql"

# Data-only backup for specific tables
pg_dump -h localhost -p 5433 -U admin -d mydb \
    --data-only \
    --table=documents \
    --table=document_content \
    --file="${BACKUP_DIR}/data_backup_${DATE}.sql"

echo "✅ Backup completed: ${DATE}"
```

### 7.2 Recovery Procedures

```bash
# Restore full database
pg_restore -h localhost -p 5433 -U admin -d mydb \
    --clean --if-exists \
    /backup/postgresql/full_backup_20241201_120000.dump

# Restore specific tables
pg_restore -h localhost -p 5433 -U admin -d mydb \
    --table=documents \
    --table=document_content \
    /backup/postgresql/full_backup_20241201_120000.dump
```

---

## 8. Best Practices Summary

### 8.1 Performance
- ✅ Sử dụng indexes phù hợp cho các query thường xuyên
- ✅ Partition tables khi data lớn (>10M records)
- ✅ Regular VACUUM và ANALYZE
- ✅ Monitor query performance với pg_stat_statements

### 8.2 Data Integrity
- ✅ Sử dụng transactions cho multi-table operations
- ✅ Foreign key constraints để đảm bảo referential integrity
- ✅ Regular backup và test recovery procedures
- ✅ Cleanup orphaned records định kỳ

### 8.3 Security
- ✅ Sử dụng connection pooling
- ✅ Limit database user permissions
- ✅ Encrypt sensitive data
- ✅ Regular security updates

### 8.4 Integration
- ✅ Maintain sync giữa PostgreSQL và Qdrant
- ✅ Handle failures gracefully với retry logic
- ✅ Monitor both databases health
- ✅ Use consistent IDs across systems

