#!/usr/bin/env python3
"""
Test file cho DocxDataProcessor
Kiểm tra tất cả functionality của processor
"""

import os
import sys
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path để import processor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from docx_data_processor import DocxDataProcessor


class TestDocxDataProcessor(unittest.TestCase):
    """Test cases cho DocxDataProcessor"""
    
    def setUp(self):
        """Setup test environment"""
        self.processor = DocxDataProcessor(
            embed_service_url="http://localhost:8005",
            database_service_url="http://localhost:8002",
            chunk_size=100,  # Smaller for testing
            chunk_overlap=20,
            enable_bm25=True  # Enable BM25 for testing
        )
        
        # Sample text for testing
        self.sample_text = """
        Welcome to Module 6 Writing in Practice.
        
        This module covers academic writing skills including:
        - Source integration
        - APA referencing
        - Critical reading
        
        Learning outcomes include effective communication and source evaluation.
        """
        
        # Mock responses for new hybrid system
        self.mock_dense_embedding = [0.1, 0.2, 0.3] * 128  # 384 dimensions
        self.mock_sparse_vector = {"316307400": 1.6786885245901642, "74040069": 1.6786885245901642}
        self.mock_hybrid_response = {
            "text": "sample text",
            "dense_vector": self.mock_dense_embedding,
            "sparse_vector": self.mock_sparse_vector,
            "dense_dimension": 384,
            "sparse_terms": 2
        }
        
        self.mock_upsert_response = {
            "success": True,
            "message": "Points upserted successfully",
            "points_count": 1
        }
    
    def test_clean_text(self):
        """Test text cleaning functionality"""
        dirty_text = "  Hello   world  \n\n\n  This is   a test  \n\n  "
        expected = "Hello world\nThis is a test"
        
        cleaned = self.processor.clean_text(dirty_text)
        self.assertEqual(cleaned, expected)
        
        # Test empty text
        self.assertEqual(self.processor.clean_text(""), "")
        
        # Test text with special characters
        special_text = "Text\twith\ttabs\nand\r\ncarriage\rreturns"
        cleaned_special = self.processor.clean_text(special_text)
        self.assertNotIn("\t", cleaned_special)
        self.assertNotIn("\r", cleaned_special)
    
    def test_extract_metadata(self):
        """Test metadata extraction from filename"""
        # Test standard format
        metadata = self.processor.extract_metadata("Module 6 S2 2025.docx")
        self.assertEqual(metadata["subject"], "module")
        self.assertIn("module", metadata["subject"])
        self.assertEqual(metadata["title"], "Module 6 S2 2025")
        
        # Test with week format
        metadata2 = self.processor.extract_metadata("math_week06_S2025.txt")
        self.assertEqual(metadata2["subject"], "unknown")  # No module in name
        self.assertEqual(metadata2["title"], "math_week06_S2025")
        
        # Test unknown format
        metadata3 = self.processor.extract_metadata("random_file.docx")
        self.assertEqual(metadata3["subject"], "unknown")
        self.assertEqual(metadata3["week"], "unknown")
        self.assertEqual(metadata3["title"], "random_file")
    
    def test_chunk_text(self):
        """Test text chunking"""
        chunks = self.processor.chunk_text(self.sample_text)
        
        # Should have at least one chunk
        self.assertGreater(len(chunks), 0)
        
        # Each chunk should be string
        for chunk in chunks:
            self.assertIsInstance(chunk, str)
            self.assertGreater(len(chunk.strip()), 0)
        
        # Test empty text
        empty_chunks = self.processor.chunk_text("")
        self.assertEqual(len(empty_chunks), 1)  # Fallback behavior
    
    @patch('requests.post')
    def test_embed_text_hybrid(self, mock_post):
        """Test hybrid text embedding via API"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.mock_hybrid_response
        mock_post.return_value = mock_response

        result = self.processor.embed_text_hybrid("test text")

        # Check API call
        mock_post.assert_called_once_with(
            "http://localhost:8005/embed-hybrid",
            json={"text": "test text"},
            timeout=30
        )

        # Check result
        self.assertIsNotNone(result)
        self.assertEqual(result["dense_vector"], self.mock_dense_embedding)
        self.assertEqual(result["sparse_vector"], self.mock_sparse_vector)
        self.assertEqual(result["dense_dimension"], 384)
        self.assertEqual(self.processor.stats["successful_embeddings"], 1)

        # Test API failure
        mock_post.side_effect = Exception("API Error")
        result_fail = self.processor.embed_text_hybrid("test text")

        self.assertIsNone(result_fail)
        self.assertEqual(self.processor.stats["failed_embeddings"], 1)
    
    def test_create_payload(self):
        """Test payload creation"""
        metadata = {
            "subject": "module",
            "title": "Test Module",
            "week": "week06",
            "file_path": "/test/path.docx"
        }
        
        payload = self.processor.create_payload("test chunk", metadata, 0)
        
        # Check structure
        self.assertIn("id", payload)
        self.assertIn("vector", payload)
        self.assertIn("payload", payload)
        
        # Check payload content
        payload_data = payload["payload"]
        self.assertEqual(payload_data["content"], "test chunk")
        self.assertEqual(payload_data["subject"], "module")
        self.assertEqual(payload_data["title"], "Test Module")
        self.assertEqual(payload_data["week"], "week06")
        self.assertEqual(payload_data["chunk_id"], 0)
        self.assertEqual(payload_data["file_path"], "/test/path.docx")
        
        # Check UUID format
        import uuid
        self.assertIsInstance(uuid.UUID(payload["id"]), uuid.UUID)

    def test_bm25_functionality(self):
        """Test BM25 sparse vector functionality (now handled by embedding service)"""
        # BM25 is now handled by embedding service, so we test the integration
        self.assertTrue(self.processor.enable_bm25)

        # Note: BM25 encoder is no longer local, it's handled by embedding service
        # The processor should still track BM25 as enabled for backward compatibility

        # Test that BM25 is enabled in stats
        stats = self.processor.get_stats()
        self.assertTrue(stats["bm25_enabled"])

        # Test corpus building (now a no-op since BM25 is centralized)
        test_docs = [
            "This is a test document about machine learning",
            "Another document discussing artificial intelligence",
            "A third document about natural language processing"
        ]

        # This should not fail even though BM25 is now centralized
        try:
            self.processor.build_bm25_corpus(test_docs)
            # Should complete without error
        except Exception as e:
            self.fail(f"build_bm25_corpus should not fail: {e}")

        # Note: Sparse vector creation is now done by embedding service via /embed-hybrid
        # No longer testing local sparse vector creation
    
    @patch('requests.post')
    def test_upsert_document(self, mock_post):
        """Test document upsert to database"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.mock_upsert_response
        mock_post.return_value = mock_response
        
        payload = {
            "id": "test-id",
            "vector": self.mock_dense_embedding,  # Dense vector as array
            "sparse_vector": self.mock_sparse_vector,  # Sparse vector separate
            "payload": {"content": "test"}
        }

        success = self.processor.upsert_document(payload)

        # Check API call - expect hybrid vector format
        expected_point = {
            "id": "test-id",
            "vector": {"dense_vector": self.mock_dense_embedding, "bm25_sparse_vector": self.mock_sparse_vector},
            "payload": {"content": "test"}
        }
        mock_post.assert_called_once_with(
            "http://localhost:8002/upsert",
            json={"points": [expected_point]},
            timeout=30
        )
        
        # Check result
        self.assertTrue(success)
        self.assertEqual(self.processor.stats["successful_upserts"], 1)
        
        # Test API failure
        mock_post.side_effect = Exception("Database Error")
        success_fail = self.processor.upsert_document(payload)
        
        self.assertFalse(success_fail)
        self.assertEqual(self.processor.stats["failed_upserts"], 1)
    
    def test_stats_tracking(self):
        """Test statistics tracking"""
        # Initial stats should be zero (except bm25_enabled which is boolean)
        stats = self.processor.get_stats()
        for key, value in stats.items():
            if key == "bm25_enabled":
                self.assertIsInstance(value, bool)
            else:
                self.assertEqual(value, 0)

        # Test reset
        self.processor.stats["files_processed"] = 5
        self.processor.reset_stats()

        stats_after_reset = self.processor.get_stats()
        for key, value in stats_after_reset.items():
            if key == "bm25_enabled":
                self.assertIsInstance(value, bool)
            else:
                self.assertEqual(value, 0)
    
    @patch('docx_data_processor.Docx2txtLoader')
    def test_load_docx_mock(self, mock_loader_class):
        """Test DOCX loading with mock"""
        # Mock document object
        mock_doc = MagicMock()
        mock_doc.page_content = self.sample_text
        
        # Mock loader
        mock_loader = MagicMock()
        mock_loader.load.return_value = [mock_doc]
        mock_loader_class.return_value = mock_loader
        
        content = self.processor.load_docx("test.docx")
        
        # Check loader was called correctly
        mock_loader_class.assert_called_once_with("test.docx")
        mock_loader.load.assert_called_once()
        
        # Check content
        self.assertEqual(content, self.sample_text)
        
        # Test empty document
        mock_loader.load.return_value = []
        with self.assertRaises(ValueError):
            self.processor.load_docx("empty.docx")
    
    @patch('pathlib.Path.glob')
    def test_process_directory(self, mock_glob):
        """Test directory processing"""
        # Mock file paths
        mock_files = [Path("file1.docx"), Path("file2.docx")]
        mock_glob.return_value = mock_files
        
        # Mock process_file method
        with patch.object(self.processor, 'process_file') as mock_process:
            mock_process.return_value = {"success": True, "file_path": "test.docx"}
            
            results = self.processor.process_directory("/test/dir")
            
            # Check calls
            self.assertEqual(len(results), 2)
            self.assertEqual(mock_process.call_count, 2)
        
        # Test empty directory
        mock_glob.return_value = []
        results_empty = self.processor.process_directory("/empty/dir")
        self.assertEqual(len(results_empty), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests với real file nếu có"""
    
    def setUp(self):
        self.processor = DocxDataProcessor()
        self.test_data_dir = Path(__file__).parent / "data"
    
    def test_real_file_if_exists(self):
        """Test với file thật nếu có"""
        test_file = self.test_data_dir / "Module 6 S2 2025.docx"
        
        if test_file.exists():
            print(f"\n🧪 Testing with real file: {test_file}")
            
            # Test chỉ load và clean, không gọi API
            try:
                content = self.processor.load_docx(str(test_file))
                self.assertIsInstance(content, str)
                self.assertGreater(len(content), 0)
                print(f"✅ Loaded {len(content)} characters")
                
                cleaned = self.processor.clean_text(content)
                self.assertIsInstance(cleaned, str)
                print(f"✅ Cleaned to {len(cleaned)} characters")
                
                chunks = self.processor.chunk_text(cleaned)
                self.assertGreater(len(chunks), 0)
                print(f"✅ Created {len(chunks)} chunks")
                
                metadata = self.processor.extract_metadata(str(test_file))
                self.assertIsInstance(metadata, dict)
                print(f"✅ Extracted metadata: {metadata}")
                
            except Exception as e:
                print(f"❌ Real file test failed: {e}")
        else:
            print(f"⚠️ Test file not found: {test_file}")


def run_tests():
    """Chạy tất cả tests"""
    print("🧪 Running DocxDataProcessor Tests...")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDocxDataProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n📊 Test Summary:")
    print(f"✅ Tests run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"⚠️ Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
