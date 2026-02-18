"""
Embedding service using sentence-transformers.

Provides text embedding generation for both document chunks
and user queries. Uses the all-MiniLM-L6-v2 model which offers
a good balance of speed and quality for semantic search.
"""

from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer


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
        Initialize the embedding model.

        Downloads the model on first use (approximately 80MB).
        Subsequent calls load from cache.

        Args:
            model_name: HuggingFace model name for sentence-transformers
        """
        # Mensaje en español para el desarrollador
        print(f"📥 Cargando modelo de embeddings: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.embedding_dimension = self.model.get_sentence_embedding_dimension()
        print(f"✅ Modelo cargado. Dimensión de embeddings: {self.embedding_dimension}")

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
        Generate embeddings for multiple texts in batch.

        Batch processing is significantly faster than encoding one at a time,
        especially for large document sets.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process simultaneously

        Returns:
            List of embedding vectors (each a list of floats)
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 10,  # Show progress for large batches
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """
        Get the embedding vector dimension.

        Returns:
            int: Number of dimensions in the embedding space (384 for MiniLM)
        """
        return self.embedding_dimension
