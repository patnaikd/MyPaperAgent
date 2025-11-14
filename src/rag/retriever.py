"""RAG retriever for semantic search across papers."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.rag.chunker import TextChunker
from src.rag.embeddings import EmbeddingGenerator
from src.rag.vector_store import VectorStore
from src.utils.database import Paper, get_session

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Retrieve relevant paper chunks using RAG."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        session: Optional[Session] = None,
    ):
        """Initialize RAG retriever.

        Args:
            vector_store: Optional vector store. Creates new one if not provided.
            session: Optional database session.
        """
        self.vector_store = vector_store or VectorStore()
        self.session = session or get_session()
        self.chunker = TextChunker()

    def index_paper(self, paper_id: int) -> int:
        """Index a paper for semantic search.

        Chunks the paper text and adds to vector store.

        Args:
            paper_id: Paper ID

        Returns:
            Number of chunks created

        Raises:
            Exception: If indexing fails
        """
        logger.info(f"Indexing paper {paper_id}")

        # Get paper from database
        paper = self.session.query(Paper).filter(Paper.id == paper_id).first()

        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        if not paper.full_text:
            raise ValueError(f"Paper {paper_id} has no text content")

        # Check if already indexed
        existing_count = self.vector_store.get_paper_chunk_count(paper_id)
        if existing_count > 0:
            logger.warning(
                f"Paper {paper_id} already has {existing_count} chunks indexed. "
                "Deleting existing chunks."
            )
            self.vector_store.delete_paper_chunks(paper_id)

        # Chunk the text
        chunks = self.chunker.chunk_text(
            paper.full_text,
            metadata={
                "paper_id": paper_id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
            },
        )

        # Add to vector store
        chunk_ids = self.vector_store.add_paper_chunks(paper_id, chunks)

        logger.info(f"Indexed paper {paper_id} with {len(chunk_ids)} chunks")
        return len(chunk_ids)

    def search(
        self,
        query: str,
        n_results: int = 5,
        paper_id: Optional[int] = None,
    ) -> list[dict[str, any]]:
        """Search for relevant paper chunks.

        Args:
            query: Search query
            n_results: Number of results to return
            paper_id: Optional paper ID to search within

        Returns:
            List of result dictionaries with 'text', 'metadata', 'distance', and 'id'
        """
        if paper_id:
            results = self.vector_store.search_by_paper(query, paper_id, n_results)
        else:
            results = self.vector_store.search(query, n_results)

        # Format results
        formatted_results = []
        for i in range(len(results["ids"])):
            formatted_results.append(
                {
                    "id": results["ids"][i],
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i],
                    "distance": results["distances"][i],
                    "relevance_score": 1 - results["distances"][i],  # Convert distance to score
                }
            )

        return formatted_results

    def get_context_for_query(
        self,
        query: str,
        n_results: int = 5,
        paper_id: Optional[int] = None,
    ) -> str:
        """Get context for a query by retrieving relevant chunks.

        Args:
            query: Search query
            n_results: Number of chunks to retrieve
            paper_id: Optional paper ID to search within

        Returns:
            Concatenated context from relevant chunks
        """
        results = self.search(query, n_results, paper_id)

        # Concatenate chunks
        context_parts = []
        for result in results:
            metadata = result["metadata"]
            title = metadata.get("title", "Unknown")
            paper_id = metadata.get("paper_id", "Unknown")

            context_parts.append(
                f"[Paper {paper_id}: {title}]\n" f"{result['text']}\n"
            )

        return "\n---\n".join(context_parts)

    def delete_paper_index(self, paper_id: int) -> None:
        """Delete all indexed chunks for a paper.

        Args:
            paper_id: Paper ID
        """
        self.vector_store.delete_paper_chunks(paper_id)
        logger.info(f"Deleted index for paper {paper_id}")

    def get_statistics(self) -> dict[str, any]:
        """Get RAG system statistics.

        Returns:
            Dictionary with statistics
        """
        total_chunks = self.vector_store.count()
        total_papers = self.session.query(Paper).count()

        return {
            "total_chunks": total_chunks,
            "total_papers": total_papers,
            "avg_chunks_per_paper": total_chunks / total_papers if total_papers > 0 else 0,
        }


def index_all_papers(retriever: Optional[RAGRetriever] = None) -> dict[str, int]:
    """Index all papers in the database.

    Args:
        retriever: Optional RAG retriever

    Returns:
        Dictionary with indexing statistics
    """
    retriever = retriever or RAGRetriever()
    session = retriever.session

    papers = session.query(Paper).all()

    indexed_count = 0
    failed_count = 0
    total_chunks = 0

    for paper in papers:
        try:
            if paper.full_text:
                chunks = retriever.index_paper(paper.id)
                indexed_count += 1
                total_chunks += chunks
                logger.info(f"Indexed paper {paper.id}: {chunks} chunks")
            else:
                logger.warning(f"Skipping paper {paper.id}: No text content")
                failed_count += 1
        except Exception as e:
            logger.error(f"Failed to index paper {paper.id}: {e}")
            failed_count += 1

    return {
        "indexed": indexed_count,
        "failed": failed_count,
        "total": len(papers),
        "total_chunks": total_chunks,
    }
