"""Paper management system for CRUD operations.

This module orchestrates paper ingestion, storage, and retrieval. It ties
together PDF extraction, external metadata enrichment, and persistent storage
so callers can add papers from local files or URLs and manage their library state.
"""
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from src.agents.author_info import AuthorInfoAgent
from src.discovery.arxiv_search import ArxivSearch
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

        # Ensure storage directory exists
        self.config.pdf_storage_path.mkdir(parents=True, exist_ok=True)

    def add_paper_from_pdf(
        self,
        pdf_path: Path,
        tags: Optional[list[str]] = None,
        collection_name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Add a paper from a PDF file.

        Args:
            pdf_path: Path to the PDF file
            tags: Optional list of tags
            collection_name: Optional collection to add paper to
            metadata: Optional paper metadata from external sources

        Returns:
            Paper ID

        Raises:
            PaperManagerError: If paper cannot be added
        """
        logger.info(f"Adding paper from PDF: {pdf_path}")

        try:
            # Extract text from PDF (delay JSON save until stored path is known)
            result = self.pdf_extractor.extract_from_file(pdf_path, save_json=False)

            metadata = metadata or {}

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
            self.pdf_extractor.save_structured_text(stored_path, result)

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
                citations_count=metadata.get("citations_count", 0) or 0,
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
            metadata, paper_meta, author_entries = self._fetch_external_metadata(url)
            existing_paper = self._find_existing_paper(
                doi=metadata.get("doi"), arxiv_id=metadata.get("arxiv_id")
            )
            if existing_paper:
                existing_paper.url = url
                if metadata:
                    self._apply_metadata_to_paper(existing_paper, metadata)
                self.session.commit()
                self._store_author_metadata(existing_paper.id, author_entries, paper_meta)
                return existing_paper.id

            temp_pdf = None
            try:
                # Download PDF to temporary location
                temp_pdf = self._download_pdf(url)

                # Add paper from the downloaded PDF
                paper_id = self.add_paper_from_pdf(
                    temp_pdf,
                    tags=tags,
                    collection_name=collection_name,
                    metadata=metadata,
                )

                # Update URL in database
                paper = self.get_paper(paper_id)
                paper.url = url
                if metadata:
                    self._apply_metadata_to_paper(paper, metadata)
                self.session.commit()

                self._store_author_metadata(paper_id, author_entries, paper_meta)

                return paper_id
            finally:
                if temp_pdf and temp_pdf.exists():
                    temp_pdf.unlink()

        except Exception as e:
            logger.error(f"Failed to add paper from URL: {e}")
            raise PaperManagerError(f"Failed to add paper from URL: {str(e)}") from e

    def refresh_semantic_scholar_metadata(self, paper_id: int) -> None:
        """Refresh paper and author metadata from Semantic Scholar."""
        paper = self.get_paper(paper_id)
        semantic_id = self._build_semantic_scholar_id(paper)
        if not semantic_id:
            raise PaperManagerError(
                "Semantic Scholar refresh requires an arXiv ID or DOI on the paper."
            )

        try:
            agent = AuthorInfoAgent()
            paper_meta = agent.fetch_paper_metadata(semantic_id)
            if not paper_meta:
                raise PaperManagerError("No metadata returned from Semantic Scholar.")

            metadata = self._map_semantic_scholar_metadata(paper_meta)
            self._apply_metadata_to_paper(paper, metadata)
            self.session.commit()

            author_entries = self._extract_semantic_scholar_author_ids(paper_meta)
            agent.store_paper_metadata(paper.id, paper_meta)
            if author_entries:
                author_infos = agent.fetch_authors_info(author_entries)
                agent.store_author_infos(paper.id, author_infos)
        except Exception as exc:
            self.session.rollback()
            raise PaperManagerError(
                f"Failed to refresh Semantic Scholar metadata: {exc}"
            ) from exc

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

    def update_paper(self, paper_id: int, status: str) -> None:
        """Backward-compatible wrapper for updating paper status."""
        self.update_paper_status(paper_id, status)

    def update_speechify_url(self, paper_id: int, speechify_url: Optional[str]) -> None:
        """Update the Speechify URL for a paper."""
        paper = self.get_paper(paper_id)
        paper.speechify_url = speechify_url or None
        self.session.commit()
        logger.info("Updated paper %s Speechify URL", paper_id)

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

    def _apply_metadata_to_paper(self, paper: Paper, metadata: dict[str, Any]) -> None:
        if metadata.get("title"):
            paper.title = metadata["title"]
        if metadata.get("authors"):
            paper.authors = metadata["authors"]
        if metadata.get("abstract"):
            paper.abstract = metadata["abstract"]
        if metadata.get("publication_date"):
            paper.publication_date = metadata["publication_date"]
        if metadata.get("doi"):
            paper.doi = metadata["doi"]
        if metadata.get("arxiv_id"):
            paper.arxiv_id = metadata["arxiv_id"]
        if metadata.get("journal"):
            paper.journal = metadata["journal"]
        if metadata.get("year"):
            paper.year = metadata["year"]
        if metadata.get("citations_count") is not None:
            paper.citations_count = metadata["citations_count"]

    def _build_semantic_scholar_id(self, paper: Paper) -> Optional[str]:
        arxiv_id = paper.arxiv_id or self._extract_arxiv_id_from_url(paper.url or "")
        if arxiv_id:
            return f"ARXIV:{arxiv_id}"

        doi = paper.doi or self._extract_doi_from_url(paper.url or "")
        if doi:
            return f"DOI:{doi}"

        return None

    def _fetch_external_metadata(
        self, url: str
    ) -> tuple[dict[str, Any], Optional[dict[str, Any]], list[dict[str, Any]]]:
        metadata: dict[str, Any] = {}
        paper_meta: Optional[dict[str, Any]] = None
        author_entries: list[dict[str, Any]] = []

        arxiv_id = self._extract_arxiv_id_from_url(url)
        doi = self._extract_doi_from_url(url)

        if arxiv_id or doi:
            semantic_id = f"ARXIV:{arxiv_id}" if arxiv_id else f"DOI:{doi}"
            try:
                agent = AuthorInfoAgent()
                paper_meta = agent.fetch_paper_metadata(semantic_id)
                if paper_meta:
                    metadata = self._map_semantic_scholar_metadata(paper_meta)
                    author_entries = self._extract_semantic_scholar_authors(paper_meta)
            except Exception as exc:
                logger.warning("Semantic Scholar metadata fetch failed: %s", exc)

        if not metadata and arxiv_id:
            try:
                searcher = ArxivSearch(max_results=1)
                arxiv_meta = searcher.get_paper_by_id(arxiv_id)
                metadata = self._map_arxiv_metadata(arxiv_meta)
                author_entries = self._extract_arxiv_authors(arxiv_meta)
            except Exception as exc:
                logger.warning("arXiv metadata fetch failed: %s", exc)

        if arxiv_id and not metadata.get("arxiv_id"):
            metadata["arxiv_id"] = arxiv_id
        if doi and not metadata.get("doi"):
            metadata["doi"] = doi

        return metadata, paper_meta, author_entries

    def _store_author_metadata(
        self,
        paper_id: int,
        author_entries: list[dict[str, Any]],
        paper_meta: Optional[dict[str, Any]],
    ) -> None:
        if not author_entries and not paper_meta:
            return

        try:
            agent = AuthorInfoAgent()
            if paper_meta:
                agent.store_paper_metadata(paper_id, paper_meta)
            if author_entries:
                author_infos = agent.fetch_authors_info(author_entries)
                agent.store_author_infos(paper_id, author_infos)
        except Exception as exc:
            logger.warning(
                "Failed to store author metadata for paper %s: %s",
                paper_id,
                exc,
            )

    def _map_semantic_scholar_metadata(
        self, paper_meta: dict[str, Any]
    ) -> dict[str, Any]:
        if not paper_meta:
            return {}

        external_ids = paper_meta.get("externalIds") or {}
        doi = self._extract_external_id(external_ids, "doi")
        arxiv_id = self._extract_external_id(external_ids, "arxiv")

        authors = paper_meta.get("authors") or []
        author_names = [
            author.get("name")
            for author in authors
            if isinstance(author, dict) and author.get("name")
        ]
        authors_text = ", ".join(author_names) if author_names else None

        journal = None
        journal_meta = paper_meta.get("journal")
        if isinstance(journal_meta, dict):
            journal = journal_meta.get("name") or journal_meta.get("pages")
        elif isinstance(journal_meta, str):
            journal = journal_meta
        if not journal:
            venue = paper_meta.get("publicationVenue")
            if isinstance(venue, dict):
                journal = venue.get("name")
        if not journal:
            journal = paper_meta.get("venue")

        return {
            "title": paper_meta.get("title"),
            "authors": authors_text,
            "abstract": paper_meta.get("abstract"),
            "publication_date": paper_meta.get("publicationDate"),
            "doi": doi,
            "arxiv_id": arxiv_id,
            "journal": journal,
            "year": paper_meta.get("year"),
            "citations_count": paper_meta.get("citationCount"),
        }

    def _map_arxiv_metadata(self, arxiv_meta: dict[str, Any]) -> dict[str, Any]:
        published = arxiv_meta.get("published")
        year = self._parse_year(published) if published else None
        return {
            "title": arxiv_meta.get("title"),
            "authors": arxiv_meta.get("authors"),
            "abstract": arxiv_meta.get("abstract"),
            "publication_date": published,
            "doi": arxiv_meta.get("doi"),
            "arxiv_id": arxiv_meta.get("arxiv_id"),
            "journal": arxiv_meta.get("journal_ref"),
            "year": year,
        }

    def _extract_semantic_scholar_authors(
        self, paper_meta: dict[str, Any]
    ) -> list[dict[str, Any]]:
        authors = paper_meta.get("authors") or []
        entries: list[dict[str, Any]] = []
        for author in authors:
            if isinstance(author, dict):
                name = author.get("name")
                author_id = author.get("authorId")
            else:
                name = author
                author_id = None
            if isinstance(name, str) and name.strip():
                entries.append({"name": name.strip(), "author_id": author_id})
            elif author_id:
                entries.append({"name": "Unknown author", "author_id": author_id})
        return entries

    def _extract_semantic_scholar_author_ids(
        self, paper_meta: dict[str, Any]
    ) -> list[dict[str, Any]]:
        authors = paper_meta.get("authors") or []
        entries: list[dict[str, Any]] = []
        for author in authors:
            if not isinstance(author, dict):
                continue
            author_id = author.get("authorId")
            if author_id:
                entries.append({"name": None, "author_id": author_id})
        return entries

    def _extract_arxiv_authors(self, arxiv_meta: dict[str, Any]) -> list[dict[str, Any]]:
        authors = arxiv_meta.get("authors") or ""
        return [
            {"name": name, "author_id": None}
            for name in self._split_authors(authors)
        ]

    @staticmethod
    def _split_authors(authors: str) -> list[str]:
        cleaned = authors.replace(" and ", ", ")
        return [author.strip() for author in cleaned.split(",") if author.strip()]

    @staticmethod
    def _extract_arxiv_id_from_url(url: str) -> Optional[str]:
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#]+)", url)
        if not match:
            return None
        arxiv_id = match.group(1)
        if arxiv_id.endswith(".pdf"):
            arxiv_id = arxiv_id[:-4]
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
        return arxiv_id or None

    @staticmethod
    def _extract_doi_from_url(url: str) -> Optional[str]:
        match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", url, re.IGNORECASE)
        if not match:
            return None
        return match.group(0).rstrip(").,;")

    @staticmethod
    def _extract_external_id(external_ids: dict[str, Any], key: str) -> Optional[str]:
        if not external_ids:
            return None
        for candidate in (key, key.lower(), key.upper(), key.title()):
            value = external_ids.get(candidate)
            if value:
                return str(value)
        for ext_key, value in external_ids.items():
            if ext_key.lower() == key.lower() and value:
                return str(value)
        return None

    @staticmethod
    def _parse_year(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        match = re.match(r"(\d{4})", value)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
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
