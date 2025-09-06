import re
import math
from collections import Counter
from typing import Dict, List, Optional
from src.utils.logger import Logger

logger = Logger(__name__)


class BM25Encoder:
    """BM25 encoder for sparse vector generation - statistical approach, no ML training."""

    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.vocabulary = {}
        self.doc_freqs = {}
        self.idf = {}
        self.corpus_size = 0
        self.avgdl = 0
        self.corpus_stats_ready = False

    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def build_corpus_statistics(self, documents: List[str]) -> None:
        """Build BM25 statistics from corpus - no training, just statistics calculation."""
        try:
            self.corpus_size = len(documents)
            doc_freqs = {}
            total_doc_length = 0

            for document in documents:
                tokens = self.tokenize(document)
                total_doc_length += len(tokens)

                # Count unique terms in this document for document frequency
                unique_tokens = set(tokens)
                for token in unique_tokens:
                    doc_freqs[token] = doc_freqs.get(token, 0) + 1

            self.doc_freqs = doc_freqs
            self.avgdl = total_doc_length / self.corpus_size if self.corpus_size > 0 else 0

            # Calculate IDF for each term
            for token, freq in doc_freqs.items():
                # BM25 IDF formula: log((N - df + 0.5) / (df + 0.5))
                self.idf[token] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5))

                # Build vocabulary mapping
                if token not in self.vocabulary:
                    self.vocabulary[token] = len(self.vocabulary)

            self.corpus_stats_ready = True
            logger.info(f"BM25 corpus statistics built: {self.corpus_size} documents, {len(self.vocabulary)} unique terms")

        except Exception as e:
            logger.error(f"Failed to build BM25 corpus statistics: {e}")
            raise
    
    def encode(self, text: str, doc_length: Optional[int] = None) -> Dict[int, float]:
        """Encode text to BM25 sparse vector."""
        if not self.corpus_stats_ready:
            logger.warning("BM25 corpus statistics not ready, returning empty sparse vector")
            return {}

        try:
            tokens = self.tokenize(text)
            token_counts = Counter(tokens)
            sparse_vector = {}

            # Use provided doc_length or calculate from tokens
            doc_len = doc_length if doc_length is not None else len(tokens)

            for token, tf in token_counts.items():
                if token in self.idf and token in self.vocabulary:
                    token_idx = self.vocabulary[token]
                    idf = self.idf[token]

                    # BM25 formula: IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * |D| / avgdl))
                    numerator = idf * tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                    score = numerator / denominator

                    if score > 0:
                        sparse_vector[token_idx] = score

            return sparse_vector

        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            return {}

    def get_corpus_info(self) -> Dict[str, any]:
        """Get corpus statistics info."""
        return {
            "corpus_size": self.corpus_size,
            "vocabulary_size": len(self.vocabulary),
            "average_doc_length": self.avgdl,
            "stats_ready": self.corpus_stats_ready
        }
