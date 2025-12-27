"""Database models and initialization for MyPaperAgent."""
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from src.utils.config import get_config


logger = logging.getLogger(__name__)

Base = declarative_base()


class ReadingStatus(str, Enum):
    """Reading status for papers."""

    UNREAD = "unread"
    READING = "reading"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class NoteType(str, Enum):
    """Type of note."""

    PERSONAL = "personal"
    AI_GENERATED = "ai_generated"


class QuestionDifficulty(str, Enum):
    """Difficulty level for quiz questions."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Paper(Base):
    """Paper metadata and storage information."""

    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, index=True)
    authors = Column(Text, nullable=True)  # Stored as comma-separated list
    abstract = Column(Text, nullable=True)
    publication_date = Column(String(50), nullable=True)
    doi = Column(String(100), nullable=True, unique=True, index=True)
    arxiv_id = Column(String(50), nullable=True, unique=True, index=True)
    url = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)  # Local PDF path
    status = Column(String(20), default=ReadingStatus.UNREAD.value, index=True)
    added_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_date = Column(DateTime, nullable=True)

    # Content
    full_text = Column(Text, nullable=True)  # Extracted text from PDF
    page_count = Column(Integer, nullable=True)

    # Metadata
    journal = Column(String(200), nullable=True)
    year = Column(Integer, nullable=True, index=True)
    citations_count = Column(Integer, default=0)

    # Relationships
    notes = relationship("Note", back_populates="paper", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="paper", cascade="all, delete-orphan")
    quiz_questions = relationship(
        "QuizQuestion", back_populates="paper", cascade="all, delete-orphan"
    )
    qa_entries = relationship(
        "QAEntry", back_populates="paper", cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "Embedding", back_populates="paper", cascade="all, delete-orphan"
    )
    paper_collections = relationship(
        "PaperCollection", back_populates="paper", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, title='{self.title[:50]}...')>"


class Note(Base):
    """Notes (personal or AI-generated) for papers."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    note_type = Column(String(20), default=NoteType.PERSONAL.value, nullable=False)
    section = Column(String(200), nullable=True)  # Which section of paper
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    paper = relationship("Paper", back_populates="notes")

    def __repr__(self) -> str:
        return f"<Note(id={self.id}, paper_id={self.paper_id}, type={self.note_type})>"


class Collection(Base):
    """Collections to organize papers."""

    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    paper_collections = relationship(
        "PaperCollection", back_populates="collection", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name='{self.name}')>"


class PaperCollection(Base):
    """Many-to-many relationship between papers and collections."""

    __tablename__ = "paper_collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    paper = relationship("Paper", back_populates="paper_collections")
    collection = relationship("Collection", back_populates="paper_collections")

    def __repr__(self) -> str:
        return f"<PaperCollection(paper_id={self.paper_id}, collection_id={self.collection_id})>"


class Tag(Base):
    """Tags for papers."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    tag_name = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    paper = relationship("Paper", back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, paper_id={self.paper_id}, tag='{self.tag_name}')>"


class QuizQuestion(Base):
    """Quiz questions generated for papers."""

    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(20), default=QuestionDifficulty.MEDIUM.value)
    times_answered = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    paper = relationship("Paper", back_populates="quiz_questions")

    def __repr__(self) -> str:
        return f"<QuizQuestion(id={self.id}, paper_id={self.paper_id}, difficulty={self.difficulty})>"


class QAEntry(Base):
    """Question/answer entries for papers."""

    __tablename__ = "qa_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    paper = relationship("Paper", back_populates="qa_entries")

    def __repr__(self) -> str:
        return f"<QAEntry(id={self.id}, paper_id={self.paper_id})>"


class Embedding(Base):
    """Vector embeddings for paper chunks."""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    section = Column(String(200), nullable=True)  # Section of paper
    vector_id = Column(String(100), nullable=True)  # ID in ChromaDB
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    paper = relationship("Paper", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<Embedding(id={self.id}, paper_id={self.paper_id}, chunk={self.chunk_index})>"


# Database session management
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        config = get_config()
        database_url = f"sqlite:///{config.database_path}"
        _engine = create_engine(database_url, echo=config.debug)
        ensure_database_initialized(_engine)
    return _engine


def get_session():
    """Get a database session."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal()


def init_database() -> None:
    """Initialize the database (create all tables)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def ensure_database_initialized(engine) -> None:
    """Create tables if the database is uninitialized."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())
    if expected_tables - existing_tables:
        Base.metadata.create_all(bind=engine)


def drop_all_tables() -> None:
    """Drop all tables (use with caution!)."""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped!")


if __name__ == "__main__":
    """Run this module to initialize the database."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "drop":
        response = input("Are you sure you want to drop all tables? (yes/no): ")
        if response.lower() == "yes":
            drop_all_tables()
        else:
            print("Cancelled.")
    else:
        print("Usage: python -m src.utils.database [init|drop]")
