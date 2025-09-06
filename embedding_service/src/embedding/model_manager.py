import os
import asyncio
import logging
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingModelManager:
    def __init__(self, model_name: str = "sentence-transformers/distiluse-base-multilingual-cased-v1"):
        self.model_name = model_name
        self.model = None
        self._loaded = False
        self.cache_dir = os.getenv("MODEL_CACHE_DIR", "/app/models")
        
    async def load_model(self):
        """Load the sentence transformer model"""
        try:
            logger.info(f"Loading model: {self.model_name}")
            
            # Create cache directory if it doesn't exist
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Load model in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                lambda: SentenceTransformer(
                    self.model_name, 
                    cache_folder=self.cache_dir
                )
            )
            
            self._loaded = True
            logger.info(f"Model {self.model_name} loaded successfully")
            logger.info(f"Model dimension: {self.get_dimension()}")
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._loaded and self.model is not None
    
    async def encode_text(self, text: str) -> np.ndarray:
        """Encode a single text into embedding"""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        
        try:
            # Run encoding in thread to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode(text, convert_to_numpy=True)
            )
            return embedding
        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            raise
    
    async def encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Encode multiple texts into embeddings"""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        
        try:
            # Run batch encoding in thread to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts, convert_to_numpy=True)
            )
            return embeddings
        except Exception as e:
            logger.error(f"Failed to encode batch: {e}")
            raise
    
    def get_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        return self.model.get_sentence_embedding_dimension()
    
    def get_max_sequence_length(self) -> int:
        """Get the maximum sequence length"""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        return self.model.max_seq_length
