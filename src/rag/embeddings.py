"""Embedding generation for RAG system."""
import logging
from typing import Literal, Optional

import openai
import voyageai

from src.utils.config import get_config

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Base exception for embedding errors."""

    pass


class EmbeddingGenerator:
    """Generate embeddings for text using Voyage AI or OpenAI."""

    def __init__(
        self, provider: Optional[Literal["voyage", "openai"]] = None, model: Optional[str] = None
    ):
        """Initialize embedding generator.

        Args:
            provider: Embedding provider (voyage or openai). Auto-detected if not provided.
            model: Model name. Uses config default if not provided.

        Raises:
            EmbeddingError: If provider cannot be initialized
        """
        self.config = get_config()

        # Auto-detect provider if not specified
        if provider is None:
            provider = self.config.get_embedding_provider()

        self.provider = provider

        # Set model
        if model:
            self.model = model
        else:
            if self.provider == "voyage":
                self.model = self.config.embedding_model or "voyage-2"
            else:  # openai
                self.model = self.config.embedding_model or "text-embedding-3-small"

        # Initialize client
        try:
            if self.provider == "voyage":
                self.client = voyageai.Client(api_key=self.config.voyage_api_key)
            else:  # openai
                self.client = openai.OpenAI(api_key=self.config.openai_api_key)

            logger.info(f"Initialized {self.provider} embedding generator with model {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize embedding provider: {e}")
            raise EmbeddingError(f"Failed to initialize {self.provider}: {str(e)}") from e

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []

        try:
            logger.info(f"Generating embeddings for {len(texts)} texts using {self.provider}")

            if self.provider == "voyage":
                result = self.client.embed(texts, model=self.model, input_type="document")
                embeddings = result.embeddings

            else:  # openai
                result = self.client.embeddings.create(input=texts, model=self.model)
                embeddings = [item.embedding for item in result.data]

            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise EmbeddingError(f"Failed to generate embeddings: {str(e)}") from e

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query.

        Uses query-specific optimizations when available.

        Args:
            query: Search query

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            logger.info(f"Generating query embedding using {self.provider}")

            if self.provider == "voyage":
                # Voyage supports query-specific embeddings
                result = self.client.embed([query], model=self.model, input_type="query")
                embedding = result.embeddings[0]

            else:  # openai
                # OpenAI doesn't have query-specific mode
                embedding = self.embed_text(query)

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise EmbeddingError(f"Failed to generate query embedding: {str(e)}") from e

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for this model.

        Returns:
            Embedding dimension
        """
        # Common dimensions for known models
        dimensions = {
            "voyage-2": 1024,
            "voyage-large-2": 1536,
            "voyage-code-2": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        return dimensions.get(self.model, 1536)  # Default to 1536


def generate_embeddings(
    texts: list[str],
    provider: Optional[Literal["voyage", "openai"]] = None,
    model: Optional[str] = None,
) -> list[list[float]]:
    """Convenience function to generate embeddings.

    Args:
        texts: List of texts to embed
        provider: Optional embedding provider
        model: Optional model name

    Returns:
        List of embedding vectors

    Raises:
        EmbeddingError: If embedding generation fails
    """
    generator = EmbeddingGenerator(provider=provider, model=model)
    return generator.embed_batch(texts)


def generate_query_embedding(
    query: str,
    provider: Optional[Literal["voyage", "openai"]] = None,
    model: Optional[str] = None,
) -> list[float]:
    """Convenience function to generate a query embedding.

    Args:
        query: Search query
        provider: Optional embedding provider
        model: Optional model name

    Returns:
        Embedding vector

    Raises:
        EmbeddingError: If embedding generation fails
    """
    generator = EmbeddingGenerator(provider=provider, model=model)
    return generator.embed_query(query)
