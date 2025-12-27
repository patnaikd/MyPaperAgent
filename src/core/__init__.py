"""Core managers for paper and note workflows.

The core package provides high-level CRUD services backed by the application's
SQLite storage. Managers in this package coordinate persistence, file storage,
and metadata extraction for the rest of the app (CLI, UI, and agents).
"""
import logging

from src.core.note_manager import NoteManager, NoteManagerError
from src.core.paper_manager import PaperManager, PaperManagerError, PaperNotFoundError
from src.core.qa_manager import QAHistoryManager, QAHistoryError


logger = logging.getLogger(__name__)

__all__ = [
    "NoteManager",
    "NoteManagerError",
    "PaperManager",
    "PaperManagerError",
    "PaperNotFoundError",
    "QAHistoryManager",
    "QAHistoryError",
]
