# Calculate Cost for Qdrant and PostgreSQL

## Qdrant Cost Calculation

### Vector description: 

vector dimension: 512
vector type: list[float]

-> 1 float = 8byte
-> 1 vector = 512 * 8byte = 4096byte = 4kb

### Metadata description: 

```json
{
  "document_id": "doc123",          // string ngắn ~10–20 bytes
  "chunk_id": 5,                    // số nguyên 4–8 bytes
  "document_name": "Quarterly Report Q3",  // chuỗi ~30–40 bytes
  "user_id": "user456",             // chuỗi ngắn ~10 bytes
  "source": "pdf",                  // chuỗi rất ngắn ~5 bytes
  "other_meta": {"page_number": 10} // số nguyên nhỏ
}
```

-> 1 metadata = 300 bytes

-> 1 point = 1 vector + 1 metadata = 4kb + 300bytes = 4.3kb

### Document description: 

1 document = 25MB
-> 1500 chunks (~1 page = 1 chunk)
-> 1500 points
-> 1500 * 4.3kb = 6.45MB

-> 1000 documents = 6.45GB

