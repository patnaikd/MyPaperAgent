"""Tests for academic paper metadata parsing."""
import pytest

from src.processing.metadata_parser import (
    MetadataParser,
    parse_paper_metadata,
)


class TestMetadataParser:
    """Test suite for metadata parsing."""

    @pytest.fixture
    def parser(self) -> MetadataParser:
        """Create MetadataParser instance."""
        return MetadataParser()

    @pytest.fixture
    def sample_paper_text(self) -> str:
        """Sample academic paper text."""
        return """Attention Is All You Need

Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit

Google Brain, Google Research

Abstract

The dominant sequence transduction models are based on complex recurrent or
convolutional neural networks that include an encoder and a decoder. The best
performing models also connect the encoder and decoder through an attention
mechanism. We propose a new simple network architecture, the Transformer,
based solely on attention mechanisms, dispensing with recurrence and convolutions
entirely. Experiments on two machine translation tasks show these models to be
superior in quality while being more parallelizable and requiring significantly
less time to train.

arXiv:1706.03762v5 [cs.CL] 6 Dec 2017

DOI: 10.48550/arXiv.1706.03762

Published in Advances in Neural Information Processing Systems (NeurIPS) 2017

1. Introduction

The Transformer model architecture has revolutionized natural language processing
and has become the foundation for many modern language models.
"""

    def test_parser_initialization(self, parser: MetadataParser) -> None:
        """Test parser initialization."""
        assert parser is not None
        assert parser.DOI_PATTERN is not None
        assert parser.ARXIV_PATTERN is not None

    def test_extract_doi(self, parser: MetadataParser, sample_paper_text: str) -> None:
        """Test DOI extraction."""
        doi = parser.extract_doi(sample_paper_text)

        assert doi is not None
        assert doi == "10.48550/arXiv.1706.03762"

    def test_extract_doi_not_found(self, parser: MetadataParser) -> None:
        """Test DOI extraction when not present."""
        text = "This paper has no DOI."
        doi = parser.extract_doi(text)

        assert doi is None

    def test_extract_doi_with_trailing_punctuation(self, parser: MetadataParser) -> None:
        """Test DOI extraction removes trailing punctuation."""
        text = "DOI: 10.1234/example.2023.,;"
        doi = parser.extract_doi(text)

        assert doi == "10.1234/example.2023"

    def test_extract_arxiv_id(
        self, parser: MetadataParser, sample_paper_text: str
    ) -> None:
        """Test arXiv ID extraction."""
        arxiv_id = parser.extract_arxiv_id(sample_paper_text)

        assert arxiv_id is not None
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_with_version(self, parser: MetadataParser) -> None:
        """Test arXiv ID extraction with version number."""
        text = "arXiv:2301.12345v3 [cs.AI]"
        arxiv_id = parser.extract_arxiv_id(text)

        assert arxiv_id == "2301.12345"

    def test_extract_arxiv_id_not_found(self, parser: MetadataParser) -> None:
        """Test arXiv ID extraction when not present."""
        text = "This paper has no arXiv ID."
        arxiv_id = parser.extract_arxiv_id(text)

        assert arxiv_id is None

    def test_extract_year(self, parser: MetadataParser, sample_paper_text: str) -> None:
        """Test year extraction."""
        year = parser.extract_year(sample_paper_text)

        assert year is not None
        assert year == 2017

    def test_extract_year_filters_invalid(self, parser: MetadataParser) -> None:
        """Test year extraction filters out invalid years."""
        text = "Published in 1234 and updated in 2023"
        year = parser.extract_year(text)

        assert year == 2023  # 1234 should be filtered out

    def test_extract_year_not_found(self, parser: MetadataParser) -> None:
        """Test year extraction when not present."""
        text = "No year here."
        year = parser.extract_year(text)

        assert year is None

    def test_extract_abstract(
        self, parser: MetadataParser, sample_paper_text: str
    ) -> None:
        """Test abstract extraction."""
        abstract = parser.extract_abstract(sample_paper_text)

        assert abstract is not None
        assert "dominant sequence transduction" in abstract
        assert "Transformer" in abstract
        assert len(abstract) > 50

    def test_extract_abstract_uppercase(self, parser: MetadataParser) -> None:
        """Test abstract extraction with uppercase header."""
        text = """Title Here

ABSTRACT

This is the abstract content with some meaningful text.

INTRODUCTION

This is the introduction.
"""
        abstract = parser.extract_abstract(text)

        assert abstract is not None
        assert "abstract content" in abstract.lower()

    def test_extract_abstract_not_found(self, parser: MetadataParser) -> None:
        """Test abstract extraction when not present."""
        text = "No abstract in this text."
        abstract = parser.extract_abstract(text)

        assert abstract is None

    def test_extract_title(
        self, parser: MetadataParser, sample_paper_text: str
    ) -> None:
        """Test title extraction."""
        title = parser.extract_title(sample_paper_text)

        assert title is not None
        assert "Attention" in title
        assert len(title) >= 10

    def test_extract_title_filters_short_lines(self, parser: MetadataParser) -> None:
        """Test title extraction filters out very short lines."""
        text = """Page 1

Short

This is the Real Title of the Paper

Authors here
"""
        title = parser.extract_title(text)

        assert title == "This is the Real Title of the Paper"

    def test_extract_authors(
        self, parser: MetadataParser, sample_paper_text: str
    ) -> None:
        """Test author extraction."""
        authors = parser.extract_authors(sample_paper_text)

        assert authors is not None
        assert "Vaswani" in authors
        assert "Shazeer" in authors

    def test_extract_authors_with_by_pattern(self, parser: MetadataParser) -> None:
        """Test author extraction with 'By' pattern."""
        text = """The Title

By John Doe, Jane Smith

Abstract

Content here.
"""
        authors = parser.extract_authors(text)

        assert authors is not None
        assert "John Doe" in authors
        assert "Jane Smith" in authors

    def test_extract_authors_not_found(self, parser: MetadataParser) -> None:
        """Test author extraction when not found."""
        text = "No clear author pattern here."
        authors = parser.extract_authors(text)

        # May be None or may use heuristic - both acceptable
        # Just ensure it doesn't crash
        assert isinstance(authors, (str, type(None)))

    def test_extract_journal(
        self, parser: MetadataParser, sample_paper_text: str
    ) -> None:
        """Test journal extraction."""
        journal = parser.extract_journal(sample_paper_text)

        assert journal is not None
        assert "Neural Information Processing Systems" in journal or "NeurIPS" in journal

    def test_extract_journal_proceedings(self, parser: MetadataParser) -> None:
        """Test journal extraction from proceedings."""
        text = "Proceedings of the 2023 Conference on Computer Vision"
        journal = parser.extract_journal(text)

        assert journal is not None
        assert "Computer Vision" in journal

    def test_extract_journal_not_found(self, parser: MetadataParser) -> None:
        """Test journal extraction when not present."""
        text = "No journal information here."
        journal = parser.extract_journal(text)

        assert journal is None

    def test_parse_metadata_complete(
        self, parser: MetadataParser, sample_paper_text: str
    ) -> None:
        """Test complete metadata parsing."""
        metadata = parser.parse_metadata(sample_paper_text)

        assert metadata is not None
        assert metadata["title"] is not None
        assert metadata["authors"] is not None
        assert metadata["abstract"] is not None
        assert metadata["doi"] is not None
        assert metadata["arxiv_id"] is not None
        assert metadata["year"] is not None

    def test_parse_metadata_with_pdf_metadata(self, parser: MetadataParser) -> None:
        """Test metadata parsing with PDF metadata fallback."""
        text = "Basic text without much metadata."
        pdf_metadata = {
            "title": "PDF Title",
            "author": "PDF Author",
            "keywords": "machine learning, AI",
        }

        metadata = parser.parse_metadata(text, pdf_metadata)

        assert metadata["title"] == "PDF Title"
        assert metadata["authors"] == "PDF Author"
        assert metadata["keywords"] == "machine learning, AI"

    def test_parse_metadata_prefers_text_over_pdf(
        self, parser: MetadataParser, sample_paper_text: str
    ) -> None:
        """Test that text metadata is preferred over PDF metadata when both exist."""
        pdf_metadata = {
            "title": "Wrong Title from PDF",
        }

        metadata = parser.parse_metadata(sample_paper_text, pdf_metadata)

        # Text extraction should find the real title
        assert "Attention" in metadata["title"]

    def test_clean_author_names(self, parser: MetadataParser) -> None:
        """Test author name cleaning."""
        raw_authors = "John Doe¹, Jane Smith²; Bob Johnson* and Alice Williams†"

        cleaned = parser.clean_author_names(raw_authors)

        assert len(cleaned) == 4
        assert "John Doe" in cleaned
        assert "Jane Smith" in cleaned
        assert "Bob Johnson" in cleaned
        assert "Alice Williams" in cleaned

        # Check that superscripts are removed
        for name in cleaned:
            assert not any(c.isdigit() for c in name)
            assert "¹" not in name
            assert "*" not in name

    def test_clean_author_names_filters_short(self, parser: MetadataParser) -> None:
        """Test that very short 'names' are filtered out."""
        raw_authors = "John Doe, X, Jane Smith, A, B"

        cleaned = parser.clean_author_names(raw_authors)

        assert "John Doe" in cleaned
        assert "Jane Smith" in cleaned
        assert "X" not in cleaned  # Too short
        assert len(cleaned) == 2

    def test_convenience_function(self, sample_paper_text: str) -> None:
        """Test convenience function for metadata parsing."""
        metadata = parse_paper_metadata(sample_paper_text)

        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert "authors" in metadata
        assert "abstract" in metadata


