import os
import requests
from src.utils.logger import Logger
from typing import List, Union

logger = Logger(__name__)

class KnowledgeBase:
    """
    Enhanced Knowledge Base using hybrid search from database service.
    Flow: query → RAG → enhance context → prompt → agent
    """

    def __init__(self,
                 database_service_url: str = None,
                 embedding_service_url: str = None):
        """
        Initialize KnowledgeBase with service URLs.

        Args:
            database_service_url: URL of the database service (default from env)
            embedding_service_url: URL of the embedding service (default from env)
        """
        self.database_service_url = database_service_url or os.getenv("DATABASE_URL", "http://vectordb:8002")
        self.embedding_service_url = embedding_service_url or os.getenv("EMBEDDING_SERVICE_URL", "http://embedding:8005")
        logger.info(f"✅ KnowledgeBase initialized:")
        logger.info(f"   📊 Database service: {self.database_service_url}")
        logger.info(f"   🧠 Embedding service: {self.embedding_service_url}")

    def search(self,
               query: str,
               limit: int = 8,
               score_threshold: float = 0.5,
               user_id: str = None) -> dict:
        """
        Search knowledge base using new hybrid flow:
        1. Get vectors from embedding_service/embed-hybrid
        2. Search with vectors via database_service/hybrid-search-with-vectors

        Args:
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum relevance score
            user_id: Optional user ID for filtering

        Returns:
            dict: Search results with metadata
        """
        try:
            logger.info(f"🔍 [KnowledgeBase] New hybrid search query: '{query}' (limit={limit}, threshold={score_threshold})")

            # Step 1: Get hybrid vectors from embedding service
            embed_response = self._get_hybrid_vectors(query)
            if not embed_response:
                return self._create_error_response("Failed to get embeddings")

            # Step 2: Search with vectors
            search_response = self._search_with_vectors(
                dense_vector=embed_response["dense_vector"],
                sparse_vector=embed_response["sparse_vector"],
                limit=limit,
                score_threshold=score_threshold,
                user_id=user_id
            )

            return search_response

        except Exception as e:
            logger.error(f"❌ [KnowledgeBase] Search failed: {str(e)}")
            return self._create_error_response(str(e))

    def _get_hybrid_vectors(self, query: str) -> dict:
        """Get both dense and sparse vectors from embedding service."""
        try:
            logger.info(f"🧠 [KnowledgeBase] Getting hybrid vectors for: '{query}'")

            response = requests.post(
                f"{self.embedding_service_url}/embed-hybrid",
                json={"text": query},
                headers={"Content-Type": "application/json"},
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                sparse_terms = result.get("sparse_terms", 0)
                dense_dim = result.get("dense_dimension", 0)

                logger.info(f"✅ [KnowledgeBase] Got hybrid vectors: {dense_dim}D dense, {sparse_terms} sparse terms")
                return result
            else:
                logger.error(f"❌ [KnowledgeBase] Embedding service error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ [KnowledgeBase] Failed to get hybrid vectors: {str(e)}")
            return None

    def _search_with_vectors(self,
                           dense_vector: list,
                           sparse_vector: dict,
                           limit: int,
                           score_threshold: float,
                           user_id: str = None) -> dict:
        """Search using pre-computed vectors."""
        try:
            # Prepare search payload
            payload = {
                "dense_vector": dense_vector,
                "sparse_vector": sparse_vector,
                "limit": limit,
                "score_threshold": score_threshold
            }

            # Add user_id filter if provided (note: current schema doesn't support this yet)
            if user_id:
                logger.warning(f"⚠️ [KnowledgeBase] User filtering not yet supported in new endpoint: {user_id}")

            # Call new database service endpoint
            response = requests.post(
                f"{self.database_service_url}/hybrid-search-with-vectors",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                search_type = result.get("search_type", "unknown")
                total_found = result.get("total_found", 0)
                results = result.get("results", [])

                logger.info(f"✅ [KnowledgeBase] Vector search ({search_type}) found {total_found} results")

                return {
                    "success": True,
                    "results": results,
                    "total_found": total_found,
                    "search_type": search_type
                }
            else:
                logger.error(f"❌ [KnowledgeBase] Database service error: {response.status_code}")
                return self._create_error_response(f"Database service returned {response.status_code}")

        except Exception as e:
            logger.error(f"❌ [KnowledgeBase] Vector search failed: {str(e)}")
            return self._create_error_response(str(e))

    def _create_error_response(self, error_message: str) -> dict:
        """Create standardized error response."""
        return {
            "success": False,
            "results": [],
            "total_found": 0,
            "search_type": "error",
            "error": error_message
        }

    def enhance_context(self,
                       query: str,
                       search_results: dict,
                       max_context_length: int = 2000) -> dict:
        """
        Enhance context from search results for prompt engineering.

        Args:
            query: Original search query
            search_results: Results from search() method
            max_context_length: Maximum context length in characters

        Returns:
            dict: Enhanced context with metadata
        """
        try:
            if not search_results.get("success", False):
                logger.warning(f"⚠️ [KnowledgeBase] No valid search results to enhance context")
                return {
                    "enhanced_context": "",
                    "source_count": 0,
                    "context_length": 0,
                    "search_type": search_results.get("search_type", "error"),
                    "truncated": False
                }

            results = search_results.get("results", [])
            if not results:
                logger.warning(f"⚠️ [KnowledgeBase] Empty search results for context enhancement")
                return {
                    "enhanced_context": "",
                    "source_count": 0,
                    "context_length": 0,
                    "search_type": search_results.get("search_type", "unknown"),
                    "truncated": False
                }

            # Build enhanced context
            context_parts = []
            context_parts.append(f"📋 **Relevant Information for: '{query}'**\n")

            for i, result in enumerate(results, 1):
                score = result.get("score", 0)
                payload = result.get("payload", {})

                # Extract content from payload
                content = payload.get("text", payload.get("content", ""))
                title = payload.get("title", f"Document {i}")

                if content:
                    context_parts.append(f"\n🔹 **Source {i}** (Score: {score:.3f}) - {title}")
                    context_parts.append(f"{content}")

            # Join and check length
            full_context = "\n".join(context_parts)
            context_length = len(full_context)
            truncated = False

            # Truncate if necessary
            if context_length > max_context_length:
                full_context = full_context[:max_context_length] + "\n\n... [Context truncated due to length limit]"
                truncated = True
                context_length = len(full_context)
                logger.info(f"📏 [KnowledgeBase] Context truncated to {max_context_length} characters")

            logger.info(f"✅ [KnowledgeBase] Enhanced context: {len(results)} sources, {context_length} chars")

            return {
                "enhanced_context": full_context,
                "source_count": len(results),
                "context_length": context_length,
                "search_type": search_results.get("search_type", "unknown"),
                "truncated": truncated,
                "sources": [
                    {
                        "title": result.get("payload", {}).get("title", f"Source {i+1}"),
                        "score": result.get("score", 0),
                        "id": result.get("id", f"doc_{i+1}")
                    }
                    for i, result in enumerate(results)
                ]
            }

        except Exception as e:
            logger.error(f"❌ [KnowledgeBase] Error enhancing context: {str(e)}")
            return {
                "enhanced_context": f"Error enhancing context: {str(e)}",
                "source_count": 0,
                "context_length": 0,
                "search_type": "error",
                "truncated": False
            }

    def search_and_enhance(self,
                          query: str,
                          limit: int = 5,
                          score_threshold: float = 0.3,
                          max_context_length: int = 5000,
                          user_id: str = None) -> dict:
        """
        Complete RAG pipeline: search + enhance context in one call.

        Args:
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum relevance score
            max_context_length: Maximum context length in characters
            user_id: Optional user ID for filtering

        Returns:
            dict: Complete RAG result with enhanced context
        """
        try:
            logger.info(f"[KnowledgeBase] Starting RAG pipeline for: '{query}'")

            # Step 1: Search knowledge base
            search_results = self.search(
                query=query,
                limit=limit,
                score_threshold=score_threshold,
                user_id=user_id
            )

            # Step 2: Enhance context
            enhanced_context = self.enhance_context(
                query=query,
                search_results=search_results,
                max_context_length=max_context_length
            )

            # Step 3: Combine results
            rag_result = {
                "query": query,
                "search_success": search_results.get("success", False),
                "search_type": search_results.get("search_type", "unknown"),
                "total_found": search_results.get("total_found", 0),
                "enhanced_context": enhanced_context.get("enhanced_context", ""),
                "source_count": enhanced_context.get("source_count", 0),
                "context_length": enhanced_context.get("context_length", 0),
                "truncated": enhanced_context.get("truncated", False),
                "sources": enhanced_context.get("sources", []),
                "raw_results": search_results.get("results", [])
            }

            if search_results.get("success", False) and enhanced_context.get("source_count", 0) > 0:
                logger.info(f"✅ [KnowledgeBase] RAG pipeline completed: {enhanced_context.get('source_count')} sources, {enhanced_context.get('context_length')} chars")
            else:
                logger.warning(f"⚠️ [KnowledgeBase] RAG pipeline completed with no relevant results")

            return rag_result

        except Exception as e:
            logger.error(f"❌ [KnowledgeBase] RAG pipeline error: {str(e)}")
            return {
                "query": query,
                "search_success": False,
                "search_type": "error",
                "total_found": 0,
                "enhanced_context": f"RAG pipeline error: {str(e)}",
                "source_count": 0,
                "context_length": 0,
                "truncated": False,
                "sources": [],
                "raw_results": [],
                "error": str(e)
            }

    def format_for_prompt(self, rag_result: dict, include_metadata: bool = True) -> str:
        """
        Format RAG result for prompt engineering.

        Args:
            rag_result: Result from search_and_enhance()
            include_metadata: Whether to include search metadata

        Returns:
            str: Formatted context for prompt
        """
        try:
            if not rag_result.get("search_success", False):
                return "No relevant information found in knowledge base."

            enhanced_context = rag_result.get("enhanced_context", "")
            if not enhanced_context:
                return "No relevant information found in knowledge base."

            # Build formatted prompt context
            prompt_parts = []

            if include_metadata:
                search_type = rag_result.get("search_type", "unknown")
                source_count = rag_result.get("source_count", 0)

                prompt_parts.append(f"📚 **Knowledge Base Context** ({search_type} search, {source_count} sources)")
                prompt_parts.append("=" * 60)

            prompt_parts.append(enhanced_context)

            if include_metadata and rag_result.get("truncated", False):
                prompt_parts.append("\n⚠️ *Note: Context was truncated due to length limits*")

            formatted_context = "\n".join(prompt_parts)

            logger.info(f"📝 [KnowledgeBase] Formatted context for prompt: {len(formatted_context)} characters")

            return formatted_context

        except Exception as e:
            logger.error(f"❌ [KnowledgeBase] Error formatting for prompt: {str(e)}")
            return f"Error formatting knowledge base context: {str(e)}"

    def get_health_status(self) -> dict:
        """
        Check health status of database service.

        Returns:
            dict: Health status information
        """
        try:
            response = requests.get(
                f"{self.database_service_url}/health",
                timeout=5
            )

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "database_service": "available",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    "status": "unhealthy",
                    "database_service": "error",
                    "error": f"HTTP {response.status_code}"
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "database_service": "unavailable",
                "error": str(e)
            }


# Example usage for agent integration
"""
Usage Example in Agent Flow:

# 1. Initialize KnowledgeBase
kb = KnowledgeBase()

# 2. RAG Pipeline: query → search → enhance context
user_query = "Hướng dẫn dọn dẹp phòng khách sạn"
rag_result = kb.search_and_enhance(
    query=user_query,
    limit=5,
    score_threshold=0.5,
    max_context_length=2000,
    user_id="user123"  # Optional user filtering
)

# 3. Format for prompt engineering
knowledge_context = kb.format_for_prompt(rag_result, include_metadata=True)

# 4. Build enhanced prompt
enhanced_prompt = f'''
Bạn là một AI assistant chuyên nghiệp. Hãy trả lời câu hỏi dựa trên thông tin từ knowledge base.

{knowledge_context}

Câu hỏi của người dùng: {user_query}

Hãy trả lời một cách chính xác và hữu ích dựa trên thông tin trên.
'''

# 5. Send to agent/LLM
# agent_response = llm.invoke(enhanced_prompt)

# Alternative: Step-by-step approach
# Step 1: Search only
search_results = kb.search(query=user_query, limit=3)

# Step 2: Enhance context
enhanced_context = kb.enhance_context(
    query=user_query,
    search_results=search_results,
    max_context_length=1500
)

# Step 3: Custom formatting
custom_context = f"Relevant info: {enhanced_context['enhanced_context']}"
"""
    