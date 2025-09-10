#!/usr/bin/env python3
"""
Xử lý file Module 6 S2 2025.docx
"""

import os
import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from docx_data_processor import DocxDataProcessor

services = {
    "embed_service_url": "http://localhost:8005",
    "database_service_url": "http://localhost:8002"
}


def check_services():
    """Kiểm tra các service có hoạt động không"""
    import requests
    
    print("🔍 Checking services...")
    all_ok = True

    for name, url in services.items():
        try:
            response = requests.get(url+"/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: OK")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                all_ok = False
        except Exception as e:
            print(f"❌ {name}: {e}")
            all_ok = False

    return all_ok


def process_module6_file_with_services():
    """Xử lý file Module 6 S2 2025.docx với embedding và database services"""
    print("Processing Module 6 S2 2025.docx with Services")
    print("="*60)

    processor = DocxDataProcessor(
        embed_service_url=services["embed_service_url"],
        database_service_url=services["database_service_url"],
        chunk_size=500,
        chunk_overlap=100
    )
    # File path
    file_path = "./data/Module 6 S2 2025.docx"

    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        return None

    print(f"📄 Processing file: {file_path}")
    start_time = time.time()

    # Process file với services
    result = processor.process_file(file_path)

    end_time = time.time()
    processing_time = end_time - start_time

    # Show results
    print(f"\n📊 Processing Results:")
    print(f"⏱️ Processing time: {processing_time:.2f} seconds")

    if result["success"]:
        print(f"✅ Success: {result['successful_chunks']}/{result['total_chunks']} chunks")
        print(f"❌ Failed: {result['failed_chunks']} chunks")
        print(f"📋 Metadata: {result['metadata']}")
        print(f"🔍 BM25 enabled: {result['bm25_enabled']}")
    else:
        print(f"❌ Failed: {result['error']}")

    # Show stats
    stats = processor.get_stats()
    print(f"\n📈 Processor Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    return result


def process_module6_file_with_service():
    """Xử lý file Module 6 S2 2025.docx với embedding service (REQUIRED)"""
    print("🔌 Processing Module 6 S2 2025.docx (Service Mode)")
    print("="*60)

    # Initialize processor
    processor = DocxDataProcessor(
        chunk_size=1500,
        chunk_overlap=50
    )

    # File path
    file_path = "./data/Module 6 S2 2025.docx"

    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        return

    try:
        print(f"Loading file: {file_path}")
        start_time = time.time()

        # 1. Load content
        content = processor.load_docx(file_path)
        print(f"✅ Loaded: {len(content)} characters")

        # 2. Clean text
        cleaned = processor.clean_text(content)
        print(f"✅ Cleaned: {len(cleaned)} characters")

        # 3. Extract metadata
        metadata = processor.extract_metadata(file_path)
        print(f"✅ Metadata: {metadata}")

        # 4. Chunk text
        chunks = processor.chunk_text(cleaned)
        print(f"✅ Chunks: {len(chunks)} pieces")

        # 5. BM25 is now handled by embedding service
        if processor.enable_bm25:
            print(f"🔍 BM25 sparse vectors handled by embedding service")
        else:
            print(f"🔍 BM25 disabled - dense vectors only")

        # 6. Show sample chunks
        print(f"\nSample chunks:")
        for i, chunk in enumerate(chunks[:3]):
            print(f"  Chunk {i+1} ({len(chunk)} chars): {chunk[:100]}...")

        # 7. Create sample payloads with REAL embeddings from service
        print(f"\nCreating payloads with real embeddings:")
        payloads = []
        for i, chunk in enumerate(chunks):
            payload = processor.create_payload(chunk, metadata, i)

            # Get REAL hybrid embedding from service (not dummy data)
            hybrid_result = processor.embed_text_hybrid(chunk)
            if hybrid_result:
                payload["vector"] = hybrid_result["dense_vector"]
                if hybrid_result["sparse_terms"] > 0:
                    payload["sparse_vector"] = hybrid_result["sparse_vector"]
                print(f"  ✅ Chunk {i+1}: Got real embedding ({hybrid_result['dense_dimension']} dims)")
            else:
                print(f"  ❌ Chunk {i+1}: Failed to get embedding from service")
                continue

            payloads.append(payload)

        print(f"✅ Created {len(payloads)} payloads with real embeddings")

        # 8. Show processing stats
        end_time = time.time()
        processing_time = end_time - start_time

        print(f"\n📊 Processing Summary:")
        print(f"⏱️ Processing time: {processing_time:.2f} seconds")
        print(f"📄 Original content: {len(content)} characters")
        print(f"🧹 Cleaned content: {len(cleaned)} characters")
        print(f"✂️ Total chunks: {len(chunks)}")
        print(f"📦 Total payloads: {len(payloads)}")

        # Show first payload details
        if payloads:
            print(f"\n📋 First payload details:")
            first_payload = payloads[0]
            print(f"  ID: {first_payload['id']}")
            print(f"  Vector dims: {len(first_payload['vector'])}")
            print(f"  Has sparse vector: {bool(first_payload.get('sparse_vector'))}")
            if first_payload.get('sparse_vector'):
                sparse = first_payload['sparse_vector']
                print(f"  Sparse vector terms: {len(sparse.get('indices', []))}")
            print(f"  Content preview: {first_payload['payload']['content'][:100]}...")

        return payloads

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Main function"""
    print("Module 6 S2 2025 Document Processor")
    print("="*60)

    # Check if services are running
    services_ok = check_services()

    if services_ok:
        print("\n✅ All services are running!")
        print("🚀 Processing with embedding and database services...")

        # Process với services
        result = process_module6_file_with_services()

        if result and result["success"]:
            print(f"\n🎉 Processing completed successfully!")
            print(f"✅ Processed: {result['successful_chunks']}/{result['total_chunks']} chunks")
            print(f"💾 Data saved to database with embeddings")
        else:
            print(f"\n❌ Processing with services failed!")

    else:
        print("\n⚠️ Services are not running!")
        print("💡 Start services with: docker-compose up embedding vectordb qdrant")
        print("❌ Cannot process without embedding service - all embeddings must go through service!")
        print("🚫 Offline mode removed - embedding service is required")


if __name__ == "__main__":
    main()
