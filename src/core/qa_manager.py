"""Q&A history management for papers."""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.utils.database import QAEntry, Paper, get_session

logger = logging.getLogger(__name__)


class QAHistoryError(Exception):
    """Base exception for Q&A history errors."""

    pass


class QAHistoryManager:
    """Manage Q&A history entries for papers."""

    def __init__(self, session: Optional[Session] = None):
        """Initialize Q&A history manager.

        Args:
            session: Optional SQLAlchemy session
        """
        self.session = session or get_session()

    def add_entry(
        self,
        paper_id: int,
        question: str,
        answer: str,
        sources: Optional[list[dict[str, str]]] = None,
    ) -> int:
        """Add a Q&A entry for a paper.

        Args:
            paper_id: Paper ID
            question: Question text
            answer: Answer text
            sources: Optional list of source dicts

        Returns:
            Entry ID
        """
        try:
            paper = self.session.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                raise QAHistoryError(f"Paper with ID {paper_id} not found")

            entry = QAEntry(
                paper_id=paper_id,
                question=question,
                answer=answer,
                sources=self._serialize_sources(sources),
            )
            self.session.add(entry)
            self.session.commit()
            logger.info("Added Q&A entry for paper %s", paper_id)
            return entry.id
        except Exception as exc:
            self.session.rollback()
            logger.error("Failed to add Q&A entry: %s", exc)
            raise QAHistoryError(f"Failed to add Q&A entry: {exc}") from exc

    def add_entry_if_new(
        self,
        paper_id: int,
        question: str,
        answer: str,
        sources: Optional[list[dict[str, str]]] = None,
    ) -> tuple[int, bool]:
        """Add a Q&A entry unless it already exists.

        Args:
            paper_id: Paper ID
            question: Question text
            answer: Answer text
            sources: Optional list of source dicts

        Returns:
            (entry_id, created_new)
        """
        existing = self.find_entry(paper_id, question, answer)
        if existing:
            return existing.id, False
        entry_id = self.add_entry(paper_id, question, answer, sources)
        return entry_id, True

    def find_entry(self, paper_id: int, question: str, answer: str) -> Optional[QAEntry]:
        """Find an existing Q&A entry by question and answer."""
        return (
            self.session.query(QAEntry)
            .filter(
                QAEntry.paper_id == paper_id,
                QAEntry.question == question,
                QAEntry.answer == answer,
            )
            .first()
        )

    def get_entries(self, paper_id: int, limit: Optional[int] = None) -> list[QAEntry]:
        """Get Q&A entries for a paper, newest first."""
        query = self.session.query(QAEntry).filter(QAEntry.paper_id == paper_id)
        query = query.order_by(QAEntry.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def _serialize_sources(sources: Optional[list[dict[str, str]]]) -> Optional[str]:
        if not sources:
            return None
        try:
            return json.dumps(sources)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def deserialize_sources(raw: Optional[str]) -> list[dict[str, str]]:
        """Parse stored JSON sources into a list."""
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []
