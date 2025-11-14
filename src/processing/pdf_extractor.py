"""PDF text and metadata extraction for academic papers."""
import logging
import re
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image
from pytesseract import image_to_string

from src.utils.config import get_config

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Raised when PDF extraction fails."""

    pass


class PDFExtractor:
    """Extract text and metadata from PDF files."""

    def __init__(self, min_text_threshold: int = 100):
        """Initialize PDF extractor.

        Args:
            min_text_threshold: Minimum number of characters to consider
                               text extraction successful (before falling back to OCR)
        """
        self.config = get_config()
        self.min_text_threshold = min_text_threshold

    def extract_from_file(self, pdf_path: Path) -> dict[str, any]:
        """Extract text and metadata from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing:
                - text: Extracted text content
                - metadata: PDF metadata (title, author, etc.)
                - page_count: Number of pages
                - extraction_method: 'text' or 'ocr'

        Raises:
            PDFExtractionError: If extraction fails
            FileNotFoundError: If PDF file doesn't exist
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Check file size
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config.max_pdf_size_mb:
            raise PDFExtractionError(
                f"PDF file too large: {file_size_mb:.2f}MB "
                f"(max: {self.config.max_pdf_size_mb}MB)"
            )

        # Validate PDF format
        if not self._is_valid_pdf(pdf_path):
            raise PDFExtractionError(f"Invalid PDF file: {pdf_path}")

        logger.info(f"Extracting content from PDF: {pdf_path}")

        try:
            # First attempt: Direct text extraction
            text, metadata, page_count = self._extract_text(pdf_path)

            # Check if extraction was successful
            if len(text.strip()) >= self.min_text_threshold:
                logger.info(
                    f"Successfully extracted {len(text)} characters "
                    f"from {page_count} pages using direct text extraction"
                )
                return {
                    "text": text,
                    "metadata": metadata,
                    "page_count": page_count,
                    "extraction_method": "text",
                }

            # Second attempt: OCR fallback
            logger.warning(
                f"Direct text extraction yielded only {len(text.strip())} characters. "
                "Falling back to OCR..."
            )
            text = self._extract_text_with_ocr(pdf_path)

            logger.info(
                f"Successfully extracted {len(text)} characters "
                f"from {page_count} pages using OCR"
            )
            return {
                "text": text,
                "metadata": metadata,
                "page_count": page_count,
                "extraction_method": "ocr",
            }

        except Exception as e:
            logger.error(f"Failed to extract content from PDF: {e}")
            raise PDFExtractionError(f"PDF extraction failed: {str(e)}") from e

    def _is_valid_pdf(self, pdf_path: Path) -> bool:
        """Check if file is a valid PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            True if valid PDF, False otherwise
        """
        try:
            with fitz.open(pdf_path) as doc:
                return doc.page_count > 0
        except Exception as e:
            logger.error(f"Invalid PDF file: {e}")
            return False

    def _extract_text(self, pdf_path: Path) -> tuple[str, dict, int]:
        """Extract text using PyMuPDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Tuple of (text, metadata, page_count)
        """
        text_parts = []
        metadata = {}

        with fitz.open(pdf_path) as doc:
            # Extract metadata
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
            }

            page_count = doc.page_count

            # Extract text from each page
            for page_num in range(page_count):
                page = doc[page_num]
                text = page.get_text("text")
                text_parts.append(text)

        # Combine all pages
        full_text = "\n\n".join(text_parts)

        # Clean up the text
        full_text = self._clean_text(full_text)

        return full_text, metadata, page_count

    def _extract_text_with_ocr(self, pdf_path: Path) -> str:
        """Extract text using OCR (for scanned PDFs).

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text
        """
        text_parts = []

        with fitz.open(pdf_path) as doc:
            for page_num in range(doc.page_count):
                logger.debug(f"Running OCR on page {page_num + 1}/{doc.page_count}")
                page = doc[page_num]

                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Run OCR
                try:
                    text = image_to_string(
                        img,
                        lang=self.config.ocr_language,
                        config=self.config.tesseract_path or "",
                    )
                    text_parts.append(text)
                except Exception as e:
                    logger.warning(f"OCR failed on page {page_num + 1}: {e}")
                    continue

        # Combine all pages
        full_text = "\n\n".join(text_parts)

        # Clean up the text
        full_text = self._clean_text(full_text)

        return full_text

    def _clean_text(self, text: str) -> str:
        """Clean extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove multiple spaces
        text = re.sub(r" {2,}", " ", text)

        # Remove hyphenation at line breaks
        text = re.sub(r"-\n", "", text)

        # Strip whitespace
        text = text.strip()

        return text

    def extract_first_page_text(self, pdf_path: Path) -> str:
        """Extract text from the first page only.

        Useful for getting abstract and initial metadata.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Text from first page
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        with fitz.open(pdf_path) as doc:
            if doc.page_count == 0:
                return ""

            first_page = doc[0]
            text = first_page.get_text("text")
            return self._clean_text(text)

    def count_pages(self, pdf_path: Path) -> int:
        """Count the number of pages in a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Number of pages
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        with fitz.open(pdf_path) as doc:
            return doc.page_count


def extract_pdf_text(pdf_path: Path, use_ocr: bool = False) -> str:
    """Convenience function to extract text from a PDF.

    Args:
        pdf_path: Path to the PDF file
        use_ocr: Force OCR extraction

    Returns:
        Extracted text

    Raises:
        PDFExtractionError: If extraction fails
    """
    extractor = PDFExtractor()

    if use_ocr:
        return extractor._extract_text_with_ocr(pdf_path)

    result = extractor.extract_from_file(pdf_path)
    return result["text"]


def extract_pdf_metadata(pdf_path: Path) -> dict[str, str]:
    """Convenience function to extract metadata from a PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary of metadata

    Raises:
        PDFExtractionError: If extraction fails
    """
    extractor = PDFExtractor()
    result = extractor.extract_from_file(pdf_path)
    return result["metadata"]
