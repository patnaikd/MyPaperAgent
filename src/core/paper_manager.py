"""Paper management system for CRUD operations.

This module orchestrates paper ingestion, storage, and retrieval. It ties
together PDF extraction, metadata parsing, and persistent storage so callers
can add papers from local files or URLs and manage their library state.
"""
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from src.processing.metadata_parser import MetadataParser
from src.processing.pdf_extractor import PDFExtractor
from src.utils.config import get_config
from src.utils.database import Paper, ReadingStatus, get_session

logger = logging.getLogger(__name__)


class PaperManagerError(Exception):
    """Base exception for paper manager errors."""

    pass


class PaperNotFoundError(PaperManagerError):
    """Raised when paper is not found."""

    pass


class PaperManager:
    """Manage academic papers in the library."""

    def __init__(self, session: Optional[Session] = None):
        """Initialize paper manager.

        Args:
            session: Optional SQLAlchemy session. If not provided, creates new session.
        """
        self.config = get_config()
        self.session = session or get_session()
        self.pdf_extractor = PDFExtractor()
        self.metadata_parser = MetadataParser()

        # Ensure storage directory exists
        self.config.pdf_storage_path.mkdir(parents=True, exist_ok=True)

    def add_paper_from_pdf(
        self,
        pdf_path: Path,
        tags: Optional[list[str]] = None,
        collection_name: Optional[str] = None,
    ) -> int:
        """Add a paper from a PDF file.

        Args:
            pdf_path: Path to the PDF file
            tags: Optional list of tags
            collection_name: Optional collection to add paper to

        Returns:
            Paper ID

        Raises:
            PaperManagerError: If paper cannot be added
        """
        logger.info(f"Adding paper from PDF: {pdf_path}")

        try:
            # Extract text and metadata from PDF
            result = self.pdf_extractor.extract_from_file(pdf_path)

            # Parse academic metadata
            metadata = self.metadata_parser.parse_metadata(
                result["text"], result["metadata"]
            )

            # Check if paper already exists (by DOI or arXiv ID)
            existing_paper = self._find_existing_paper(
                doi=metadata.get("doi"), arxiv_id=metadata.get("arxiv_id")
            )

            if existing_paper:
                logger.warning(
                    f"Paper already exists with ID {existing_paper.id}. "
                    "Updating instead of creating new entry."
                )
                return existing_paper.id

            # Copy PDF to storage
            stored_path = self._store_pdf(pdf_path)

            # Create paper record
            paper = Paper(
                title=metadata.get("title") or pdf_path.stem,
                authors=metadata.get("authors"),
                abstract=metadata.get("abstract"),
                publication_date=metadata.get("publication_date"),
                doi=metadata.get("doi"),
                arxiv_id=metadata.get("arxiv_id"),
                file_path=str(stored_path),
                full_text=result["text"],
                page_count=result["page_count"],
                journal=metadata.get("journal"),
                year=metadata.get("year"),
                status=ReadingStatus.UNREAD.value,
            )

            self.session.add(paper)
            self.session.commit()

            logger.info(f"Successfully added paper with ID: {paper.id}")

            # Add tags if provided
            if tags:
                self._add_tags(paper.id, tags)

            # Add to collection if provided
            if collection_name:
                self._add_to_collection(paper.id, collection_name)

            return paper.id

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to add paper from PDF: {e}")
            raise PaperManagerError(f"Failed to add paper: {str(e)}") from e

    def add_paper_from_url(
        self,
        url: str,
        tags: Optional[list[str]] = None,
        collection_name: Optional[str] = None,
    ) -> int:
        """Add a paper from a URL.

        Downloads the PDF and adds it to the library.

        Args:
            url: URL to the PDF
            tags: Optional list of tags
            collection_name: Optional collection to add paper to

        Returns:
            Paper ID

        Raises:
            PaperManagerError: If paper cannot be added
        """
        logger.info(f"Adding paper from URL: {url}")

        try:
            # Download PDF to temporary location
            temp_pdf = self._download_pdf(url)

            # Add paper from the downloaded PDF
            paper_id = self.add_paper_from_pdf(temp_pdf, tags, collection_name)

            # Update URL in database
            paper = self.get_paper(paper_id)
            paper.url = url
            self.session.commit()

            # Clean up temporary file
            temp_pdf.unlink()

            return paper_id

        except Exception as e:
            logger.error(f"Failed to add paper from URL: {e}")
            raise PaperManagerError(f"Failed to add paper from URL: {str(e)}") from e

    def get_paper(self, paper_id: int) -> Paper:
        """Get a paper by ID.

        Args:
            paper_id: Paper ID

        Returns:
            Paper object

        Raises:
            PaperNotFoundError: If paper not found
        """
        paper = self.session.query(Paper).filter(Paper.id == paper_id).first()

        if not paper:
            raise PaperNotFoundError(f"Paper with ID {paper_id} not found")

        return paper

    def list_papers(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Paper]:
        """List papers in the library.

        Args:
            status: Optional filter by reading status
            limit: Optional limit on number of results
            offset: Offset for pagination

        Returns:
            List of Paper objects
        """
        query = self.session.query(Paper)

        if status:
            query = query.filter(Paper.status == status)

        query = query.order_by(Paper.added_date.desc())

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        return query.all()

    def update_paper_status(self, paper_id: int, status: str) -> None:
        """Update the reading status of a paper.

        Args:
            paper_id: Paper ID
            status: New status (unread, reading, completed, archived)

        Raises:
            PaperNotFoundError: If paper not found
        """
        paper = self.get_paper(paper_id)
        paper.status = status

        if status == ReadingStatus.COMPLETED.value:
            paper.completed_date = datetime.utcnow()

        self.session.commit()
        logger.info(f"Updated paper {paper_id} status to {status}")

    def delete_paper(self, paper_id: int, delete_file: bool = True) -> None:
        """Delete a paper from the library.

        Args:
            paper_id: Paper ID
            delete_file: Whether to delete the PDF file

        Raises:
            PaperNotFoundError: If paper not found
        """
        paper = self.get_paper(paper_id)

        # Delete PDF file if requested
        if delete_file and paper.file_path:
            file_path = Path(paper.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted PDF file: {file_path}")

        # Delete from database (cascades to notes, tags, etc.)
        self.session.delete(paper)
        self.session.commit()

        logger.info(f"Deleted paper {paper_id}")

    def search_papers(self, query: str, limit: int = 10) -> list[Paper]:
        """Search papers by title, authors, or abstract.

        This is a simple text-based search. For semantic search,
        use the RAG retriever.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching papers
        """
        search_pattern = f"%{query}%"

        results = (
            self.session.query(Paper)
            .filter(
                (Paper.title.ilike(search_pattern))
                | (Paper.authors.ilike(search_pattern))
                | (Paper.abstract.ilike(search_pattern))
            )
            .limit(limit)
            .all()
        )

        return results

    def get_paper_count(self, status: Optional[str] = None) -> int:
        """Get count of papers in library.

        Args:
            status: Optional filter by status

        Returns:
            Number of papers
        """
        query = self.session.query(Paper)

        if status:
            query = query.filter(Paper.status == status)

        return query.count()

    # Private helper methods

    def _find_existing_paper(
        self, doi: Optional[str] = None, arxiv_id: Optional[str] = None
    ) -> Optional[Paper]:
        """Check if paper already exists by DOI or arXiv ID.

        Args:
            doi: DOI to check
            arxiv_id: arXiv ID to check

        Returns:
            Existing paper or None
        """
        if doi:
            paper = self.session.query(Paper).filter(Paper.doi == doi).first()
            if paper:
                return paper

        if arxiv_id:
            paper = self.session.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
            if paper:
                return paper

        return None

    def _store_pdf(self, source_path: Path) -> Path:
        """Copy PDF to storage directory.

        Args:
            source_path: Source PDF path

        Returns:
            Path to stored PDF
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{source_path.name}"
        dest_path = self.config.pdf_storage_path / filename

        # Copy file
        shutil.copy2(source_path, dest_path)
        logger.info(f"Stored PDF at: {dest_path}")

        return dest_path

    def _download_pdf(self, url: str) -> Path:
        """Download PDF from URL to temporary location.

        Args:
            url: URL to download from

        Returns:
            Path to downloaded PDF

        Raises:
            PaperManagerError: If download fails
        """
        try:
            # Parse filename from URL
            parsed = urlparse(url)
            filename = Path(parsed.path).name or "downloaded.pdf"

            # Ensure it has .pdf extension
            if not filename.lower().endswith(".pdf"):
                filename = f"{filename}.pdf"

            # Download to temp location
            temp_path = Path("/tmp") / filename

            logger.info(f"Downloading PDF from {url}")
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded PDF to {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Failed to download PDF: {e}")
            raise PaperManagerError(f"Failed to download PDF: {str(e)}") from e

    def _add_tags(self, paper_id: int, tags: list[str]) -> None:
        """Add tags to a paper.

        Args:
            paper_id: Paper ID
            tags: List of tag names
        """
        from src.utils.database import Tag

        for tag_name in tags:
            tag = Tag(paper_id=paper_id, tag_name=tag_name.strip())
            self.session.add(tag)

        self.session.commit()
        logger.info(f"Added {len(tags)} tags to paper {paper_id}")

    def _add_to_collection(self, paper_id: int, collection_name: str) -> None:
        """Add paper to a collection.

        Args:
            paper_id: Paper ID
            collection_name: Collection name
        """
        from src.utils.database import Collection, PaperCollection

        # Find or create collection
        collection = (
            self.session.query(Collection)
            .filter(Collection.name == collection_name)
            .first()
        )

        if not collection:
            collection = Collection(name=collection_name)
            self.session.add(collection)
            self.session.commit()

        # Add paper to collection
        paper_collection = PaperCollection(
            paper_id=paper_id, collection_id=collection.id
        )
        self.session.add(paper_collection)
        self.session.commit()

        logger.info(f"Added paper {paper_id} to collection '{collection_name}'")
