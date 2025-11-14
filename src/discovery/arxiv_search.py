"""arXiv API integration for paper discovery."""
import logging
from datetime import datetime
from typing import Optional

import arxiv

logger = logging.getLogger(__name__)


class ArxivSearchError(Exception):
    """Base exception for arXiv search errors."""

    pass


class ArxivSearch:
    """Search and retrieve papers from arXiv."""

    def __init__(self, max_results: int = 10):
        """Initialize arXiv search.

        Args:
            max_results: Maximum number of results to return
        """
        self.max_results = max_results
        self.client = arxiv.Client()

    def search_by_topic(
        self, topic: str, max_results: Optional[int] = None
    ) -> list[dict[str, any]]:
        """Search arXiv by topic/keywords.

        Args:
            topic: Search query
            max_results: Optional max results (overrides default)

        Returns:
            List of paper dictionaries

        Raises:
            ArxivSearchError: If search fails
        """
        try:
            logger.info(f"Searching arXiv for: {topic}")

            search = arxiv.Search(
                query=topic,
                max_results=max_results or self.max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )

            results = []
            for result in self.client.results(search):
                results.append(self._format_result(result))

            logger.info(f"Found {len(results)} papers on arXiv")
            return results

        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            raise ArxivSearchError(f"Search failed: {str(e)}") from e

    def search_by_author(
        self, author: str, max_results: Optional[int] = None
    ) -> list[dict[str, any]]:
        """Search arXiv by author name.

        Args:
            author: Author name
            max_results: Optional max results

        Returns:
            List of paper dictionaries

        Raises:
            ArxivSearchError: If search fails
        """
        try:
            query = f"au:{author}"
            return self.search_by_topic(query, max_results)

        except Exception as e:
            logger.error(f"Author search failed: {e}")
            raise ArxivSearchError(f"Author search failed: {str(e)}") from e

    def search_recent(
        self, category: Optional[str] = None, max_results: Optional[int] = None
    ) -> list[dict[str, any]]:
        """Search for recent papers on arXiv.

        Args:
            category: Optional category filter (e.g., "cs.AI", "cs.LG")
            max_results: Optional max results

        Returns:
            List of paper dictionaries

        Raises:
            ArxivSearchError: If search fails
        """
        try:
            query = f"cat:{category}" if category else "all"

            search = arxiv.Search(
                query=query,
                max_results=max_results or self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            results = []
            for result in self.client.results(search):
                results.append(self._format_result(result))

            logger.info(f"Found {len(results)} recent papers")
            return results

        except Exception as e:
            logger.error(f"Recent papers search failed: {e}")
            raise ArxivSearchError(f"Recent search failed: {str(e)}") from e

    def get_paper_by_id(self, arxiv_id: str) -> dict[str, any]:
        """Get a specific paper by arXiv ID.

        Args:
            arxiv_id: arXiv ID (e.g., "1706.03762")

        Returns:
            Paper dictionary

        Raises:
            ArxivSearchError: If retrieval fails
        """
        try:
            logger.info(f"Fetching arXiv paper: {arxiv_id}")

            search = arxiv.Search(id_list=[arxiv_id])
            result = next(self.client.results(search))

            return self._format_result(result)

        except Exception as e:
            logger.error(f"Failed to fetch paper {arxiv_id}: {e}")
            raise ArxivSearchError(f"Failed to fetch paper: {str(e)}") from e

    def _format_result(self, result: arxiv.Result) -> dict[str, any]:
        """Format arXiv result into standardized dictionary.

        Args:
            result: arXiv Result object

        Returns:
            Formatted dictionary
        """
        return {
            "title": result.title,
            "authors": ", ".join([author.name for author in result.authors]),
            "abstract": result.summary,
            "arxiv_id": result.entry_id.split("/")[-1].replace("v", "").split("v")[0],
            "url": result.entry_id,
            "pdf_url": result.pdf_url,
            "published": result.published.strftime("%Y-%m-%d") if result.published else None,
            "updated": result.updated.strftime("%Y-%m-%d") if result.updated else None,
            "categories": result.categories,
            "primary_category": result.primary_category,
            "doi": result.doi,
            "journal_ref": result.journal_ref,
        }


def search_arxiv(topic: str, max_results: int = 10) -> list[dict[str, any]]:
    """Convenience function to search arXiv.

    Args:
        topic: Search query
        max_results: Maximum results

    Returns:
        List of paper dictionaries
    """
    searcher = ArxivSearch(max_results=max_results)
    return searcher.search_by_topic(topic)
