"""
Embedding service using sentence-transformers.

Provides text embedding generation for both document chunks
and user queries. Uses the all-MiniLM-L6-v2 model which offers
a good balance of speed and quality for semantic search.
"""

import threading
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer


# Thread-safe singleton for the embedding model
_model_lock = threading.Lock()
_shared_model: SentenceTransformer = None
_shared_dimension: int = None


def _get_shared_model(model_name: str = "all-MiniLM-L6-v2"):
    """
    Get or create the shared SentenceTransformer model (singleton).
    
    This prevents multiple background threads from loading separate
    copies of the model, which causes 'meta tensor' errors when
    torch tries to allocate memory concurrently.
    """
    global _shared_model, _shared_dimension
    if _shared_model is None:
        with _model_lock:
            # Double-check inside lock
            if _shared_model is None:
                print(f"📥 Cargando modelo de embeddings (singleton): {model_name}...")
                _shared_model = SentenceTransformer(model_name)
                _shared_dimension = _shared_model.get_sentence_embedding_dimension()
                print(f"✅ Modelo cargado. Dimensión: {_shared_dimension}")
    return _shared_model, _shared_dimension


class EmbedderService:
    """
    Text embedding service using sentence-transformers.

    The all-MiniLM-L6-v2 model generates 384-dimensional embeddings
    optimized for semantic similarity tasks. It's small enough to run
    efficiently on CPU while providing good search quality.

    Usage:
        embedder = EmbedderService()
        embedding = embedder.embed_query("What is machine learning?")
        embeddings = embedder.embed_batch(["text1", "text2", "text3"])
    """

    # Model name constant for consistency
    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = MODEL_NAME):
        """
        Initialize the embedding service using a shared singleton model.

        The model is loaded once and shared across all instances/threads
        to prevent concurrent torch model loading crashes (meta tensor errors).

        Args:
            model_name: HuggingFace model name for sentence-transformers
        """
        self.model, self.embedding_dimension = _get_shared_model(model_name)

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query text.

        Args:
            text: Query text to embed

        Returns:
            List of floats representing the embedding vector
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch (thread-safe).

        Uses a lock to serialize concurrent encoding calls, preventing
        torch from crashing when multiple background threads try to
        use the model simultaneously.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process simultaneously

        Returns:
            List of embedding vectors (each a list of floats)
        """
        if not texts:
            return []

        with _model_lock:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 10,
            )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """
        Get the embedding vector dimension.

        Returns:
            int: Number of dimensions in the embedding space (384 for MiniLM)
        """
        return self.embedding_dimension
