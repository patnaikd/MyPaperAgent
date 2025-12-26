"""ChromaDB vector store for RAG system."""
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings

from src.rag.embeddings import EmbeddingGenerator
from src.utils.config import get_config

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Base exception for vector store errors."""

    pass


class VectorStore:
    """Manage paper embeddings in ChromaDB."""

    def __init__(
        self,
        collection_name: str = "papers",
        embedding_generator: Optional[EmbeddingGenerator] = None,
    ):
        """Initialize vector store.

        Args:
            collection_name: Name of the ChromaDB collection
            embedding_generator: Optional embedding generator. Creates new one if not provided.

        Raises:
            VectorStoreError: If initialization fails
        """
        self.config = get_config()
        self.collection_name = collection_name

        # Initialize embedding generator
        self.embedding_generator = embedding_generator or EmbeddingGenerator()

        # Initialize ChromaDB client
        try:
            persist_directory = str(self.config.vector_db_path)

            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )

            logger.info(f"Initialized vector store with collection '{collection_name}'")
            logger.info(f"Collection has {self.collection.count()} documents")

        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise VectorStoreError(f"Failed to initialize vector store: {str(e)}") from e

    def add_documents(
        self,
        texts: list[str],
        metadata: list[dict],
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        """Add documents to the vector store.

        Args:
            texts: List of text chunks
            metadata: List of metadata dictionaries (one per text)
            ids: Optional list of document IDs. Auto-generated if not provided.

        Returns:
            List of document IDs

        Raises:
            VectorStoreError: If adding documents fails
        """
        if not texts:
            return []

        if len(texts) != len(metadata):
            raise VectorStoreError(
                f"Number of texts ({len(texts)}) must match number of metadata ({len(metadata)})"
            )

        try:
            logger.info(f"Adding {len(texts)} documents to vector store")

            sanitized_metadata = [
                self._sanitize_metadata(entry) for entry in metadata
            ]

            # Generate IDs if not provided
            if ids is None:
                # Use collection count as base for IDs
                base_count = self.collection.count()
                ids = [f"doc_{base_count + i}" for i in range(len(texts))]

            # Generate embeddings
            embeddings = self.embedding_generator.embed_batch(texts)

            # Add to collection
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=sanitized_metadata,
                ids=ids,
            )

            logger.info(f"Successfully added {len(texts)} documents")
            return ids

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise VectorStoreError(f"Failed to add documents: {str(e)}") from e

    def _sanitize_metadata(self, metadata: dict) -> dict:
        """Ensure metadata values are compatible with ChromaDB."""
        sanitized = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (bool, int, float, str)):
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized

    def add_paper_chunks(
        self, paper_id: int, chunks: list[dict[str, any]]
    ) -> list[str]:
        """Add paper chunks to the vector store.

        Args:
            paper_id: Paper ID
            chunks: List of chunk dictionaries from TextChunker

        Returns:
            List of document IDs

        Raises:
            VectorStoreError: If adding chunks fails
        """
        if not chunks:
            return []

        # Extract texts and metadata
        texts = [chunk["text"] for chunk in chunks]

        metadatas = []
        for chunk in chunks:
            metadata = {
                "paper_id": paper_id,
                "chunk_index": chunk["index"],
                "token_count": chunk["token_count"],
            }
            # Merge any additional metadata from chunk
            if "metadata" in chunk:
                metadata.update(chunk["metadata"])

            metadatas.append(metadata)

        # Generate IDs
        ids = [f"paper_{paper_id}_chunk_{chunk['index']}" for chunk in chunks]

        return self.add_documents(texts, metadatas, ids)

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter: Optional[dict] = None,
    ) -> dict[str, list]:
        """Search for similar documents.

        Args:
            query: Search query
            n_results: Number of results to return
            filter: Optional metadata filter

        Returns:
            Dictionary with 'documents', 'metadatas', 'distances', and 'ids'

        Raises:
            VectorStoreError: If search fails
        """
        try:
            logger.info(f"Searching for: '{query}' (top {n_results})")

            # Generate query embedding
            query_embedding = self.embedding_generator.embed_query(query)

            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter,
                include=["documents", "metadatas", "distances"],
            )

            # ChromaDB returns results as lists of lists, flatten for single query
            flattened_results = {
                "ids": results["ids"][0] if results["ids"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
            }

            logger.info(f"Found {len(flattened_results['ids'])} results")
            return flattened_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise VectorStoreError(f"Search failed: {str(e)}") from e

    def search_by_paper(
        self, query: str, paper_id: int, n_results: int = 5
    ) -> dict[str, list]:
        """Search within a specific paper.

        Args:
            query: Search query
            paper_id: Paper ID to search within
            n_results: Number of results to return

        Returns:
            Search results

        Raises:
            VectorStoreError: If search fails
        """
        filter = {"paper_id": paper_id}
        return self.search(query, n_results=n_results, filter=filter)

    def delete_paper_chunks(self, paper_id: int) -> None:
        """Delete all chunks for a paper.

        Args:
            paper_id: Paper ID

        Raises:
            VectorStoreError: If deletion fails
        """
        try:
            logger.info(f"Deleting chunks for paper {paper_id}")

            # Get all IDs for this paper
            results = self.collection.get(where={"paper_id": paper_id})

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} chunks")
            else:
                logger.info("No chunks found to delete")

        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            raise VectorStoreError(f"Failed to delete chunks: {str(e)}") from e

    def get_paper_chunk_count(self, paper_id: int) -> int:
        """Get the number of chunks for a paper.

        Args:
            paper_id: Paper ID

        Returns:
            Number of chunks
        """
        try:
            results = self.collection.get(where={"paper_id": paper_id})
            return len(results["ids"])
        except Exception:
            return 0

    def count(self) -> int:
        """Get total number of documents in the store.

        Returns:
            Document count
        """
        return self.collection.count()

    def reset(self) -> None:
        """Delete all documents from the collection.

        WARNING: This cannot be undone!

        Raises:
            VectorStoreError: If reset fails
        """
        try:
            logger.warning(f"Resetting collection '{self.collection_name}'")
            self.client.delete_collection(self.collection_name)

            # Recreate collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            logger.info("Collection reset successfully")

        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise VectorStoreError(f"Failed to reset collection: {str(e)}") from e
