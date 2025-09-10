from typing import Dict, List, Optional, Any
from fastembed import SparseTextEmbedding
import logging

logger = logging.getLogger(__name__)


class FastEmbedBM25:
    """FastEmbed BM25 encoder for embedding_service - centralized sparse embedding."""

    def __init__(self, model_name: str = "Qdrant/bm25"):
        self.model_name = model_name
        self.model = None
        self._model_loaded = False
        
    def _load_model(self):
        """Load the FastEmbed BM25 model."""
        if self._model_loaded:
            return
            
        try:
            logger.info(f"Loading FastEmbed BM25 model: {self.model_name}")
            self.model = SparseTextEmbedding(model_name=self.model_name)
            self._model_loaded = True
            logger.info(f"FastEmbed BM25 model loaded successfully: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load FastEmbed BM25 model: {e}")
            raise

    def is_loaded(self) -> bool:
        """Check if BM25 model is loaded."""
        return self._model_loaded

    def encode(self, text: str) -> Dict[int, float]:
        """
        Encode text to BM25 sparse vector using FastEmbed.
        
        Args:
            text: Input text to encode
            
        Returns:
            Dict[int, float]: Sparse vector as {index: value} mapping
        """
        if not self._model_loaded:
            logger.info("FastEmbed BM25 model not loaded, loading now...")
            self._load_model()

        try:
            logger.debug(f"🔍 Encoding text with FastEmbed BM25: '{text}'")
            
            # Get sparse embedding from FastEmbed
            embeddings = list(self.model.embed([text]))
            
            if not embeddings:
                logger.warning("FastEmbed returned empty embeddings")
                return {}
                
            embedding = embeddings[0]
            
            # Convert FastEmbed sparse format to our format
            sparse_vector = {}
            if hasattr(embedding, 'indices') and hasattr(embedding, 'values'):
                # FastEmbed returns SparseEmbedding with indices and values
                for idx, value in zip(embedding.indices, embedding.values):
                    if value > 0:  # Only include positive values
                        sparse_vector[int(idx)] = float(value)
            else:
                logger.warning("Unexpected FastEmbed embedding format")
                return {}
            
            logger.debug(f"📊 FastEmbed sparse vector: {len(sparse_vector)} terms")
            return sparse_vector

        except Exception as e:
            logger.error(f"Failed to encode text with FastEmbed: {e}")
            return {}

    def encode_batch(self, texts: List[str]) -> List[Dict[int, float]]:
        """
        Encode multiple texts to BM25 sparse vectors.
        
        Args:
            texts: List of input texts
            
        Returns:
            List[Dict[int, float]]: List of sparse vectors
        """
        if not self._model_loaded:
            logger.info("FastEmbed BM25 model not loaded, loading now...")
            self._load_model()

        try:
            logger.debug(f"🔍 Encoding {len(texts)} texts with FastEmbed BM25")
            
            # Get sparse embeddings from FastEmbed
            embeddings = list(self.model.embed(texts))
            
            if not embeddings:
                logger.warning("FastEmbed returned empty embeddings")
                return [{}] * len(texts)
            
            results = []
            for embedding in embeddings:
                sparse_vector = {}
                if hasattr(embedding, 'indices') and hasattr(embedding, 'values'):
                    for idx, value in zip(embedding.indices, embedding.values):
                        if value > 0:
                            sparse_vector[int(idx)] = float(value)
                results.append(sparse_vector)
            
            logger.debug(f"📊 FastEmbed batch result: {len(results)} sparse vectors")
            return results

        except Exception as e:
            logger.error(f"Failed to encode batch with FastEmbed: {e}")
            return [{}] * len(texts)

    def get_model_info(self) -> Dict[str, Any]:
        """Get BM25 model information."""
        return {
            "model_name": self.model_name,
            "model_loaded": self._model_loaded,
            "type": "fastembed_bm25"
        }
