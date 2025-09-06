import os
import requests
from typing import List, Dict, Any, Optional
from src.services.bm25_encoder import BM25Encoder
from src.utils.logger import Logger

logger = Logger(__name__)


class VectorServices:
    def __init__(self, database_service_url: str, embedding_service_url: str = None):
        self.database_service_url = database_service_url
        self.embedding_service_url = embedding_service_url or os.getenv("EMBEDDING_SERVICE_URL", "http://embedding:8005")
        self.bm25_encoder = BM25Encoder()
        self._corpus_initialized = False

    def _initialize_bm25_corpus(self, qdrant_config):
        """Initialize BM25 with corpus from Qdrant - no training, just statistics."""
        if self._corpus_initialized:
            return

        try:
            # Fetch all documents from Qdrant to build corpus statistics
            documents = self._fetch_corpus_documents(qdrant_config)
            if documents:
                self.bm25_encoder.build_corpus_statistics(documents)
                self._corpus_initialized = True
                logger.info(f"BM25 corpus initialized with {len(documents)} documents")
            else:
                logger.warning("No documents found in Qdrant for BM25 corpus initialization")
        except Exception as e:
            logger.error(f"Failed to initialize BM25 corpus: {e}")

    def _fetch_corpus_documents(self, qdrant_config) -> List[str]:
        """Fetch all document texts from Qdrant collection."""
        try:
            # Use Qdrant scroll to get all documents
            scroll_result = qdrant_config.client.scroll(
                collection_name=qdrant_config.collection_name,
                limit=1000,  # Adjust based on corpus size
                with_payload=True,
                with_vectors=False
            )

            documents = []
            for point in scroll_result[0]:  # scroll returns (points, next_page_offset)
                if 'text' in point.payload:
                    documents.append(point.payload['text'])

            return documents
        except Exception as e:
            logger.error(f"Failed to fetch corpus documents: {e}")
            return []

    def search_vectors(self, query_vector: List[float], limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents using dense vector."""
        try:
            response = requests.post(
                f"{self.database_service_url}/search",
                json={
                    "query_vector": query_vector,
                    "limit": limit,
                    "score_threshold": score_threshold
                }
            )
            response.raise_for_status()
            return response.json()["results"]
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from embedding service."""
        try:
            response = requests.post(
                f"{self.embedding_service_url}/embed",
                json={"text": text},
                timeout=30
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    def hybrid_search(self,
                     query_text: str,
                     qdrant_config,
                     limit: int = 5,
                     score_threshold: float = 0.5,
                     user_id: Optional[str] = None) -> Dict[str, Any]:
        """Perform true hybrid search using Qdrant's native RRF."""
        try:
            # Initialize BM25 corpus if not done yet
            self._initialize_bm25_corpus(qdrant_config)

            # Get dense embedding
            dense_vector = self.get_embedding(query_text)
            if not dense_vector:
                logger.error("Failed to get dense embedding")
                return {"results": [], "total_found": 0, "search_type": "error"}

            # Get sparse vector
            sparse_vector = self.bm25_encoder.encode(query_text)

            # Perform true hybrid search using Qdrant's native capabilities
            if sparse_vector and self._corpus_initialized:
                return self._qdrant_hybrid_search(
                    dense_vector, sparse_vector, qdrant_config,
                    limit, score_threshold, user_id
                )
            else:
                logger.warning("BM25 not ready, falling back to dense search")
                return self._dense_only_search(dense_vector, qdrant_config, limit, score_threshold, user_id)

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return {"results": [], "total_found": 0, "search_type": "error"}

    def _qdrant_hybrid_search(self,
                             dense_vector: List[float],
                             sparse_vector: Dict[int, float],
                             qdrant_config,
                             limit: int,
                             score_threshold: float,
                             user_id: Optional[str]) -> Dict[str, Any]:
        """Perform hybrid search using Qdrant's native RRF."""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, Prefetch, FusionQuery, Fusion

            # Build filter conditions
            filter_conditions = None
            if user_id:
                filter_conditions = Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                )

            # Convert sparse vector to Qdrant format
            sparse_indices = list(sparse_vector.keys())
            sparse_values = list(sparse_vector.values())

            # Use Qdrant's Query API with RRF
            search_result = qdrant_config.client.query_points(
                collection_name=qdrant_config.collection_name,
                prefetch=[
                    Prefetch(
                        query={"indices": sparse_indices, "values": sparse_values},
                        using="bm25_sparse_vector",
                        limit=limit * 2,  # Get more candidates for RRF
                        filter=filter_conditions
                    ),
                    Prefetch(
                        query=dense_vector,
                        using="dense_vector",
                        limit=limit * 2,  # Get more candidates for RRF
                        filter=filter_conditions
                    )
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            # Format results
            results = []
            for point in search_result.points:
                if point.score >= score_threshold:
                    from src.database.qdrant_client import VectorDocument
                    doc = VectorDocument.from_payload(point.id, point.payload)
                    results.append({
                        "id": point.id,
                        "score": point.score,
                        "payload": doc.to_payload()
                    })

            return {
                "results": results,
                "total_found": len(results),
                "search_type": "hybrid"
            }

        except Exception as e:
            logger.error(f"Qdrant hybrid search failed: {e}")
            # Fallback to dense search
            return self._dense_only_search(dense_vector, qdrant_config, limit, score_threshold, user_id)

    def _dense_only_search(self,
                          dense_vector: List[float],
                          qdrant_config,
                          limit: int,
                          score_threshold: float,
                          user_id: Optional[str]) -> Dict[str, Any]:
        """Fallback to dense search only."""
        try:
            filter_conditions = {}
            if user_id:
                filter_conditions = {
                    "must": [
                        {
                            "key": "user_id",
                            "match": {"value": user_id}
                        }
                    ]
                }

            results = qdrant_config.search_similar(
                query_vector=dense_vector,
                limit=limit,
                score_threshold=score_threshold,
                filter_conditions=filter_conditions if user_id else None
            )

            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result["id"],
                    "score": result["score"],
                    "payload": result["document"].to_payload()
                })

            return {
                "results": formatted_results,
                "total_found": len(formatted_results),
                "search_type": "dense_only"
            }

        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            return {"results": [], "total_found": 0, "search_type": "error"}