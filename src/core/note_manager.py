"""Note management system for papers."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.utils.database import Note, NoteType, Paper, get_session

logger = logging.getLogger(__name__)


class NoteManagerError(Exception):
    """Base exception for note manager errors."""

    pass


class NoteManager:
    """Manage notes for papers."""

    def __init__(self, session: Optional[Session] = None):
        """Initialize note manager.

        Args:
            session: Optional SQLAlchemy session
        """
        self.session = session or get_session()

    def add_note(
        self,
        paper_id: int,
        content: str,
        note_type: str = NoteType.PERSONAL.value,
        section: Optional[str] = None,
    ) -> int:
        """Add a note to a paper.

        Args:
            paper_id: Paper ID
            content: Note content
            note_type: Type of note (personal or ai_generated)
            section: Optional paper section this note relates to

        Returns:
            Note ID

        Raises:
            NoteManagerError: If note cannot be added
        """
        try:
            # Verify paper exists
            paper = self.session.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                raise NoteManagerError(f"Paper with ID {paper_id} not found")

            note = Note(
                paper_id=paper_id, content=content, note_type=note_type, section=section
            )

            self.session.add(note)
            self.session.commit()

            logger.info(f"Added {note_type} note to paper {paper_id}")
            return note.id

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to add note: {e}")
            raise NoteManagerError(f"Failed to add note: {str(e)}") from e

    def get_note(self, note_id: int) -> Note:
        """Get a note by ID.

        Args:
            note_id: Note ID

        Returns:
            Note object

        Raises:
            NoteManagerError: If note not found
        """
        note = self.session.query(Note).filter(Note.id == note_id).first()

        if not note:
            raise NoteManagerError(f"Note with ID {note_id} not found")

        return note

    def get_paper_notes(
        self,
        paper_id: int,
        note_type: Optional[str] = None,
        section: Optional[str] = None,
    ) -> list[Note]:
        """Get all notes for a paper.

        Args:
            paper_id: Paper ID
            note_type: Optional filter by note type
            section: Optional filter by section

        Returns:
            List of notes
        """
        query = self.session.query(Note).filter(Note.paper_id == paper_id)

        if note_type:
            query = query.filter(Note.note_type == note_type)

        if section:
            query = query.filter(Note.section == section)

        return query.order_by(Note.created_at.desc()).all()

    def update_note(self, note_id: int, content: str) -> None:
        """Update a note's content.

        Args:
            note_id: Note ID
            content: New content

        Raises:
            NoteManagerError: If note not found
        """
        note = self.get_note(note_id)
        note.content = content
        self.session.commit()

        logger.info(f"Updated note {note_id}")

    def delete_note(self, note_id: int) -> None:
        """Delete a note.

        Args:
            note_id: Note ID

        Raises:
            NoteManagerError: If note not found
        """
        note = self.get_note(note_id)
        self.session.delete(note)
        self.session.commit()

        logger.info(f"Deleted note {note_id}")

    def merge_notes(self, paper_id: int) -> str:
        """Merge AI-generated and personal notes for a paper.

        Personal notes are displayed with priority.

        Args:
            paper_id: Paper ID

        Returns:
            Merged notes as formatted text
        """
        ai_notes = self.get_paper_notes(paper_id, note_type=NoteType.AI_GENERATED.value)
        personal_notes = self.get_paper_notes(paper_id, note_type=NoteType.PERSONAL.value)

        output = []

        if personal_notes:
            output.append("## Personal Notes\n")
            for note in personal_notes:
                section_header = f"### {note.section}\n" if note.section else ""
                output.append(f"{section_header}{note.content}\n")

        if ai_notes:
            output.append("\n## AI-Generated Notes\n")
            for note in ai_notes:
                section_header = f"### {note.section}\n" if note.section else ""
                output.append(f"{section_header}{note.content}\n")

        return "\n".join(output)
