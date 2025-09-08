#!/usr/bin/env python3
"""
Example usage của DocxDataProcessor
Demo các tính năng chính và cách sử dụng
"""

import os
import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from docx_data_processor import DocxDataProcessor


def check_services():
    """Kiểm tra các service có hoạt động không"""
    import requests
    
    services = {
        "Embedding Service": "http://localhost:8005/health",
        "Database Service": "http://localhost:8002/health"
    }
    
    print("🔍 Checking services...")
    all_ok = True
    
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: OK")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                all_ok = False
        except Exception as e:
            print(f"❌ {name}: {e}")
            all_ok = False
    
    return all_ok


def example_basic_usage():
    """Example cơ bản: xử lý một file"""
    print("\n" + "="*50)
    print("📄 EXAMPLE 1: Basic File Processing")
    print("="*50)
    
    # Initialize processor
    processor = DocxDataProcessor(
        embed_service_url="http://localhost:8005",
        database_service_url="http://localhost:8002",
        chunk_size=1500,
        chunk_overlap=50
    )
    
    # File path
    file_path = "./data/Module 6 S2 2025.docx"
    
    if not Path(file_path).exists():
        print(f"⚠️ File không tồn tại: {file_path}")
        print("💡 Tạo file test hoặc cập nhật đường dẫn")
        return
    
    print(f"🚀 Processing file: {file_path}")
    start_time = time.time()
    
    # Process file
    result = processor.process_file(file_path)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    # Show results
    print(f"\n📊 Results:")
    print(f"⏱️ Processing time: {processing_time:.2f} seconds")
    
    if result["success"]:
        print(f"✅ Success: {result['successful_chunks']}/{result['total_chunks']} chunks")
        print(f"📋 Metadata: {result['metadata']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Show stats
    stats = processor.get_stats()
    print(f"\n📈 Processor Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def example_directory_processing():
    """Example: xử lý tất cả file trong thư mục"""
    print("\n" + "="*50)
    print("📁 EXAMPLE 2: Directory Processing")
    print("="*50)
    
    processor = DocxDataProcessor(chunk_size=400)
    
    data_dir = "./data"
    if not Path(data_dir).exists():
        print(f"⚠️ Thư mục không tồn tại: {data_dir}")
        return
    
    print(f"🚀 Processing directory: {data_dir}")
    start_time = time.time()
    
    results = processor.process_directory(data_dir)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"\n📊 Directory Results:")
    print(f"⏱️ Total processing time: {processing_time:.2f} seconds")
    print(f"📄 Files processed: {len(results)}")
    
    successful_files = sum(1 for r in results if r["success"])
    print(f"✅ Successful: {successful_files}/{len(results)} files")
    
    # Detail per file
    for result in results:
        if result["success"]:
            print(f"  ✅ {Path(result['file_path']).name}: {result['successful_chunks']} chunks")
        else:
            print(f"  ❌ {Path(result['file_path']).name}: {result['error']}")
    
    # Overall stats
    stats = processor.get_stats()
    print(f"\n📈 Overall Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def example_text_cleaning():
    """Example: demo text cleaning"""
    print("\n" + "="*50)
    print("🧹 EXAMPLE 3: Text Cleaning Demo")
    print("="*50)
    
    processor = DocxDataProcessor()
    
    # Sample dirty text
    dirty_texts = [
        "  Hello   world  \n\n\n  This is   a test  \n\n  ",
        "Text\twith\ttabs\nand\r\ncarriage\rreturns",
        "\n\n\n   Multiple   \n\n   newlines   \n\n\n",
        "Normal text without issues"
    ]
    
    for i, dirty_text in enumerate(dirty_texts, 1):
        print(f"\n🧪 Test {i}:")
        print(f"📝 Original: {repr(dirty_text)}")
        
        cleaned = processor.clean_text(dirty_text)
        print(f"✨ Cleaned:  {repr(cleaned)}")
        
        print(f"📏 Length: {len(dirty_text)} → {len(cleaned)}")


def example_metadata_extraction():
    """Example: demo metadata extraction"""
    print("\n" + "="*50)
    print("📋 EXAMPLE 4: Metadata Extraction Demo")
    print("="*50)
    
    processor = DocxDataProcessor()
    
    # Sample filenames
    filenames = [
        "Module 6 S2 2025.docx",
        "math_week06_S2025.txt",
        "Week 3 Assignment.docx",
        "random_document.pdf",
        "Module 12 Final Project S1 2024.docx"
    ]
    
    for filename in filenames:
        print(f"\n📄 File: {filename}")
        metadata = processor.extract_metadata(filename)
        
        for key, value in metadata.items():
            print(f"  {key}: {value}")


def example_chunking():
    """Example: demo text chunking"""
    print("\n" + "="*50)
    print("✂️ EXAMPLE 5: Text Chunking Demo")
    print("="*50)
    
    # Test different chunk sizes
    chunk_sizes = [100, 200, 500]
    
    sample_text = """
    Welcome to Module 6 Writing in Practice. This module covers academic writing skills 
    including source integration, APA referencing, and critical reading. Learning outcomes 
    include effective communication and source evaluation. Students will learn to integrate 
    sources into their writing using various methods such as direct quotes, paraphrasing, 
    summarizing, and synthesizing. The module emphasizes the importance of proper citation 
    and reference formatting according to APA style guidelines.
    """ * 3  # Repeat to make it longer
    
    print(f"📝 Sample text length: {len(sample_text)} characters")
    
    for chunk_size in chunk_sizes:
        processor = DocxDataProcessor(chunk_size=chunk_size, chunk_overlap=20)
        chunks = processor.chunk_text(sample_text)
        
        print(f"\n✂️ Chunk size {chunk_size}:")
        print(f"  📊 Number of chunks: {len(chunks)}")
        
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"  📄 Chunk {i+1}: {len(chunk)} chars - {chunk[:50]}...")
        
        if len(chunks) > 3:
            print(f"  ... and {len(chunks) - 3} more chunks")


def example_offline_processing():
    """Example: xử lý offline (không gọi API)"""
    print("\n" + "="*50)
    print("🔌 EXAMPLE 6: Offline Processing (No API calls)")
    print("="*50)
    
    processor = DocxDataProcessor()
    
    file_path = "./data/Module 6 S2 2025.docx"
    
    if not Path(file_path).exists():
        print(f"⚠️ File không tồn tại: {file_path}")
        return
    
    try:
        print(f"📄 Loading file: {file_path}")
        
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

        # 5. Build BM25 corpus if enabled
        if processor.enable_bm25:
            print(f"🔍 Building BM25 corpus for sparse vectors...")
            processor.build_bm25_corpus(chunks)
            if processor.bm25_encoder and processor.bm25_encoder.corpus_stats_ready:
                corpus_info = processor.bm25_encoder.get_corpus_info()
                print(f"✅ BM25 corpus built: {corpus_info['vocabulary_size']} terms")

        # 6. Show sample chunks
        print(f"\n📄 Sample chunks:")
        for i, chunk in enumerate(chunks[:3]):
            print(f"  Chunk {i+1} ({len(chunk)} chars): {chunk[:100]}...")

        # 7. Create sample payloads (without embedding)
        print(f"\n📦 Sample payloads:")
        for i in range(min(2, len(chunks))):
            payload = processor.create_payload(chunks[i], metadata, i)
            payload["vector"] = [0.1] * 512  # Dummy vector

            print(f"  Payload {i+1}:")
            print(f"    ID: {payload['id']}")
            print(f"    Vector dims: {len(payload['vector'])}")
            print(f"    Has sparse vector: {bool(payload.get('sparse_vector'))}")
            if payload.get('sparse_vector'):
                sparse = payload['sparse_vector']
                print(f"    Sparse vector terms: {len(sparse.get('indices', []))}")
            print(f"    Content preview: {payload['payload']['content'][:50]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main function để chạy tất cả examples"""
    print("🚀 DocxDataProcessor Examples")
    print("="*60)
    
    # Check if services are running
    services_ok = check_services()
    
    if not services_ok:
        print("\n⚠️ Some services are not running!")
        print("💡 Start services with: docker-compose up embedding vectordb")
        print("🔌 Running offline examples only...")
        
        # Run offline examples
        example_text_cleaning()
        example_metadata_extraction()
        example_chunking()
        example_offline_processing()
        
    else:
        print("\n✅ All services are running!")
        print("🚀 Running full examples...")
        
        # Run all examples
        example_text_cleaning()
        example_metadata_extraction()
        example_chunking()
        example_offline_processing()
        example_basic_usage()
        example_directory_processing()
    
    print("\n" + "="*60)
    print("✅ Examples completed!")
    print("💡 Check the code in example_usage.py for implementation details")


if __name__ == "__main__":
    main()
