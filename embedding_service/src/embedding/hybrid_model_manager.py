import os
import asyncio
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from .fastembed_bm25 import FastEmbedBM25

logger = logging.getLogger(__name__)


class HybridModelManager:
    """Manager for both dense and sparse embedding models."""
    
    def __init__(self, 
                 dense_model_name: str = "sentence-transformers/distiluse-base-multilingual-cased-v1",
                 sparse_model_name: str = "Qdrant/bm25"):
        self.dense_model_name = dense_model_name
        self.sparse_model_name = sparse_model_name
        
        # Dense model (sentence-transformers)
        self.dense_model = None
        self._dense_loaded = False
        
        # Sparse model (FastEmbed BM25)
        self.sparse_model = FastEmbedBM25(sparse_model_name)
        
        self.cache_dir = os.getenv("MODEL_CACHE_DIR", "/app/models")
        
    async def load_models(self):
        """Load both dense and sparse models."""
        try:
            logger.info("Loading hybrid models (dense + sparse)...")
            
            # Load dense model
            await self._load_dense_model()
            
            # Load sparse model (in thread to avoid blocking)
            await self._load_sparse_model()
            
            logger.info("✅ Hybrid models loaded successfully")
            logger.info(f"Dense model: {self.dense_model_name} (dim: {self.get_dense_dimension()})")
            logger.info(f"Sparse model: {self.sparse_model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load hybrid models: {e}")
            raise
    
    async def _load_dense_model(self):
        """Load the dense sentence transformer model."""
        try:
            logger.info(f"Loading dense model: {self.dense_model_name}")
            
            # Create cache directory if it doesn't exist
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Load model in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.dense_model = await loop.run_in_executor(
                None, 
                lambda: SentenceTransformer(
                    self.dense_model_name, 
                    cache_folder=self.cache_dir
                )
            )
            
            self._dense_loaded = True
            logger.info(f"✅ Dense model loaded: {self.dense_model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load dense model: {e}")
            raise
    
    async def _load_sparse_model(self):
        """Load the sparse BM25 model."""
        try:
            logger.info(f"Loading sparse model: {self.sparse_model_name}")
            
            # Load BM25 model in thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.sparse_model._load_model)
            
            logger.info(f"✅ Sparse model loaded: {self.sparse_model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load sparse model: {e}")
            raise
    
    def is_loaded(self) -> bool:
        """Check if both models are loaded."""
        return self._dense_loaded and self.sparse_model.is_loaded()
    
    def is_dense_loaded(self) -> bool:
        """Check if dense model is loaded."""
        return self._dense_loaded and self.dense_model is not None
    
    def is_sparse_loaded(self) -> bool:
        """Check if sparse model is loaded."""
        return self.sparse_model.is_loaded()
    
    async def encode_hybrid(self, text: str) -> Tuple[np.ndarray, Dict[int, float]]:
        """
        Encode text to both dense and sparse vectors.
        
        Returns:
            Tuple[np.ndarray, Dict[int, float]]: (dense_vector, sparse_vector)
        """
        if not self.is_loaded():
            raise RuntimeError("Models not loaded")
        
        try:
            # Encode dense vector (async)
            dense_task = self.encode_dense(text)
            
            # Encode sparse vector (in thread)
            loop = asyncio.get_event_loop()
            sparse_task = loop.run_in_executor(None, self.sparse_model.encode, text)
            
            # Wait for both to complete
            dense_vector, sparse_vector = await asyncio.gather(dense_task, sparse_task)
            
            return dense_vector, sparse_vector
            
        except Exception as e:
            logger.error(f"Failed to encode hybrid: {e}")
            raise
    
    async def encode_dense(self, text: str) -> np.ndarray:
        """Encode text to dense vector only."""
        if not self.is_dense_loaded():
            raise RuntimeError("Dense model not loaded")
        
        try:
            # Run encoding in thread to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.dense_model.encode(text, convert_to_numpy=True)
            )
            return embedding
        except Exception as e:
            logger.error(f"Failed to encode dense: {e}")
            raise
    
    async def encode_sparse(self, text: str) -> Dict[int, float]:
        """Encode text to sparse vector only."""
        if not self.is_sparse_loaded():
            raise RuntimeError("Sparse model not loaded")
        
        try:
            # Run encoding in thread to avoid blocking
            loop = asyncio.get_event_loop()
            sparse_vector = await loop.run_in_executor(None, self.sparse_model.encode, text)
            return sparse_vector
        except Exception as e:
            logger.error(f"Failed to encode sparse: {e}")
            raise
    
    async def encode_hybrid_batch(self, texts: List[str]) -> Tuple[List[np.ndarray], List[Dict[int, float]]]:
        """
        Encode multiple texts to both dense and sparse vectors.
        
        Returns:
            Tuple[List[np.ndarray], List[Dict[int, float]]]: (dense_vectors, sparse_vectors)
        """
        if not self.is_loaded():
            raise RuntimeError("Models not loaded")
        
        try:
            # Encode dense vectors (async)
            dense_task = self.encode_dense_batch(texts)
            
            # Encode sparse vectors (in thread)
            loop = asyncio.get_event_loop()
            sparse_task = loop.run_in_executor(None, self.sparse_model.encode_batch, texts)
            
            # Wait for both to complete
            dense_vectors, sparse_vectors = await asyncio.gather(dense_task, sparse_task)
            
            return dense_vectors, sparse_vectors
            
        except Exception as e:
            logger.error(f"Failed to encode hybrid batch: {e}")
            raise
    
    async def encode_dense_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Encode multiple texts to dense vectors only."""
        if not self.is_dense_loaded():
            raise RuntimeError("Dense model not loaded")
        
        try:
            # Run batch encoding in thread to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.dense_model.encode(texts, convert_to_numpy=True)
            )
            return embeddings
        except Exception as e:
            logger.error(f"Failed to encode dense batch: {e}")
            raise
    
    def get_dense_dimension(self) -> int:
        """Get the dimension of dense embeddings."""
        if not self.is_dense_loaded():
            raise RuntimeError("Dense model not loaded")
        return self.dense_model.get_sentence_embedding_dimension()
    
    def get_max_sequence_length(self) -> int:
        """Get the maximum sequence length."""
        if not self.is_dense_loaded():
            raise RuntimeError("Dense model not loaded")
        return self.dense_model.max_seq_length
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about both models."""
        return {
            "dense_model": {
                "name": self.dense_model_name,
                "loaded": self.is_dense_loaded(),
                "dimension": self.get_dense_dimension() if self.is_dense_loaded() else None
            },
            "sparse_model": {
                "name": self.sparse_model_name,
                "loaded": self.is_sparse_loaded(),
                "type": "fastembed_bm25"
            },
            "hybrid_ready": self.is_loaded()
        }