class TestMetadataParserEdgeCases:
    """Test edge cases for metadata parsing."""

    @pytest.fixture
    def parser(self) -> MetadataParser:
        """Create parser instance."""
        return MetadataParser()

    def test_empty_text(self, parser: MetadataParser) -> None:
        """Test parsing empty text."""
        metadata = parser.parse_metadata("")

        assert isinstance(metadata, dict)
        # All fields should be None
        assert metadata["doi"] is None
        assert metadata["arxiv_id"] is None

    def test_malformed_doi(self, parser: MetadataParser) -> None:
        """Test handling of malformed DOI."""
        text = "DOI: not-a-real-doi"
        doi = parser.extract_doi(text)

        assert doi is None

    def test_very_long_abstract(self, parser: MetadataParser) -> None:
        """Test extraction of very long abstract."""
        abstract_text = "A" * 5000
        text = f"Abstract\n\n{abstract_text}\n\nIntroduction"

        abstract = parser.extract_abstract(text)

        assert abstract is not None
        assert len(abstract) > 1000

    def test_multiple_years(self, parser: MetadataParser) -> None:
        """Test year extraction with multiple years in text."""
        text = "Published in 2020, revised in 2021, cited paper from 2019"
        year = parser.extract_year(text)

        # Should pick the most common or first reasonable year
        assert year in [2019, 2020, 2021]

    def test_unicode_in_authors(self, parser: MetadataParser) -> None:
        """Test author extraction with unicode characters."""
        text = "Authors: José García, François Müller, 李明"

        authors = parser.extract_authors(text)

        # Should handle unicode gracefully
        if authors:
            assert isinstance(authors, str)
