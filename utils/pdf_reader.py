"""
utils/pdf_reader.py
--------------------
Extracts clean text from PDF files.

Primary:  pdfplumber  -- better layout, table support, multi-column handling
Fallback: pypdf       -- used only if pdfplumber fails for any reason

Both are listed in requirements.txt so both are always available.
"""

import re
import os


class PDFReader:
    """
    Reads a PDF file and returns clean extracted text
    ready to feed into the NLP chunking pipeline.

    Uses pdfplumber as the primary extractor (better accuracy),
    falls back to pypdf automatically if pdfplumber fails.
    """

    def __init__(self):
        pass

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract all text from a PDF file.

        Args:
            pdf_path: Path to the .pdf file.

        Returns:
            Cleaned plain text string.

        Raises:
            FileNotFoundError: If the PDF path does not exist.
            ValueError:        If the PDF has no extractable text (scanned image PDF).
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if not pdf_path.lower().endswith(".pdf"):
            raise ValueError(f"File is not a PDF: {pdf_path}")

        # Step 1: Try pdfplumber first (primary -- better quality)
        text = self._extract_with_pdfplumber(pdf_path)

        # Step 2: Fall back to pypdf if pdfplumber returned nothing useful
        if not text or len(text.strip()) < 50:
            print("  [PDFReader] pdfplumber returned little/no text. Trying pypdf...")
            text = self._extract_with_pypdf(pdf_path)

        # Step 3: If both failed, PDF is likely a scanned image
        if not text or len(text.strip()) < 50:
            raise ValueError(
                f"Could not extract readable text from: {pdf_path}\n"
                "The PDF might be a scanned image (no selectable text).\n"
                "Consider using OCR tools like Adobe Acrobat or pytesseract."
            )

        return self._clean_text(text)

    def extract_by_page(self, pdf_path: str) -> list[dict]:
        """
        Extract text page by page -- useful when you want
        each page to become its own chunk.

        Returns:
            List of dicts: [{"page": 1, "text": "..."}]
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Try pdfplumber page by page (primary)
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    cleaned = self._clean_text(text)
                    if cleaned.strip():
                        pages.append({"page": i, "text": cleaned})
            if pages:
                return pages
        except Exception:
            pass

        # Fallback: pypdf page by page
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            pages = []
            for i, page in enumerate(reader.pages, 1):
                raw = page.extract_text() or ""
                cleaned = self._clean_text(raw)
                if cleaned.strip():
                    pages.append({"page": i, "text": cleaned})
            return pages
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF by page: {e}")

    def get_metadata(self, pdf_path: str) -> dict:
        """Return basic metadata from the PDF (title, author, pages, etc.)"""
        # Try pdfplumber first (primary)
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                meta = pdf.metadata or {}
                return {
                    "total_pages": len(pdf.pages),
                    "title": meta.get("Title", ""),
                    "author": meta.get("Author", ""),
                    "subject": meta.get("Subject", ""),
                    "creator": meta.get("Creator", ""),
                }
        except Exception:
            pass

        # Fallback: pypdf metadata
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            meta = reader.metadata or {}
            return {
                "total_pages": len(reader.pages),
                "title": meta.get("/Title", ""),
                "author": meta.get("/Author", ""),
                "subject": meta.get("/Subject", ""),
                "creator": meta.get("/Creator", ""),
            }
        except Exception:
            return {"total_pages": 0}

    # ------------------------------------------------------------------ #
    # Private: extraction backends                                         #
    # ------------------------------------------------------------------ #

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """
        PRIMARY extractor.
        pdfplumber is better at:
          - Preserving reading order
          - Handling multi-column layouts (research papers, textbooks)
          - Extracting tables as structured text
          - Complex academic PDF formats
        """
        try:
            import pdfplumber
        except ImportError:
            raise ImportError(
                "pdfplumber is not installed.\n"
                "Run: pip install pdfplumber"
            )

        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract regular text
                text = page.extract_text()
                if text:
                    pages_text.append(text)

                # Also extract any tables and append as plain text rows
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            row_text = " | ".join(
                                cell.strip() for cell in row if cell and cell.strip()
                            )
                            if row_text:
                                pages_text.append(row_text)

        return "\n\n".join(pages_text)

    def _extract_with_pypdf(self, pdf_path: str) -> str:
        """
        FALLBACK extractor.
        pypdf is faster but less accurate for complex layouts.
        Used only when pdfplumber fails or returns empty text.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError(
                "pypdf is not installed.\n"
                "Run: pip install pypdf"
            )

        reader = PdfReader(pdf_path)
        pages_text = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

        return "\n\n".join(pages_text)

    # ------------------------------------------------------------------ #
    # Private: text cleaning                                               #
    # ------------------------------------------------------------------ #

    def _clean_text(self, text: str) -> str:
        """
        Clean raw PDF-extracted text:
        - Fix hyphenated line breaks  (e.g. photo-newlinesynthesis -> photosynthesis)
        - Normalize unicode dashes and smart quotes
        - Remove page numbers standing alone on a line
        - Collapse 3+ blank lines into a paragraph break
        - Remove excessive whitespace
        """
        if not text:
            return ""

        # Fix hyphenated word breaks across lines
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)

        # Normalize dashes and smart quotes
        text = text.replace('\u2013', '-').replace('\u2014', '-')
        text = text.replace('\u2018', "'").replace('\u2019', "'")
        text = text.replace('\u201c', '"').replace('\u201d', '"')

        # Replace form feed (page break character) with paragraph break
        text = text.replace('\f', '\n\n')

        # Collapse 3+ newlines into a double newline (paragraph separator)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove standalone page numbers (a line with only digits)
        text = re.sub(r'^\s*\d{1,4}\s*$', '', text, flags=re.MULTILINE)

        # Remove lines that are only whitespace
        lines = [line for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        # Collapse multiple spaces (but not newlines)
        text = re.sub(r'[^\S\n]+', ' ', text)

        return text.strip()