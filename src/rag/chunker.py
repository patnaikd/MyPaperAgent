"""Text chunking utilities for RAG system."""
import logging
import re
from typing import Optional

import tiktoken

from src.utils.config import get_config

logger = logging.getLogger(__name__)


class TextChunker:
    """Chunk text for embedding and retrieval."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        encoding_name: str = "cl100k_base",
    ):
        """Initialize text chunker.

        Args:
            chunk_size: Size of chunks in tokens. Defaults to config.
            chunk_overlap: Overlap between chunks in tokens. Defaults to config.
            encoding_name: Tiktoken encoding to use for token counting
        """
        config = get_config()
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

    def chunk_text(
        self, text: str, metadata: Optional[dict] = None
    ) -> list[dict[str, any]]:
        """Chunk text into smaller pieces with metadata.

        Uses semantic chunking based on paragraphs when possible,
        falling back to fixed-size chunking for very long paragraphs.
        Limits chunks to 1-2 paragraphs for tighter retrieval granularity.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with text, metadata, and token count
        """
        logger.info(f"Chunking text of length {len(text)} characters")

        # Split into paragraphs
        paragraphs = self._split_into_paragraphs(text)

        chunks = []
        current_chunk = []
        current_tokens = 0
        max_paragraphs = 2

        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)

            # If single paragraph exceeds chunk size, split it further
            if para_tokens > self.chunk_size:
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))
                    current_chunk = []
                    current_tokens = 0

                # Split large paragraph
                sub_chunks = self._chunk_by_tokens(paragraph)
                for sub_chunk in sub_chunks:
                    chunks.append(self._create_chunk(sub_chunk, len(chunks), metadata))
                continue

            # If adding paragraph would exceed size, save current chunk
            if current_chunk and (
                current_tokens + para_tokens > self.chunk_size
                or len(current_chunk) >= max_paragraphs
            ):
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))

                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Keep last paragraph(s) for overlap
                    overlap_text = current_chunk[-1] if current_chunk else ""
                    overlap_tokens = self._count_tokens(overlap_text)

                    if (
                        overlap_tokens <= self.chunk_overlap
                        and overlap_tokens + para_tokens <= self.chunk_size
                    ):
                        current_chunk = [overlap_text]
                        current_tokens = overlap_tokens
                    else:
                        current_chunk = []
                        current_tokens = 0
                else:
                    current_chunk = []
                    current_tokens = 0

            # Add paragraph to current chunk
            current_chunk.append(paragraph)
            current_tokens += para_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))

        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs.

        Args:
            text: Text to split

        Returns:
            List of paragraphs
        """
        # Split on double newlines (paragraphs)
        paragraphs = re.split(r"\n\s*\n", text)

        # Filter out empty paragraphs and strip whitespace
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _chunk_by_tokens(self, text: str) -> list[str]:
        """Chunk text by token count (for very long paragraphs).

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            # If single sentence exceeds chunk size, split it forcefully
            if sentence_tokens > self.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split by words
                words = sentence.split()
                temp_chunk = []
                temp_tokens = 0

                for word in words:
                    word_tokens = self._count_tokens(word)
                    if temp_tokens + word_tokens > self.chunk_size:
                        if temp_chunk:
                            chunks.append(" ".join(temp_chunk))
                        temp_chunk = [word]
                        temp_tokens = word_tokens
                    else:
                        temp_chunk.append(word)
                        temp_tokens += word_tokens

                if temp_chunk:
                    chunks.append(" ".join(temp_chunk))

            # If adding sentence would exceed size, save current chunk
            elif current_tokens + sentence_tokens > self.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens

            # Add sentence to current chunk
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def _create_chunk(
        self, text: str, index: int, metadata: Optional[dict] = None
    ) -> dict[str, any]:
        """Create a chunk dictionary.

        Args:
            text: Chunk text
            index: Chunk index
            metadata: Optional metadata

        Returns:
            Chunk dictionary
        """
        chunk = {
            "text": text,
            "index": index,
            "token_count": self._count_tokens(text),
            "metadata": metadata or {},
        }

        return chunk


def chunk_paper_text(
    text: str,
    paper_id: int,
    title: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[dict[str, any]]:
    """Convenience function to chunk paper text.

    Args:
        text: Paper text
        paper_id: Paper ID
        title: Optional paper title
        chunk_size: Optional chunk size
        chunk_overlap: Optional chunk overlap

    Returns:
        List of chunks with metadata
    """
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    metadata = {"paper_id": paper_id}
    if title:
        metadata["title"] = title

    return chunker.chunk_text(text, metadata=metadata)
