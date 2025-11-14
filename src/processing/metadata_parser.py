"""Parse academic paper metadata from text."""
import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class MetadataParser:
    """Extract academic paper metadata from text."""

    # Common patterns for academic metadata
    DOI_PATTERN = r"10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+"
    ARXIV_PATTERN = r"arXiv:(\d{4}\.\d{4,5})(v\d+)?"
    YEAR_PATTERN = r"\b(19|20)\d{2}\b"

    # Date patterns
    DATE_PATTERNS = [
        r"(\d{4})-(\d{2})-(\d{2})",  # YYYY-MM-DD
        r"(\d{2})/(\d{2})/(\d{4})",  # MM/DD/YYYY
        r"(\w+)\s+(\d{1,2}),\s+(\d{4})",  # Month DD, YYYY
    ]

    def parse_metadata(self, text: str, pdf_metadata: dict = None) -> dict:
        """Parse metadata from paper text.

        Args:
            text: Full text or first page text
            pdf_metadata: Optional PDF metadata from file

        Returns:
            Dictionary with parsed metadata
        """
        metadata = {
            "title": None,
            "authors": None,
            "abstract": None,
            "doi": None,
            "arxiv_id": None,
            "year": None,
            "publication_date": None,
            "journal": None,
            "keywords": None,
        }

        # Use PDF metadata as fallback
        if pdf_metadata:
            metadata["title"] = pdf_metadata.get("title") or metadata["title"]
            metadata["authors"] = pdf_metadata.get("author") or metadata["authors"]
            metadata["keywords"] = pdf_metadata.get("keywords") or metadata["keywords"]

        # Extract from text
        metadata["doi"] = self.extract_doi(text)
        metadata["arxiv_id"] = self.extract_arxiv_id(text)
        metadata["year"] = self.extract_year(text)
        metadata["abstract"] = self.extract_abstract(text)

        # If title not in PDF metadata, try to extract from text
        if not metadata["title"]:
            metadata["title"] = self.extract_title(text)

        # If authors not in PDF metadata, try to extract from text
        if not metadata["authors"]:
            metadata["authors"] = self.extract_authors(text)

        # Extract journal name
        metadata["journal"] = self.extract_journal(text)

        return metadata

    def extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text.

        Args:
            text: Text to search

        Returns:
            DOI string or None
        """
        # Look in first 2000 characters (usually on first page)
        search_text = text[:2000]

        match = re.search(self.DOI_PATTERN, search_text, re.IGNORECASE)
        if match:
            doi = match.group(0)
            # Clean up common artifacts
            doi = doi.rstrip(".,;)")
            logger.debug(f"Extracted DOI: {doi}")
            return doi

        return None

    def extract_arxiv_id(self, text: str) -> Optional[str]:
        """Extract arXiv ID from text.

        Args:
            text: Text to search

        Returns:
            arXiv ID or None
        """
        # Look in first 2000 characters
        search_text = text[:2000]

        match = re.search(self.ARXIV_PATTERN, search_text, re.IGNORECASE)
        if match:
            arxiv_id = match.group(1)  # Just the ID, not version
            logger.debug(f"Extracted arXiv ID: {arxiv_id}")
            return arxiv_id

        return None

    def extract_year(self, text: str) -> Optional[int]:
        """Extract publication year from text.

        Args:
            text: Text to search

        Returns:
            Year as integer or None
        """
        # Look in first 2000 characters
        search_text = text[:2000]

        # Find all years
        years = re.findall(self.YEAR_PATTERN, search_text)

        if years:
            # Convert to integers
            years_int = [int(y) for y in years]

            # Filter to reasonable range (papers from 1950-current year + 1)
            current_year = datetime.now().year
            valid_years = [y for y in years_int if 1950 <= y <= current_year + 1]

            if valid_years:
                # Return the most common year (likely publication year)
                year = max(set(valid_years), key=valid_years.count)
                logger.debug(f"Extracted year: {year}")
                return year

        return None

    def extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from paper text.

        Args:
            text: Full text or first few pages

        Returns:
            Abstract text or None
        """
        # Look in first 3000 characters
        search_text = text[:3000]

        # Common abstract patterns
        patterns = [
            r"Abstract\s*[:\-—]?\s*\n(.+?)(?:\n\n|\nIntroduction|\n1\.)",
            r"ABSTRACT\s*[:\-—]?\s*\n(.+?)(?:\n\n|\nINTRODUCTION|\n1\.)",
            r"Summary\s*[:\-—]?\s*\n(.+?)(?:\n\n|\nIntroduction|\n1\.)",
        ]

        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up
                abstract = re.sub(r"\s+", " ", abstract)
                if len(abstract) > 50:  # Minimum reasonable abstract length
                    logger.debug(f"Extracted abstract: {abstract[:100]}...")
                    return abstract

        return None

    def extract_title(self, text: str) -> Optional[str]:
        """Extract title from paper text.

        This is a heuristic approach - the title is usually one of the
        first lines, often in title case or all caps.

        Args:
            text: Text to search

        Returns:
            Title or None
        """
        # Look at first 1000 characters
        lines = text[:1000].split("\n")

        # Filter out very short lines and common headers
        candidates = []
        skip_patterns = [
            r"^(page|\d+|abstract|introduction|arxiv|doi|http)",
        ]

        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()

            # Skip if too short or too long
            if len(line) < 10 or len(line) > 200:
                continue

            # Skip if matches skip patterns
            if any(re.match(p, line, re.IGNORECASE) for p in skip_patterns):
                continue

            # Skip if mostly punctuation or numbers
            if sum(c.isalnum() for c in line) / len(line) < 0.6:
                continue

            candidates.append(line)

        # Return the first reasonable candidate
        if candidates:
            title = candidates[0]
            logger.debug(f"Extracted title: {title}")
            return title

        return None

    def extract_authors(self, text: str) -> Optional[str]:
        """Extract authors from paper text.

        Args:
            text: Text to search

        Returns:
            Comma-separated author names or None
        """
        # Look in first 1500 characters
        search_text = text[:1500]

        # Common patterns for author lists
        patterns = [
            r"Authors?:\s*(.+?)(?:\n\n|\nAbstract)",
            r"By\s+(.+?)(?:\n\n|\nAbstract)",
        ]

        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE | re.DOTALL)
            if match:
                authors = match.group(1).strip()
                # Clean up
                authors = re.sub(r"\s+", " ", authors)
                authors = re.sub(r"\n", ", ", authors)

                if len(authors) < 200:  # Reasonable author list length
                    logger.debug(f"Extracted authors: {authors}")
                    return authors

        # Heuristic: Look for lines with multiple capitalized names
        lines = search_text.split("\n")
        for line in lines[1:10]:  # Skip first line (likely title), check next 9
            # Check if line looks like author names
            # Pattern: "Firstname Lastname, Firstname Lastname"
            if re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+,?\s*){2,}", line):
                authors = line.strip()
                if 10 < len(authors) < 200:
                    logger.debug(f"Extracted authors (heuristic): {authors}")
                    return authors

        return None

    def extract_journal(self, text: str) -> Optional[str]:
        """Extract journal/conference name from text.

        Args:
            text: Text to search

        Returns:
            Journal name or None
        """
        # Look in first 2000 characters
        search_text = text[:2000]

        # Common journal/conference patterns
        patterns = [
            r"(?:Published in|Appeared in|In)\s+([A-Z][^.\n]{10,100})",
            r"(?:Journal|Conference):\s*([^\n]{10,100})",
            r"Proceedings of (?:the\s+)?([^\n]{10,100})",
        ]

        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                journal = match.group(1).strip()
                # Clean up
                journal = re.sub(r"\s+", " ", journal)
                journal = journal.rstrip(".,;")

                if len(journal) < 150:  # Reasonable journal name length
                    logger.debug(f"Extracted journal: {journal}")
                    return journal

        return None

    def clean_author_names(self, authors: str) -> list[str]:
        """Parse and clean author names.

        Args:
            authors: Raw author string

        Returns:
            List of cleaned author names
        """
        # Split by common delimiters
        author_list = re.split(r",|;|\band\b", authors)

        # Clean each name
        cleaned = []
        for name in author_list:
            name = name.strip()
            # Remove superscript numbers and other artifacts
            name = re.sub(r"[\d\*†‡§¶]", "", name)
            # Remove extra whitespace
            name = re.sub(r"\s+", " ", name)
            name = name.strip()

            if len(name) > 2:  # Minimum name length
                cleaned.append(name)

        return cleaned


def parse_paper_metadata(text: str, pdf_metadata: dict = None) -> dict:
    """Convenience function to parse paper metadata.

    Args:
        text: Paper text
        pdf_metadata: Optional PDF metadata

    Returns:
        Parsed metadata dictionary
    """
    parser = MetadataParser()
    return parser.parse_metadata(text, pdf_metadata)
