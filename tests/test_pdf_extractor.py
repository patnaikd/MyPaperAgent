"""Tests for PDF text extraction."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.processing.pdf_extractor import (
    PDFExtractor,
    PDFExtractionError,
    extract_pdf_text,
    extract_pdf_metadata,
)


class TestPDFExtractor:
    """Test suite for PDF text extraction."""

    @pytest.fixture
    def pdf_extractor(self) -> PDFExtractor:
        """Create PDFExtractor instance."""
        return PDFExtractor()

    @pytest.fixture
    def sample_pdf_content(self) -> str:
        """Sample PDF text content."""
        return """Attention Is All You Need

Ashish Vaswani, Noam Shazeer, Niki Parmar

Google Brain

Abstract

The dominant sequence transduction models are based on complex recurrent or
convolutional neural networks that include an encoder and a decoder. The best
performing models also connect the encoder and decoder through an attention
mechanism. We propose a new simple network architecture, the Transformer,
based solely on attention mechanisms, dispensing with recurrence and convolutions
entirely.

arXiv:1706.03762v5 [cs.CL] 6 Dec 2017

DOI: 10.48550/arXiv.1706.03762

1 Introduction

The Transformer model architecture has revolutionized natural language processing...
"""

    def test_extractor_initialization(self, pdf_extractor: PDFExtractor) -> None:
        """Test PDFExtractor initialization."""
        assert pdf_extractor.min_text_threshold == 100
        assert pdf_extractor.config is not None

    def test_extractor_custom_threshold(self) -> None:
        """Test PDFExtractor with custom threshold."""
        extractor = PDFExtractor(min_text_threshold=500)
        assert extractor.min_text_threshold == 500

    def test_is_valid_pdf_with_valid_file(
        self, pdf_extractor: PDFExtractor, tmp_path: Path
    ) -> None:
        """Test PDF validation with a valid PDF."""
        # Create a minimal valid PDF
        pdf_path = tmp_path / "test.pdf"
        self._create_sample_pdf(pdf_path, "Test content")

        assert pdf_extractor._is_valid_pdf(pdf_path) is True

    def test_is_valid_pdf_with_invalid_file(
        self, pdf_extractor: PDFExtractor, tmp_path: Path
    ) -> None:
        """Test PDF validation with an invalid file."""
        # Create a non-PDF file
        invalid_path = tmp_path / "test.txt"
        invalid_path.write_text("Not a PDF")

        assert pdf_extractor._is_valid_pdf(invalid_path) is False

    def test_is_valid_pdf_with_nonexistent_file(
        self, pdf_extractor: PDFExtractor, tmp_path: Path
    ) -> None:
        """Test PDF validation with nonexistent file."""
        nonexistent = tmp_path / "nonexistent.pdf"
        assert pdf_extractor._is_valid_pdf(nonexistent) is False

    def test_extract_from_file_success(
        self, pdf_extractor: PDFExtractor, tmp_path: Path
    ) -> None:
        """Test successful PDF text extraction."""
        pdf_path = tmp_path / "test.pdf"
        content = "A" * 150  # Exceed min threshold
        self._create_sample_pdf(pdf_path, content)

        result = pdf_extractor.extract_from_file(pdf_path)

        assert "text" in result
        assert "metadata" in result
        assert "page_count" in result
        assert "extraction_method" in result
        assert len(result["text"]) >= pdf_extractor.min_text_threshold
        assert result["page_count"] >= 1

    def test_extract_from_file_not_found(self, pdf_extractor: PDFExtractor) -> None:
        """Test extraction from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            pdf_extractor.extract_from_file(Path("/nonexistent/file.pdf"))

    def test_extract_from_file_too_large(
        self, pdf_extractor: PDFExtractor, tmp_path: Path, monkeypatch
    ) -> None:
        """Test extraction fails for files exceeding size limit."""
        # Set a very small max size
        monkeypatch.setattr(pdf_extractor.config, "max_pdf_size_mb", 0.001)

        pdf_path = tmp_path / "large.pdf"
        self._create_sample_pdf(pdf_path, "A" * 10000)

        with pytest.raises(PDFExtractionError, match="too large"):
            pdf_extractor.extract_from_file(pdf_path)

    def test_clean_text(self, pdf_extractor: PDFExtractor) -> None:
        """Test text cleaning functionality."""
        dirty_text = """This   is   a   test.


Multiple newlines.



Hyphen-
ation test.

  Extra spaces.  """

        cleaned = pdf_extractor._clean_text(dirty_text)

        assert "  " not in cleaned  # No double spaces
        assert "\n\n\n" not in cleaned  # No triple newlines
        assert "Hyphen-\nation" not in cleaned  # Hyphenation removed
        assert cleaned.startswith("This")  # Leading whitespace removed
        assert cleaned.endswith(".")  # Trailing whitespace removed

    def test_extract_first_page_text(
        self, pdf_extractor: PDFExtractor, tmp_path: Path
    ) -> None:
        """Test extracting only first page."""
        pdf_path = tmp_path / "test.pdf"
        self._create_sample_pdf(pdf_path, "First page content")

        text = pdf_extractor.extract_first_page_text(pdf_path)

        assert len(text) > 0
        assert "First page" in text

    def test_extract_first_page_nonexistent(self, pdf_extractor: PDFExtractor) -> None:
        """Test first page extraction from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            pdf_extractor.extract_first_page_text(Path("/nonexistent.pdf"))

    def test_count_pages(self, pdf_extractor: PDFExtractor, tmp_path: Path) -> None:
        """Test page counting."""
        pdf_path = tmp_path / "test.pdf"
        self._create_sample_pdf(pdf_path, "Test content")

        page_count = pdf_extractor.count_pages(pdf_path)

        assert page_count >= 1

    def test_count_pages_nonexistent(self, pdf_extractor: PDFExtractor) -> None:
        """Test page counting with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            pdf_extractor.count_pages(Path("/nonexistent.pdf"))

    @patch("src.processing.pdf_extractor.image_to_string")
    def test_extract_with_ocr_fallback(
        self, mock_ocr: Mock, pdf_extractor: PDFExtractor, tmp_path: Path
    ) -> None:
        """Test OCR fallback when direct extraction yields too little text."""
        # Mock OCR to return meaningful text
        mock_ocr.return_value = "A" * 200  # Above threshold

        # Create PDF with minimal text (below threshold)
        pdf_path = tmp_path / "scanned.pdf"
        self._create_sample_pdf(pdf_path, "AB")  # Below threshold

        result = pdf_extractor.extract_from_file(pdf_path)

        assert result["extraction_method"] == "ocr"
        assert len(result["text"]) >= pdf_extractor.min_text_threshold

    def test_convenience_extract_pdf_text(self, tmp_path: Path) -> None:
        """Test convenience function for text extraction."""
        pdf_path = tmp_path / "test.pdf"
        self._create_sample_pdf(pdf_path, "A" * 150)

        text = extract_pdf_text(pdf_path)

        assert len(text) > 0

    def test_convenience_extract_pdf_metadata(self, tmp_path: Path) -> None:
        """Test convenience function for metadata extraction."""
        pdf_path = tmp_path / "test.pdf"
        self._create_sample_pdf(pdf_path, "A" * 150)

        metadata = extract_pdf_metadata(pdf_path)

        assert isinstance(metadata, dict)

    # Helper methods

    def _create_sample_pdf(self, pdf_path: Path, content: str) -> None:
        """Create a sample PDF file for testing.

        Args:
            pdf_path: Path where PDF should be created
            content: Text content for the PDF
        """
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), content)  # 1 inch margins
        doc.save(pdf_path)
        doc.close()


class TestPDFExtractionEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_pdf(self, tmp_path: Path) -> None:
        """Test handling of empty PDF."""
        import fitz

        pdf_path = tmp_path / "empty.pdf"
        doc = fitz.open()
        doc.new_page()  # Empty page
        doc.save(pdf_path)
        doc.close()

        extractor = PDFExtractor(min_text_threshold=1)
        result = extractor.extract_from_file(pdf_path)

        assert result["text"] == ""
        assert result["page_count"] == 1

    def test_invalid_pdf_format(self, tmp_path: Path) -> None:
        """Test handling of invalid PDF format."""
        pdf_path = tmp_path / "invalid.pdf"
        pdf_path.write_text("This is not a PDF")

        extractor = PDFExtractor()

        with pytest.raises(PDFExtractionError, match="Invalid PDF"):
            extractor.extract_from_file(pdf_path)

    def test_corrupted_pdf(self, tmp_path: Path) -> None:
        """Test handling of corrupted PDF."""
        pdf_path = tmp_path / "corrupted.pdf"
        # Write partial PDF header
        pdf_path.write_bytes(b"%PDF-1.4\n%corrupted")

        extractor = PDFExtractor()

        with pytest.raises(PDFExtractionError):
            extractor.extract_from_file(pdf_path)
