"""Pytest configuration and shared fixtures."""
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.utils.database import Base


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_papers_dir(test_data_dir: Path) -> Path:
    """Path to sample papers directory."""
    return test_data_dir / "papers"


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a test database session.

    This fixture creates an in-memory SQLite database for testing
    and provides a session that will be rolled back after each test.
    """
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    yield session

    # Cleanup
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def mock_anthropic_client(monkeypatch: pytest.MonkeyPatch):
    """Mock Anthropic API client for testing."""
    # TODO: Implement mock client once we have actual API integration
    pass


@pytest.fixture(scope="function")
def mock_voyage_client(monkeypatch: pytest.MonkeyPatch):
    """Mock Voyage AI client for testing."""
    # TODO: Implement mock client once we have actual API integration
    pass


@pytest.fixture(scope="function")
def sample_paper_metadata() -> dict:
    """Sample paper metadata for testing."""
    return {
        "title": "Attention Is All You Need",
        "authors": "Vaswani, Ashish; Shazeer, Noam; Parmar, Niki",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        "publication_date": "2017-06-12",
        "doi": "10.48550/arXiv.1706.03762",
        "arxiv_id": "1706.03762",
        "url": "https://arxiv.org/abs/1706.03762",
        "journal": "NeurIPS",
        "year": 2017,
    }


@pytest.fixture(scope="function")
def sample_pdf_path(tmp_path: Path) -> Path:
    """Create a sample PDF file path for testing.

    Note: This creates an empty file. For tests that require
    actual PDF content, use a real sample PDF.
    """
    pdf_path = tmp_path / "test_paper.pdf"
    pdf_path.touch()
    return pdf_path


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Set up test environment variables for all tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VECTOR_DB_PATH", str(tmp_path / "vector_db"))
    monkeypatch.setenv("PDF_STORAGE_PATH", str(tmp_path / "papers"))
    monkeypatch.setenv("USE_MOCK_APIS", "true")
