"""Configuration management for MyPaperAgent."""
import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    # API Keys
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    voyage_api_key: Optional[str] = Field(None, env="VOYAGE_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    semantic_scholar_api_key: Optional[str] = Field(None, env="SEMANTIC_SCHOLAR_API_KEY")

    # Database
    database_path: Path = Field(
        default=Path("data/database/papers.db"), env="DATABASE_PATH"
    )
    vector_db_path: Path = Field(default=Path("data/vector_db"), env="VECTOR_DB_PATH")

    # PDF Storage
    pdf_storage_path: Path = Field(default=Path("data/papers"), env="PDF_STORAGE_PATH")
    max_pdf_size_mb: int = Field(default=50, env="MAX_PDF_SIZE_MB")

    # RAG Configuration
    embedding_model: str = Field(default="voyage-2", env="EMBEDDING_MODEL")
    chunk_size: int = Field(default=800, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, env="CHUNK_OVERLAP")
    top_k_results: int = Field(default=5, env="TOP_K_RESULTS")

    # OCR Settings
    tesseract_path: Optional[str] = Field(None, env="TESSERACT_PATH")
    ocr_language: str = Field(default="eng", env="OCR_LANGUAGE")

    # API Rate Limiting
    anthropic_max_retries: int = Field(default=3, env="ANTHROPIC_MAX_RETRIES")
    api_retry_delay: int = Field(default=1, env="API_RETRY_DELAY")
    api_timeout: int = Field(default=60, env="API_TIMEOUT")

    # Quiz Settings
    default_quiz_length: int = Field(default=10, env="DEFAULT_QUIZ_LENGTH")
    quiz_difficulty: Literal["easy", "medium", "hard", "adaptive"] = Field(
        default="adaptive", env="QUIZ_DIFFICULTY"
    )

    # Paper Discovery
    default_search_limit: int = Field(default=10, env="DEFAULT_SEARCH_LIMIT")
    arxiv_max_results: int = Field(default=50, env="ARXIV_MAX_RESULTS")
    semantic_scholar_max_results: int = Field(
        default=50, env="SEMANTIC_SCHOLAR_MAX_RESULTS"
    )

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Path = Field(default=Path("logs/mypaperagent.log"), env="LOG_FILE")

    # Debug Mode
    debug: bool = Field(default=False, env="DEBUG")

    # Testing
    test_database_path: str = Field(default=":memory:", env="TEST_DATABASE_PATH")
    use_mock_apis: bool = Field(default=False, env="USE_MOCK_APIS")

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def validate_api_keys(self) -> None:
        """Validate that required API keys are present."""
        if not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Get your key at https://console.anthropic.com/"
            )

        if not self.voyage_api_key and not self.openai_api_key:
            raise ValueError(
                "Either VOYAGE_API_KEY or OPENAI_API_KEY is required for embeddings. "
                "Get Voyage key at https://dash.voyageai.com/ or "
                "OpenAI key at https://platform.openai.com/"
            )

    def get_embedding_provider(self) -> Literal["voyage", "openai"]:
        """Determine which embedding provider to use."""
        if self.voyage_api_key:
            return "voyage"
        elif self.openai_api_key:
            return "openai"
        else:
            raise ValueError("No embedding provider API key found")

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        self.pdf_storage_path.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
        _config.validate_api_keys()
        _config.ensure_directories()
    return _config


def reset_config() -> None:
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None


# Convenience function for getting specific settings
def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a specific setting from environment or config."""
    return os.getenv(key, default)
