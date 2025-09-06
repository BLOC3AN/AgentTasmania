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
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, Modifier
from src.utils.logger import Logger

# Load environment variables
load_dotenv()

logger = Logger(__name__)


@dataclass
class VectorDocument:
    """Vector document model for Qdrant storage."""
    id: Union[str, int]
    text: str
    user_id: str
    title: Optional[str] = None
    source: Optional[str] = None
    file_id: Optional[str] = None
    page: Optional[int] = None
    timestamp: Optional[str] = None
    vector_size: int = 512
    
    def __post_init__(self):
        """Post-initialization to set default values."""
        if self.vector_size is None:
            self.vector_size = 512

        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload format."""
        return {
            "text": self.text,
            "user_id": self.user_id,
            "title": self.title,
            "file_id": self.file_id,
            "source": self.source,
            "page": self.page,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_payload(cls, doc_id: Union[str, int], payload: Dict[str, Any]) -> 'VectorDocument':
        """Create VectorDocument from Qdrant payload."""
        return cls(
            id=doc_id,
            text=payload.get("text", ""),
            user_id=payload.get("user_id", ""),
            title=payload.get("title"),
            source=payload.get("source"),
            file_id=payload.get("file_id"),
            page=payload.get("page"),
            timestamp=payload.get("timestamp")
        )


class QdrantConfig:
    """Qdrant database configuration and connection management."""

    def __init__(self,
                 api_key: str = None,
                 url: str = None,
                 collection_name: str = None,
                 vector_size: int = 512):
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
            # Create index for user_id field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            # Create index for title field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="title",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            # Create index for source field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="source",
                field_schema=models.PayloadSchemaType.KEYWORD
            )

            # Create index for file_id field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="file_id",
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
            dense_vector: Dense embedding vector (1024 dimensions)
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
                      filter_conditions: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
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
                query_filter=models.Filter(**filter_conditions) if filter_conditions else None,
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

    def check_file_exists(self, user_id: str, file_id: str = None, title: str = None, source: str = None) -> Optional[VectorDocument]:
        """
        Check if a file has already been embedded for a user.
        Supports both regular files and chunked files.

        Args:
            user_id: User ID
            file_id: Unique file identifier (preferred)
            title: File title (fallback)
            source: Optional source/file_key for more specific matching

        Returns:
            VectorDocument if exists, None otherwise
        """
        try:
            # Prefer file_id if provided, otherwise use title
            identifier = file_id if file_id else title
            if not identifier:
                logger.error("Either file_id or title must be provided")
                return None

            # First try exact match
            exact_result = self._check_file_exact_match(user_id, identifier, source, use_file_id=bool(file_id))
            if exact_result:
                return exact_result

            # If no exact match, try chunked file match (for PDF files)
            chunked_result = self._check_chunked_file_exists(user_id, identifier, source)
            if chunked_result:
                return chunked_result

            return None

        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return None

    def _check_file_exact_match(self, user_id: str, identifier: str, source: str = None, use_file_id: bool = True) -> Optional[VectorDocument]:
        """Check for exact file match using file_id or title field."""
        try:
            # Build filter conditions for exact match
            field_name = "file_id" if use_file_id else "title"
            must_conditions = [
                {
                    "key": "user_id",
                    "match": {"value": user_id}
                },
                {
                    "key": field_name,
                    "match": {"value": identifier}
                }
            ]

            if source:
                must_conditions.append({
                    "key": "source",
                    "match": {"value": source}
                })

            filter_conditions = {
                "must": must_conditions
            }

            # Use scroll to find points with filter
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(**filter_conditions),
                limit=1,
                with_payload=True,
                with_vectors=False
            )

            if results:
                point = results[0]
                return VectorDocument.from_payload(point.id, point.payload)

            return None

        except Exception as e:
            logger.error(f"Error in exact match check: {e}")
            return None

    def _check_chunked_file_exists(self, user_id: str, identifier: str, source: str = None) -> Optional[VectorDocument]:
        """Check for chunked file existence (for PDF files)."""
        try:
            # Method 1: Check using title field for chunked files
            try:
                must_conditions = [
                    {
                        "key": "user_id",
                        "match": {"value": user_id}
                    },
                    {
                        "key": "title",
                        "match": {"value": identifier}
                    }
                ]

                filter_conditions = {"must": must_conditions}

                results, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(**filter_conditions),
                    limit=1,
                    with_payload=True,
                    with_vectors=False
                )

                if results:
                    point = results[0]
                    return VectorDocument.from_payload(point.id, point.payload)

            except Exception as e:
                logger.warning(f"Method 1 (title) failed: {e}")

            # Method 2: Check for chunks using source field pattern
            try:
                must_conditions = [
                    {
                        "key": "user_id",
                        "match": {"value": user_id}
                    },
                    {
                        "key": "source",
                        "match": {"value": f"{identifier}#chunk"}
                    }
                ]

                filter_conditions = {"must": must_conditions}

                results, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(**filter_conditions),
                    limit=1,
                    with_payload=True,
                    with_vectors=False
                )

                if results:
                    point = results[0]
                    return VectorDocument.from_payload(point.id, point.payload)

            except Exception as e:
                logger.warning(f"Method 2 (source pattern) failed: {e}")

            # Method 3: Check for source patterns like "filename#chunk_X"
            if source:
                try:
                    must_conditions = [
                        {
                            "key": "user_id",
                            "match": {"value": user_id}
                        }
                    ]

                    # Get all documents for this user and check source patterns manually
                    results, _ = self.client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=models.Filter(must=must_conditions),
                        limit=100,  # Get more results to check patterns
                        with_payload=True,
                        with_vectors=False
                    )

                    # Check each result for matching patterns
                    for point in results:
                        payload = point.payload
                        point_source = payload.get("source", "")
                        point_title = payload.get("title", "")

                        # Check if source starts with our file source and has chunk pattern
                        if point_source.startswith(f"{source}#chunk_"):
                            return VectorDocument.from_payload(point.id, point.payload)

                        # Check if title starts with our identifier and has part pattern
                        if point_title.startswith(f"{identifier} (Part"):
                            return VectorDocument.from_payload(point.id, point.payload)

                except Exception as e:
                    logger.warning(f"Method 3 (source pattern) failed: {e}")

            return None

        except Exception as e:
            logger.error(f"Error in chunked file check: {e}")
            return None

    def delete_user_file_vectors(self, user_id: str, file_id: str = None, title: str = None, source: str = None) -> bool:
        """
        Delete all vectors for a specific user file using file_id or title field.

        Args:
            user_id: User ID
            file_id: Unique file identifier (preferred)
            title: File title (fallback)
            source: Optional source for more specific matching

        Returns:
            bool: Success status
        """
        try:
            # Prefer file_id if provided, otherwise use title
            identifier = file_id if file_id else title
            if not identifier:
                logger.error("Either file_id or title must be provided")
                return False

            deleted_count = 0

            # Method 1: Delete using file_id or title field
            try:
                field_name = "file_id" if file_id else "title"
                must_conditions = [
                    {
                        "key": "user_id",
                        "match": {"value": user_id}
                    },
                    {
                        "key": field_name,
                        "match": {"value": identifier}
                    }
                ]

                if source:
                    must_conditions.append({
                        "key": "source",
                        "match": {"value": source}
                    })

                filter_conditions = {"must": must_conditions}

                # Count before deletion for logging
                count_result, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(**filter_conditions),
                    limit=1,
                    with_payload=False,
                    with_vectors=False
                )

                if count_result:
                    # Delete points with filter
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=models.FilterSelector(
                            filter=models.Filter(**filter_conditions)
                        )
                    )
                    deleted_count += len(count_result)
                    logger.info(f"Deleted {len(count_result)} vectors using {field_name} field")

            except Exception as e:
                logger.warning(f"Method 1 ({field_name}) failed: {e}")

            # Method 2: Delete chunked files using source pattern
            try:
                must_conditions = [
                    {
                        "key": "user_id",
                        "match": {"value": user_id}
                    },
                    {
                        "key": "source",
                        "match": {"value": f"{identifier}#chunk"}
                    }
                ]

                if source:
                    must_conditions.append({
                        "key": "source",
                        "match": {"value": source}
                    })

                filter_conditions = {"must": must_conditions}

                # Count before deletion for logging
                count_result, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(**filter_conditions),
                    limit=1,
                    with_payload=False,
                    with_vectors=False
                )

                if count_result:
                    # Delete points with filter
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=models.FilterSelector(
                            filter=models.Filter(**filter_conditions)
                        )
                    )
                    deleted_count += len(count_result)
                    logger.info(f"Deleted {len(count_result)} vectors using source pattern")

            except Exception as e:
                logger.warning(f"Method 2 (source pattern) failed: {e}")

            logger.info(f"Total deleted vectors for user {user_id}, identifier: {identifier} = {deleted_count}")
            return deleted_count > 0

        except Exception as e:
            logger.error(f"Failed to delete file vectors: {e}")
            return False

    def get_user_files(self, user_id: str, limit: int = 100) -> List[VectorDocument]:
        """
        Get all files for a specific user.

        Args:
            user_id: User ID
            limit: Maximum number of files to return

        Returns:
            List of VectorDocument for the user
        """
        try:
            filter_conditions = {
                "must": [
                    {
                        "key": "user_id",
                        "match": {"value": user_id}
                    }
                ]
            }

            # Use scroll to get all user files
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(**filter_conditions),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            user_files = []
            for point in results:
                doc = VectorDocument.from_payload(point.id, point.payload)
                user_files.append(doc)

            return user_files

        except Exception as e:
            logger.error(f"Failed to get user files: {e}")
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


def create_vector_document(text: str,
                          user_id: str,
                          title: str = None,
                          source: str = None,
                          file_id: str = None,
                          page: int = None) -> VectorDocument:
    """
    Create a VectorDocument with proper structure.

    Args:
        text: Main text content
        user_id: User ID for file isolation
        title: Document title
        source: Source file or origin
        file_id: Unique file identifier
        page: Page number if applicable

    Returns:
        VectorDocument instance
    """
    doc_id = generate_document_id()

    return VectorDocument(
        id=doc_id,
        text=text,
        user_id=user_id,
        title=title,
        source=source,
        file_id=file_id,
        page=page
    )