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
    MetaData,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.schema import CreateTable

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
    arxiv_id = Column(String(50), nullable=True, index=True)
    url = Column(String(500), nullable=True)
    speechify_url = Column(String(500), nullable=True)
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
    paper_authors = relationship(
        "PaperAuthor", back_populates="paper", cascade="all, delete-orphan"
    )
    semantic_scholar = relationship(
        "PaperSemanticScholar", back_populates="paper", uselist=False, cascade="all, delete-orphan"
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


class Author(Base):
    """Author metadata collected from external sources."""

    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    semantic_scholar_id = Column(String(50), nullable=True, unique=True, index=True)
    name = Column(String(200), nullable=True, index=True)
    homepage = Column(String(500), nullable=True)
    semantic_scholar_url = Column(String(500), nullable=True)
    dblp_url = Column(String(500), nullable=True)
    affiliation = Column(String(500), nullable=True)
    introduction = Column(Text, nullable=True)
    top_cited_papers = Column(Text, nullable=True)
    coauthors = Column(Text, nullable=True)
    research_interests = Column(Text, nullable=True)
    sources = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    paper_links = relationship(
        "PaperAuthor", back_populates="author", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Author(id={self.id}, name='{self.name}')>"


class PaperAuthor(Base):
    """Link table between papers and authors."""

    __tablename__ = "paper_authors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False, index=True)
    author_order = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    paper = relationship("Paper", back_populates="paper_authors")
    author = relationship("Author", back_populates="paper_links")

    def __repr__(self) -> str:
        return f"<PaperAuthor(paper_id={self.paper_id}, author_id={self.author_id})>"


class PaperSemanticScholar(Base):
    """Raw Semantic Scholar response stored by paper."""

    __tablename__ = "paper_semantic_scholar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, unique=True, index=True)
    response_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    paper = relationship("Paper", back_populates="semantic_scholar")

    def __repr__(self) -> str:
        return f"<PaperSemanticScholar(paper_id={self.paper_id})>"


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
        inspector = inspect(engine)
    _ensure_paper_columns(engine, inspector)
    _ensure_paper_constraints(engine, inspector)


def _ensure_paper_columns(engine, inspector) -> None:
    """Add missing columns to the papers table for existing databases."""
    if "papers" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("papers")}
    missing_columns = {
        "speechify_url": "speechify_url VARCHAR(500)",
    }

    for name, ddl in missing_columns.items():
        if name in existing_columns:
            continue
        try:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE papers ADD COLUMN {ddl}"))
            logger.info("Added missing column '%s' to papers table.", name)
        except Exception as exc:
            logger.warning("Failed to add column '%s' to papers table: %s", name, exc)


def _ensure_paper_constraints(engine, inspector) -> None:
    """Ensure the papers table does not enforce uniqueness on arxiv_id."""
    if "papers" not in inspector.get_table_names():
        return

    try:
        with engine.connect() as connection:
            if not _has_unique_arxiv_id(connection):
                return
    except Exception as exc:
        logger.warning("Failed to inspect papers constraints: %s", exc)
        return

    logger.info("Removing UNIQUE constraint on papers.arxiv_id")
    try:
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))

            metadata = MetaData()
            new_table = Paper.__table__.to_metadata(metadata, name="papers_new")
            connection.execute(CreateTable(new_table))

            column_names = [column.name for column in new_table.columns]
            columns_csv = ", ".join(column_names)
            connection.execute(
                text(
                    f"INSERT INTO papers_new ({columns_csv}) "
                    f"SELECT {columns_csv} FROM papers"
                )
            )
            connection.execute(text("DROP TABLE papers"))
            connection.execute(text("ALTER TABLE papers_new RENAME TO papers"))
            connection.execute(text("PRAGMA foreign_keys=ON"))
    except Exception as exc:
        logger.warning("Failed to rebuild papers table: %s", exc)
        return

    try:
        for index in Paper.__table__.indexes:
            index.create(bind=engine, checkfirst=True)
    except Exception as exc:
        logger.warning("Failed to recreate papers indexes: %s", exc)


def _has_unique_arxiv_id(connection) -> bool:
    indexes = connection.execute(text("PRAGMA index_list('papers')")).mappings().all()
    for index in indexes:
        if not index.get("unique"):
            continue
        index_name = index.get("name")
        if not index_name:
            continue
        columns = connection.execute(
            text(f"PRAGMA index_info('{index_name}')")
        ).mappings()
        column_names = [row.get("name") for row in columns if row.get("name")]
        if column_names == ["arxiv_id"]:
            return True
    return False

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
