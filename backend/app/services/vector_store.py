"""
Vector store service wrapping ChromaDB.

Provides document storage and similarity search functionality
for the RAG pipeline. Uses ChromaDB in embedded (local) mode
with persistent storage for data durability.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


class VectorStore:
    """
    ChromaDB wrapper for vector similarity search.

    Stores document chunk embeddings with metadata and provides
    filtered similarity search for the RAG pipeline.

    The collection is isolated per-application to support
    multi-tenant scenarios in the future.

    Usage:
        store = VectorStore()
        store.add_document(chunk_id="abc", text="...", embedding=[...], metadata={...})
        results = store.query(query_embedding=[...], filter_dict={...}, n_results=5)
    """

    # Collection name for all study material embeddings
    COLLECTION_NAME = "study_materials"

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize ChromaDB client with persistent storage.

        Args:
            persist_directory: Directory for ChromaDB data persistence.
                             Defaults to VECTOR_DB_PATH from settings.
        """
        persist_path = persist_directory or settings.VECTOR_DB_PATH

        # Mensaje en español para el desarrollador
        print(f"📦 Inicializando ChromaDB en: {persist_path}")

        self.client = chromadb.PersistentClient(
            path=persist_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,  # Disable telemetry
            ),
        )

        # Get or create the main collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )

        print(
            f"✅ ChromaDB listo. Colección '{self.COLLECTION_NAME}' "
            f"con {self.collection.count()} documentos existentes."
        )

    def add_document(
        self,
        chunk_id: str,
        text: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Add a single document chunk to the vector store.

        Args:
            chunk_id: Unique identifier for the chunk (UUID as string)
            text: Text content of the chunk
            embedding: Pre-computed embedding vector
            metadata: Metadata dictionary for filtering (must contain
                      document_id, subject_id, user_id)

        Returns:
            str: The chunk_id used as the vector store ID
        """
        self.collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
        return chunk_id

    def add_documents_batch(
        self,
        chunk_ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """
        Add multiple document chunks in batch for better performance.

        Args:
            chunk_ids: List of unique chunk identifiers
            texts: List of text contents
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
        """
        if not chunk_ids:
            return

        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: List[float],
        filter_dict: Optional[Dict[str, Any]] = None,
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Perform similarity search in the vector store.

        Args:
            query_embedding: Query vector for similarity comparison
            filter_dict: Metadata filters (e.g., {"user_id": "...", "subject_id": "..."})
            n_results: Maximum number of results to return

        Returns:
            dict: ChromaDB query results with keys:
                - ids: List[List[str]] - matching chunk IDs
                - documents: List[List[str]] - matching text contents
                - metadatas: List[List[dict]] - matching metadata
                - distances: List[List[float]] - cosine distances (lower = more similar)
        """
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }

        if filter_dict:
            # Build ChromaDB where clause from filter dictionary
            where_clause = self._build_where_clause(filter_dict)
            if where_clause:
                query_params["where"] = where_clause

        return self.collection.query(**query_params)

    def delete_by_document(self, document_id: str) -> None:
        """
        Delete all chunks belonging to a specific document.

        Args:
            document_id: Document ID whose chunks should be removed
        """
        self.collection.delete(
            where={"document_id": document_id}
        )

    def delete_by_id(self, chunk_id: str) -> None:
        """
        Delete a specific chunk by its ID.

        Args:
            chunk_id: The chunk ID to delete
        """
        self.collection.delete(ids=[chunk_id])

    def get_collection_count(self) -> int:
        """
        Get the total number of documents in the collection.

        Returns:
            int: Total document count
        """
        return self.collection.count()

    def _build_where_clause(self, filter_dict: Dict[str, Any]) -> Optional[Dict]:
        """
        Build a ChromaDB where clause from a simple filter dictionary.

        Supports direct equality and $in operators.

        Args:
            filter_dict: Simple key-value filters

        Returns:
            dict: ChromaDB-compatible where clause, or None if empty
        """
        if not filter_dict:
            return None

        conditions = []
        for key, value in filter_dict.items():
            if isinstance(value, dict):
                # Already a ChromaDB operator (e.g., {"$in": [...]})
                conditions.append({key: value})
            else:
                conditions.append({key: str(value)})

        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return {"$and": conditions}

        return None
