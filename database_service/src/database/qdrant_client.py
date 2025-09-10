"""
Qdrant Vector Database Client for Multi-Agent System.
Handles vector embeddings storage and retrieval for semantic search.
Supports both local Qdrant (Docker) and Qdrant Cloud configurations.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, Modifier, FieldCondition, MatchValue
from src.utils.logger import Logger

# Load environment variables
load_dotenv()

logger = Logger(__name__)


@dataclass
class VectorDocument:
    """Vector document model for Qdrant storage."""
    id: Union[str, int]
    content: str  # The content of chunk in source
    subject: str  # The subject like math, physic, etc
    title: str    # The title of file or session like season1
    week: str     # The number of week like week1, week2, week3, etc
    chunk_id: str # The id of chunk content in source
    timestamp: Optional[str] = None  # The time create
    vector_size: int = 384

    def __post_init__(self):
        """Post-initialization to set default values."""
        if self.vector_size is None:
            self.vector_size = 384

        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload format."""
        return {
            "content": self.content,
            "subject": self.subject,
            "title": self.title,
            "week": self.week,
            "chunk_id": self.chunk_id,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_payload(cls, doc_id: Union[str, int], payload: Dict[str, Any]) -> 'VectorDocument':
        """Create VectorDocument from Qdrant payload."""
        return cls(
            id=doc_id,
            content=payload.get("content", ""),
            subject=payload.get("subject", ""),
            title=payload.get("title", ""),
            week=payload.get("week", ""),
            chunk_id=payload.get("chunk_id", ""),
            timestamp=payload.get("timestamp")
        )


class QdrantConfig:
    """Qdrant database configuration and connection management."""

    def __init__(self,
                 api_key: str = None,
                 url: str = None,
                 collection_name: str = None,
                 vector_size: int = 384):
        """
        Initialize Qdrant configuration.
        Supports both local Qdrant (Docker) and Qdrant Cloud.

        Args:
            api_key: Qdrant Cloud API key (optional for local)
            url: Qdrant endpoint URL
            collection_name: Collection name for storing vectors
            vector_size: Vector dimension size
        """
        self.url = url or os.getenv("QDRANT_URL", "http://qdrant:6333")
        self.api_key = api_key or os.getenv("QDRANT_CLOUD_API_KEY")
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", "agent_data")
        self.vector_size = vector_size

        # Determine if using local or cloud based on URL and API key
        self.is_local = "qdrant:6333" in self.url or "127.0.0.1" in self.url

        if not self.url:
            raise ValueError("QDRANT_URL must be provided")

        if not self.is_local and not self.api_key:
            raise ValueError("QDRANT_CLOUD_API_KEY is required for cloud deployment")

        # Initialize Qdrant client
        client_kwargs = {"url": self.url}
        if not self.is_local and self.api_key:
            client_kwargs["api_key"] = self.api_key

        self.client = QdrantClient(**client_kwargs)

        logger.info(f"Qdrant client initialized ({'local' if self.is_local else 'cloud'}): {self.url}")

        # Test connection and create collection if needed
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize collection with proper configuration."""
        try:
            # Test connection
            self.client.get_collections()
            logger.info(f"✅ Connected to Qdrant ({'local' if self.is_local else 'cloud'}): {self.url}")

            # Check if collection exists
            if not self.client.collection_exists(collection_name=self.collection_name):
                logger.info(f"📦 Creating collection: {self.collection_name}")

                # Create collection with dense and sparse vectors
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense_vector": VectorParams(
                            size=self.vector_size,
                            distance=Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "bm25_sparse_vector": SparseVectorParams(
                            modifier=Modifier.IDF  # Enable Inverse Document Frequency
                        )
                    }
                )
                logger.info(f"Collection created successfully: {self.collection_name}")
                self._create_payload_indexes()
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
                self._create_payload_indexes()

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise

    def _create_payload_indexes(self):
        """Create payload indexes for efficient filtering."""
        try:
            # Create index for subject field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="subject",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            # Create index for title field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="title",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            # Create index for week field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="week",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            # Create index for chunk_id field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="chunk_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )

            logger.info(f"Payload indexes created successfully for {self.collection_name}")

        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("Payload indexes already exist")
            else:
                logger.warning(f"Failed to create some payload indexes: {e}")
    
    def upsert_document(self, 
                       document: VectorDocument, 
                       dense_vector: List[float],
                       sparse_vector: Optional[Dict[str, Any]] = None) -> bool:
        """
        Insert or update a document in Qdrant.
        
        Args:
            document: VectorDocument to store
            dense_vector: Dense embedding vector (384 dimensions)
            sparse_vector: Optional sparse vector for BM25
            
        Returns:
            bool: Success status
        """
        try:
            # Prepare vectors
            vectors = {
                "dense_vector": dense_vector
            }
            
            if sparse_vector:
                vectors["bm25_sparse_vector"] = sparse_vector
            
            # Upsert point
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=document.id,
                        vector=vectors,
                        payload=document.to_payload()
                    )
                ]
            )
            
            logger.info(f"Document upserted: {document.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert document: {e}")
            return False
    
    def search_similar(self,
                      query_vector: List[float],
                      limit: int = 10,
                      score_threshold: float = 0.7,
                      filter_conditions: Optional[models.Filter] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents using dense vector.
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Optional filter conditions
            
        Returns:
            List of similar documents with scores
        """
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=("dense_vector", query_vector),
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_conditions,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for point in search_result:
                doc = VectorDocument.from_payload(point.id, point.payload)
                results.append({
                    "document": doc,
                    "score": point.score,
                    "id": point.id
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    def get_document(self, doc_id: Union[str, int]) -> Optional[VectorDocument]:
        """
        Get a specific document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            VectorDocument or None if not found
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[doc_id],
                with_payload=True,
                with_vectors=False
            )
            
            if result:
                point = result[0]
                return VectorDocument.from_payload(point.id, point.payload)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    def delete_document(self, doc_id: Union[str, int]) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            bool: Success status
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[doc_id]
                )
            )
            
            logger.info(f"Document deleted: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def get_collection_info(self) -> Optional[Dict[str, Any]]:
        """Get collection information and statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "config": {
                    "vector_size": info.config.params.vectors.get("dense_vector", {}).size if info.config.params.vectors else None,
                    "distance": info.config.params.vectors.get("dense_vector", {}).distance if info.config.params.vectors else None
                }
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None

    def check_file_exists(self, subject: str, title: str, week: str = None, chunk_id: str = None) -> Optional[VectorDocument]:
        """
        Check if a file has already been embedded.

        Args:
            subject: Subject like math, physic, etc
            title: Title of file or session
            week: Optional week number
            chunk_id: Optional chunk ID

        Returns:
            VectorDocument if exists, None otherwise
        """
        try:
            # Build filter conditions using proper Qdrant models
            must_conditions = [
                models.FieldCondition(
                    key="subject",
                    match=models.MatchValue(value=subject)
                ),
                models.FieldCondition(
                    key="title",
                    match=models.MatchValue(value=title)
                )
            ]

            if week:
                must_conditions.append(
                    models.FieldCondition(
                        key="week",
                        match=models.MatchValue(value=week)
                    )
                )

            if chunk_id:
                must_conditions.append(
                    models.FieldCondition(
                        key="chunk_id",
                        match=models.MatchValue(value=chunk_id)
                    )
                )

            filter_conditions = models.Filter(must=must_conditions)

            # Use scroll to find points with filter
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_conditions,
                limit=1,
                with_payload=True,
                with_vectors=False
            )

            if results:
                point = results[0]
                return VectorDocument.from_payload(point.id, point.payload or {})

            return None

        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return None





    def delete_vectors_by_filter(self, subject: str = None, title: str = None, week: str = None, chunk_id: str = None) -> bool:
        """
        Delete vectors by filter conditions.

        Args:
            subject: Subject filter
            title: Title filter
            week: Week filter
            chunk_id: Chunk ID filter

        Returns:
            bool: Success status
        """
        try:
            if not any([subject, title, week, chunk_id]):
                logger.error("At least one filter condition must be provided")
                return False

            # Build filter conditions
            must_conditions = []

            if subject:
                must_conditions.append(
                    models.FieldCondition(
                        key="subject",
                        match=models.MatchValue(value=subject)
                    )
                )

            if title:
                must_conditions.append(
                    models.FieldCondition(
                        key="title",
                        match=models.MatchValue(value=title)
                    )
                )

            if week:
                must_conditions.append(
                    models.FieldCondition(
                        key="week",
                        match=models.MatchValue(value=week)
                    )
                )

            if chunk_id:
                must_conditions.append(
                    models.FieldCondition(
                        key="chunk_id",
                        match=models.MatchValue(value=chunk_id)
                    )
                )

            filter_conditions = models.Filter(must=must_conditions)

            # Count before deletion for logging
            count_result, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_conditions,
                limit=100,
                with_payload=False,
                with_vectors=False
            )

            if count_result:
                # Delete points with filter
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.FilterSelector(filter=filter_conditions)
                )
                logger.info(f"Deleted {len(count_result)} vectors")
                return True
            else:
                logger.info("No vectors found matching the filter conditions")
                return False

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    def get_documents_by_filter(self, subject: str = None, title: str = None, week: str = None, limit: int = 100) -> List[VectorDocument]:
        """
        Get documents by filter conditions.

        Args:
            subject: Subject filter
            title: Title filter
            week: Week filter
            limit: Maximum number of documents to return

        Returns:
            List of VectorDocument matching the filters
        """
        try:
            # Build filter conditions
            must_conditions = []

            if subject:
                must_conditions.append(
                    models.FieldCondition(
                        key="subject",
                        match=models.MatchValue(value=subject)
                    )
                )

            if title:
                must_conditions.append(
                    models.FieldCondition(
                        key="title",
                        match=models.MatchValue(value=title)
                    )
                )

            if week:
                must_conditions.append(
                    models.FieldCondition(
                        key="week",
                        match=models.MatchValue(value=week)
                    )
                )

            # If no filters provided, get all documents
            filter_conditions = models.Filter(must=must_conditions) if must_conditions else None

            # Use scroll to get documents
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_conditions,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            documents = []
            for point in results:
                doc = VectorDocument.from_payload(point.id, point.payload or {})
                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []


# Global Qdrant configuration instance
_qdrant_config: Optional[QdrantConfig] = None


def get_qdrant_config() -> QdrantConfig:
    """Get or create Qdrant configuration instance."""
    global _qdrant_config
    
    if _qdrant_config is None:
        _qdrant_config = QdrantConfig()
    
    return _qdrant_config


def close_qdrant_connection():
    """Close Qdrant connection."""
    global _qdrant_config
    
    if _qdrant_config:
        # Qdrant client doesn't need explicit closing
        _qdrant_config = None


# Utility functions
def generate_document_id() -> str:
    """Generate a unique document ID."""
    return str(uuid.uuid4())


def create_vector_document(content: str,
                          subject: str,
                          title: str,
                          week: str,
                          chunk_id: str) -> VectorDocument:
    """
    Create a VectorDocument with proper structure.

    Args:
        content: The content of chunk in source
        subject: The subject like math, physic, etc
        title: The title of file or session like season1
        week: The number of week like week1, week2, week3, etc
        chunk_id: The id of chunk content in source

    Returns:
        VectorDocument instance
    """
    doc_id = generate_document_id()

    return VectorDocument(
        id=doc_id,
        content=content,
        subject=subject,
        title=title,
        week=week,
        chunk_id=chunk_id
    )