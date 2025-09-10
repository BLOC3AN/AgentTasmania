#!/usr/bin/env python3
"""
DOCX Data Processor
Xử lý tài liệu DOCX từ nguồn đến embedding tự động
- Load tài liệu DOCX
- Làm sạch và chuẩn hóa nội dung  
- Chia nhỏ thành chunks
- Tạo embedding qua API
- Lưu vào vector database
"""

import os
import re
import uuid
import requests
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_community.document_loaders import Docx2txtLoader
from langchain.text_splitter import TokenTextSplitter
# Removed: from .fastembed_bm25_encoder import FastEmbedBM25Encoder
# Now using centralized embed-hybrid endpoint

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)





class DocxDataProcessor:
    """Processor để xử lý tài liệu DOCX tự động"""
    
    def __init__(
        self,
        embed_service_url: str = "http://13.210.111.152:8005",
        database_service_url: str = "http://13.210.111.152:8002",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        enable_bm25: bool = True
    ):
        self.embed_service_url = embed_service_url
        self.database_service_url = database_service_url
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_bm25 = enable_bm25

        # Text splitter cho chunking
        self.text_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Note: BM25 now handled by embedding service via /embed-hybrid
        # No need for local BM25 encoder anymore

        # Stats tracking
        self.stats = {
            "files_processed": 0,
            "total_chunks": 0,
            "successful_embeddings": 0,
            "failed_embeddings": 0,
            "successful_upserts": 0,
            "failed_upserts": 0,
            "bm25_enabled": enable_bm25
        }
        
    def load_docx(self, file_path: str) -> str:
        """Load nội dung từ file DOCX"""
        try:
            logger.info(f"📄 Loading DOCX file: {file_path}")
            loader = Docx2txtLoader(file_path)
            documents = loader.load()
            
            if not documents:
                raise ValueError("Không thể load nội dung từ file DOCX")
                
            content = "\n".join([doc.page_content for doc in documents])
            logger.info(f"✅ Loaded {len(content)} characters from DOCX")
            return content
            
        except Exception as e:
            logger.error(f"❌ Lỗi load DOCX {file_path}: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """Làm sạch và chuẩn hóa text"""
        try:
            # Loại bỏ ký tự đặc biệt và normalize whitespace
            text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs -> single space
            text = re.sub(r'\n+', '\n', text)  # Multiple newlines -> single newline
            text = re.sub(r'\r', '', text)  # Remove carriage returns
            text = text.strip()

            # Loại bỏ các dòng trống
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)

            logger.debug(f"🧹 Cleaned text: {len(text)} -> {len(cleaned_text)} chars")
            return cleaned_text

        except Exception as e:
            logger.error(f"❌ Lỗi clean text: {e}")
            return text
    
    def extract_metadata(self, file_path: str) -> Dict[str, str]:
        """Extract metadata từ tên file"""
        try:
            file_name = Path(file_path).stem
            parts = file_name.split()
            
            # Mặc định metadata
            metadata = {
                "subject": "unknown",
                "week": "unknown",
                "title": file_name
            }
            
            # Tìm pattern "Module X" hoặc "Week X"
            for part in parts:
                if part.lower().startswith('module'):
                    metadata["subject"] = part.lower()
                elif part.lower().startswith('week') or part.lower().startswith('w'):
                    metadata["week"] = part.lower()
                elif 's2' in part.lower() or 's1' in part.lower():
                    metadata["semester"] = part.lower()
            
            logger.debug(f"📋 Extracted metadata: {metadata}")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract metadata: {e}")
            return {"subject": "unknown", "week": "unknown", "title": Path(file_path).stem}
    
    def chunk_text(self, text: str) -> List[str]:
        """Chia text thành chunks"""
        try:
            if not text.strip():
                return [""]  # Return empty string for empty input

            chunks = self.text_splitter.split_text(text)
            logger.info(f"✂️ Split into {len(chunks)} chunks")
            return chunks if chunks else [text]  # Ensure at least one chunk

        except Exception as e:
            logger.error(f"❌ Lỗi chunk text: {e}")
            return [text]  # Fallback: return original text as single chunk
    
    def embed_text_hybrid(self, text: str) -> Optional[Dict[str, Any]]:
        """Tạo hybrid embedding (dense + sparse) cho text qua API"""
        try:
            response = requests.post(
                f"{self.embed_service_url}/embed-hybrid",
                json={"text": text},
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            self.stats["successful_embeddings"] += 1

            dense_dim = result.get("dense_dimension", 0)
            sparse_terms = result.get("sparse_terms", 0)
            logger.debug(f"🔢 Created hybrid embedding: {dense_dim}D dense, {sparse_terms} sparse terms")

            return {
                "dense_vector": result["dense_vector"],
                "sparse_vector": result["sparse_vector"],
                "dense_dimension": dense_dim,
                "sparse_terms": sparse_terms
            }

        except Exception as e:
            logger.error(f"❌ Lỗi embed hybrid text: {e}")
            self.stats["failed_embeddings"] += 1
            return None
    
    # Removed: create_sparse_vector method
    # Sparse vectors now created by embedding service via /embed-hybrid

    def build_bm25_corpus(self, texts: List[str]):
        """Build BM25 corpus - now handled by embedding service, this is a no-op"""
        # BM25 corpus building is now handled by the centralized embedding service
        # This method is kept for backward compatibility but does nothing
        logger.info(f"🔍 BM25 corpus building skipped - handled by embedding service")

    def create_payload(self, chunk: str, metadata: Dict[str, str], chunk_id: int) -> Dict[str, Any]:
        """Tạo payload theo format chuẩn với hybrid vectors"""
        payload = {
            "id": str(uuid.uuid4()),  # UUID format for Qdrant compatibility
            "vector": None,  # Dense vector - sẽ được set sau khi embed
            "payload": {
                "content": chunk,
                "subject": metadata["subject"],
                "title": metadata["title"],
                "week": metadata["week"],
                "chunk_id": chunk_id,
                "file_path": metadata.get("file_path", "")
            }
        }

        # Note: Sparse vectors are now created by embedding service via /embed-hybrid
        # No need to create them locally anymore

        return payload
    
    def upsert_document(self, payload: Dict[str, Any]) -> bool:
        """Upsert document vào vector database với hybrid vectors"""
        try:
            # Prepare the point for Qdrant format
            point = {
                "id": payload["id"],
                "vector": {},
                "payload": payload["payload"]
            }

            # Add dense vector
            if payload.get("vector"):
                point["vector"]["dense_vector"] = payload["vector"]

            # Add sparse vector if available (convert to Qdrant format)
            if payload.get("sparse_vector"):
                sparse_vector = payload["sparse_vector"]
                # Convert to Qdrant sparse vector format: {"indices": [...], "values": [...]}
                if isinstance(sparse_vector, dict):
                    indices = [int(k) for k in sparse_vector.keys()]
                    values = list(sparse_vector.values())
                    point["vector"]["bm25_sparse_vector"] = {
                        "indices": indices,
                        "values": values
                    }
                else:
                    point["vector"]["bm25_sparse_vector"] = sparse_vector

            request_data = {"points": [point]}

            response = requests.post(
                f"{self.database_service_url}/upsert",
                json=request_data,
                timeout=30
            )
            response.raise_for_status()

            success = response.json().get("success", False)
            if success:
                self.stats["successful_upserts"] += 1
                logger.debug(f"✅ Upserted with {'hybrid' if payload.get('sparse_vector') else 'dense'} vectors")
            else:
                self.stats["failed_upserts"] += 1

            return success

        except Exception as e:
            logger.error(f"❌ Lỗi upsert: {e}")
            self.stats["failed_upserts"] += 1
            return False
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Xử lý một file DOCX hoàn chỉnh với hybrid vectors"""
        try:
            logger.info(f"🚀 Bắt đầu xử lý file: {file_path}")

            # 1. Load DOCX
            content = self.load_docx(file_path)

            # 2. Clean text
            cleaned_content = self.clean_text(content)

            # 3. Extract metadata
            metadata = self.extract_metadata(file_path)
            metadata["file_path"] = file_path

            # 4. Chunk text
            chunks = self.chunk_text(cleaned_content)

            # 5. Build BM25 corpus if enabled
            if self.enable_bm25:
                logger.info("🔍 Building BM25 corpus for sparse vectors...")
                self.build_bm25_corpus(chunks)

            # 6. Process từng chunk
            successful_chunks = 0
            failed_chunks = 0

            for i, chunk in enumerate(chunks):
                logger.info(f"📄 Processing chunk {i+1}/{len(chunks)}")

                # Get hybrid embedding (dense + sparse)
                hybrid_result = self.embed_text_hybrid(chunk)
                if hybrid_result is None:
                    failed_chunks += 1
                    continue

                # Tạo payload với hybrid vectors
                payload = self.create_payload(chunk, metadata, i)
                payload["vector"] = hybrid_result["dense_vector"]

                # Add sparse vector if available
                if hybrid_result["sparse_terms"] > 0:
                    payload["sparse_vector"] = hybrid_result["sparse_vector"]

                # Upsert vào database
                success = self.upsert_document(payload)
                if success:
                    successful_chunks += 1
                    vector_type = "hybrid" if payload.get("sparse_vector") else "dense"
                    logger.debug(f"✅ Chunk {i+1} processed successfully ({vector_type})")
                else:
                    failed_chunks += 1
                    logger.warning(f"❌ Chunk {i+1} failed to upsert")

            # Update stats
            self.stats["files_processed"] += 1
            self.stats["total_chunks"] += len(chunks)

            result = {
                "success": True,
                "file_path": file_path,
                "total_chunks": len(chunks),
                "successful_chunks": successful_chunks,
                "failed_chunks": failed_chunks,
                "metadata": metadata,
                "bm25_enabled": self.enable_bm25
            }

            logger.info(f"✅ File processed: {successful_chunks}/{len(chunks)} chunks successful")
            if self.enable_bm25:
                logger.info(f"🔍 BM25 sparse vectors enabled for hybrid search")
            return result

        except Exception as e:
            logger.error(f"❌ Lỗi xử lý file {file_path}: {e}")
            return {
                "success": False,
                "file_path": file_path,
                "error": str(e)
            }
    
    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Xử lý tất cả file DOCX trong thư mục"""
        try:
            directory = Path(directory_path)
            docx_files = list(directory.glob("*.docx"))
            
            if not docx_files:
                logger.warning(f"⚠️ Không tìm thấy file DOCX nào trong {directory_path}")
                return []
            
            logger.info(f"📁 Tìm thấy {len(docx_files)} file DOCX")
            
            results = []
            for file_path in docx_files:
                result = self.process_file(str(file_path))
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý thư mục {directory_path}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, int]:
        """Lấy thống kê xử lý"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset thống kê (except bm25_enabled)"""
        for key in self.stats:
            if key != "bm25_enabled":
                self.stats[key] = 0


def main():
    """Main function để demo basic usage với hybrid vectors"""
    print("🚀 DocxDataProcessor Demo (Hybrid Vectors)")
    print("="*50)

    # Initialize processor với BM25 enabled
    processor = DocxDataProcessor(
        embed_service_url="http://localhost:8005",
        database_service_url="http://localhost:8002",
        chunk_size=300,
        chunk_overlap=50,
        enable_bm25=True  # Enable hybrid search
    )

    print(f"🔍 BM25 Sparse Vectors: {'✅ Enabled' if processor.enable_bm25 else '❌ Disabled'}")

    # Check if test file exists
    test_file = "./data/Module 6 S2 2025.docx"
    if not Path(test_file).exists():
        print(f"⚠️ Test file not found: {test_file}")
        print("💡 Please add a DOCX file to the data directory")
        return

    try:
        print(f"📄 Processing: {test_file}")
        result = processor.process_file(test_file)

        if result["success"]:
            print(f"✅ Success!")
            print(f"📊 Chunks: {result['successful_chunks']}/{result['total_chunks']}")
            print(f"� BM25 Enabled: {result.get('bm25_enabled', False)}")
            print(f"�📋 Metadata: {result['metadata']}")
        else:
            print(f"❌ Failed: {result['error']}")

        # Show stats
        stats = processor.get_stats()
        print(f"\n📈 Stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # BM25 info now handled by embedding service
        if processor.enable_bm25:
            print(f"\n🔍 BM25 Status: Enabled (handled by embedding service)")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
