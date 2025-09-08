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
            logger.debug("BM25 corpus already initialized, skipping")
            return

        try:
            logger.info("🔍 Initializing BM25 corpus from Qdrant documents...")

            # Fetch all documents from Qdrant to build corpus statistics
            documents = self._fetch_corpus_documents(qdrant_config)

            if documents:
                logger.info(f"📄 Fetched {len(documents)} documents from Qdrant")
                self.bm25_encoder.build_corpus_statistics(documents)
                self._corpus_initialized = True

                # Get corpus info for logging
                corpus_info = self.bm25_encoder.get_corpus_info()
                logger.info(f"✅ BM25 corpus initialized successfully:")
                logger.info(f"   📊 Documents: {corpus_info['corpus_size']}")
                logger.info(f"   📝 Vocabulary: {corpus_info['vocabulary_size']} terms")
                logger.info(f"   📏 Avg doc length: {corpus_info['average_doc_length']:.1f} tokens")
            else:
                logger.warning("❌ No documents found in Qdrant for BM25 corpus initialization")

        except Exception as e:
            logger.error(f"❌ Failed to initialize BM25 corpus: {e}")
            import traceback
            logger.debug(f"Stack trace: {traceback.format_exc()}")

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
                if 'content' in point.payload:  # Changed from 'text' to 'content'
                    documents.append(point.payload['content'])

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
            logger.debug(f"🔍 Getting embedding for: '{text}' from {self.embedding_service_url}")
            response = requests.post(
                f"{self.embedding_service_url}/embed",
                json={"text": text},
                timeout=30
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            logger.debug(f"✅ Got embedding with dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"❌ Failed to get embedding for '{text}': {e}")
            logger.error(f"   URL: {self.embedding_service_url}/embed")
            return None

    def hybrid_search(self,
                     query_text: str,
                     qdrant_config,
                     limit: int = 5,
                     score_threshold: float = 0.5,
                     subject: Optional[str] = None,
                     title: Optional[str] = None,
                     week: Optional[str] = None) -> Dict[str, Any]:
        """Perform true hybrid search using Qdrant's native RRF."""
        try:
            # Get dense embedding first
            dense_vector = self.get_embedding(query_text)
            if not dense_vector:
                logger.error("Failed to get dense embedding")
                return {"results": [], "total_found": 0, "search_type": "error"}

            # Initialize BM25 corpus if not done yet
            self._initialize_bm25_corpus(qdrant_config)

            # Check if BM25 is ready for hybrid search
            if self._corpus_initialized and self.bm25_encoder.corpus_stats_ready:
                # Get sparse vector (now that corpus is ready)
                sparse_vector = self.bm25_encoder.encode(query_text)

                if sparse_vector:  # If we got a valid sparse vector
                    logger.info(f"Performing hybrid search with {len(sparse_vector)} sparse terms")
                    return self._qdrant_hybrid_search(
                        dense_vector, sparse_vector, qdrant_config,
                        limit, score_threshold, subject, title, week
                    )
                else:
                    logger.warning("Sparse vector is empty, falling back to dense search")
            else:
                logger.warning("⚠️ BM25 not ready, falling back to dense search")

            # Fallback to dense search
            return self._dense_only_search(dense_vector, qdrant_config, limit, score_threshold, subject, title, week)

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return {"results": [], "total_found": 0, "search_type": "error"}

    def _qdrant_hybrid_search(self,
                             dense_vector: List[float],
                             sparse_vector: Dict[int, float],
                             qdrant_config,
                             limit: int,
                             score_threshold: float,
                             subject: Optional[str] = None,
                             title: Optional[str] = None,
                             week: Optional[str] = None) -> Dict[str, Any]:
        """Perform hybrid search using Qdrant's native RRF."""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, Prefetch, FusionQuery, Fusion

            # Build filter conditions
            filter_conditions = None
            must_conditions = []

            if subject:
                must_conditions.append(
                    FieldCondition(
                        key="subject",
                        match=MatchValue(value=subject)
                    )
                )

            if title:
                must_conditions.append(
                    FieldCondition(
                        key="title",
                        match=MatchValue(value=title)
                    )
                )

            if week:
                must_conditions.append(
                    FieldCondition(
                        key="week",
                        match=MatchValue(value=week)
                    )
                )

            if must_conditions:
                filter_conditions = Filter(must=must_conditions)

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
            return self._dense_only_search(dense_vector, qdrant_config, limit, score_threshold, subject, title, week)

    def _dense_only_search(self,
                          dense_vector: List[float],
                          qdrant_config,
                          limit: int,
                          score_threshold: float,
                          subject: Optional[str] = None,
                          title: Optional[str] = None,
                          week: Optional[str] = None) -> Dict[str, Any]:
        """Fallback to dense search only."""
        try:
            filter_conditions = None
            if any([subject, title, week]):
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                must_conditions = []

                if subject:
                    must_conditions.append(
                        FieldCondition(
                            key="subject",
                            match=MatchValue(value=subject)
                        )
                    )

                if title:
                    must_conditions.append(
                        FieldCondition(
                            key="title",
                            match=MatchValue(value=title)
                        )
                    )

                if week:
                    must_conditions.append(
                        FieldCondition(
                            key="week",
                            match=MatchValue(value=week)
                        )
                    )

                filter_conditions = Filter(must=must_conditions)

            results = qdrant_config.search_similar(
                query_vector=dense_vector,
                limit=limit,
                score_threshold=score_threshold,
                filter_conditions=filter_conditions
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