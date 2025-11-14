"""Tests for configuration management."""
import os
from pathlib import Path

import pytest

from src.utils.config import Config, get_config, reset_config


class TestConfig:
    """Test suite for configuration management."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_config()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_config()

    def test_config_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that configuration has sensible defaults."""
        # Set required API keys for testing
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")

        config = Config()

        assert config.chunk_size == 800
        assert config.chunk_overlap == 100
        assert config.max_pdf_size_mb == 50
        assert config.embedding_model == "voyage-2"
        assert config.default_quiz_length == 10

    def test_config_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
        monkeypatch.setenv("CHUNK_SIZE", "1000")
        monkeypatch.setenv("MAX_PDF_SIZE_MB", "100")

        config = Config()

        assert config.anthropic_api_key == "test-anthropic-key"
        assert config.voyage_api_key == "test-voyage-key"
        assert config.chunk_size == 1000
        assert config.max_pdf_size_mb == 100

    def test_validate_api_keys_missing_anthropic(self) -> None:
        """Test that missing Anthropic API key raises error."""
        config = Config(
            anthropic_api_key="",
            voyage_api_key="test-key"
        )

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            config.validate_api_keys()

    def test_validate_api_keys_missing_embedding_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing embedding provider raises error."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = Config(anthropic_api_key="test-key")

        with pytest.raises(ValueError, match="Either VOYAGE_API_KEY or OPENAI_API_KEY"):
            config.validate_api_keys()

    def test_get_embedding_provider_voyage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test embedding provider detection for Voyage."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")

        config = Config()
        assert config.get_embedding_provider() == "voyage"

    def test_get_embedding_provider_openai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test embedding provider detection for OpenAI."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

        config = Config()
        assert config.get_embedding_provider() == "openai"

    def test_get_embedding_provider_prefers_voyage(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that Voyage is preferred when both are available."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

        config = Config()
        assert config.get_embedding_provider() == "voyage"

    def test_ensure_directories_creates_paths(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that ensure_directories creates required paths."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")

        db_path = tmp_path / "test_db" / "papers.db"
        vector_path = tmp_path / "test_vector"
        pdf_path = tmp_path / "test_pdfs"
        log_path = tmp_path / "logs" / "app.log"

        config = Config(
            database_path=db_path,
            vector_db_path=vector_path,
            pdf_storage_path=pdf_path,
            log_file=log_path,
        )

        config.ensure_directories()

        assert db_path.parent.exists()
        assert vector_path.exists()
        assert pdf_path.exists()
        assert log_path.parent.exists()

    def test_get_config_singleton(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that get_config returns the same instance."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2
