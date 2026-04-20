"""
utils/pdf_reader.py
--------------------
Extracts clean text from PDF files.

Primary:  pdfplumber  -- better layout, table support, multi-column handling
Fallback: pypdf       -- used only if pdfplumber fails for any reason

Handles diagram-heavy PDFs (like lecture slides) by:
- Processing page by page
- Skipping pages that are mostly images with little/no text
- Merging all text-bearing pages into one clean passage
- Logging which pages were skipped (diagram-only pages)
"""

import re
import os


# Minimum meaningful words a page must have to be included
# Pages with fewer words than this are considered diagram/image pages
MIN_WORDS_PER_PAGE = 15


class PDFReader:
    """
    Reads a PDF file and returns clean extracted text
    ready to feed into the NLP chunking pipeline.

    Automatically skips diagram-only and image-only pages.
    Uses pdfplumber as primary, pypdf as fallback.
    """

    def __init__(self, min_words_per_page: int = MIN_WORDS_PER_PAGE):
        """
        Args:
            min_words_per_page: Pages with fewer words are skipped as
                                diagram/image pages. Default is 15 words.
        """
        self.min_words_per_page = min_words_per_page

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract all meaningful text from a PDF file.
        Automatically skips diagram-only and image-only pages.

        Args:
            pdf_path: Path to the .pdf file.

        Returns:
            Cleaned plain text string from all text-bearing pages.

        Raises:
            FileNotFoundError: If the PDF path does not exist.
            ValueError:        If the PDF has no extractable text at all.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if not pdf_path.lower().endswith(".pdf"):
            raise ValueError(f"File is not a PDF: {pdf_path}")

        # Extract page by page with diagram skipping
        pages = self._extract_pages_smart(pdf_path)

        if not pages:
            raise ValueError(
                f"Could not extract readable text from: {pdf_path}\n"
                "All pages appear to be images or diagrams with no selectable text.\n"
                "Consider using OCR tools like Adobe Acrobat or pytesseract."
            )

        # Merge all text-bearing pages
        full_text = "\n\n".join(p["text"] for p in pages)
        return self._clean_text(full_text)

    def _extract_pages_smart(self, pdf_path: str) -> list[dict]:
        """
        Extract text page by page, smartly skipping:
        - Diagram-only pages (image with no text)
        - Pages with only copyright/header lines
        - Pages with fewer than min_words_per_page meaningful words

        Returns list of dicts: [{"page": 1, "text": "...", "skipped": False}]
        Logs skipped pages to terminal so user knows what was skipped.
        """
        pages = []
        skipped_pages = []
        text_pages = []

        # Try pdfplumber first
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                total = len(pdf.pages)
                for i, page in enumerate(pdf.pages, 1):
                    raw_text = page.extract_text() or ""

                    # Also extract tables
                    try:
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                if row:
                                    row_text = " | ".join(
                                        cell.strip() for cell in row
                                        if cell and cell.strip()
                                    )
                                    if row_text:
                                        raw_text += "\n" + row_text
                    except Exception:
                        pass

                    cleaned = self._clean_text(raw_text)
                    word_count = len(cleaned.split())

                    # Skip diagram/image pages
                    if self._is_diagram_page(cleaned, word_count):
                        skipped_pages.append(i)
                    else:
                        text_pages.append(i)
                        pages.append({"page": i, "text": cleaned})

            # Log what happened
            print(f"  [PDFReader] Total pages: {total}")
            print(f"  [PDFReader] Text pages extracted: {len(text_pages)} → pages {text_pages}")
            if skipped_pages:
                print(f"  [PDFReader] Skipped (diagram/image pages): {len(skipped_pages)} → pages {skipped_pages}")

            if pages:
                return pages

        except ImportError:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")
        except Exception as e:
            print(f"  [PDFReader] pdfplumber failed: {e}. Trying pypdf...")

        # Fallback: pypdf page by page
        return self._extract_pages_pypdf(pdf_path)

    def _extract_pages_pypdf(self, pdf_path: str) -> list[dict]:
        """Fallback page-by-page extraction using pypdf."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("pypdf not installed. Run: pip install pypdf")

        reader = PdfReader(pdf_path)
        pages = []
        skipped = []

        for i, page in enumerate(reader.pages, 1):
            raw = page.extract_text() or ""
            cleaned = self._clean_text(raw)
            word_count = len(cleaned.split())

            if self._is_diagram_page(cleaned, word_count):
                skipped.append(i)
            else:
                pages.append({"page": i, "text": cleaned})

        print(f"  [PDFReader] pypdf fallback: {len(pages)} text pages, {len(skipped)} skipped")
        return pages

    def _is_diagram_page(self, text: str, word_count: int) -> bool:
        """
        Detect if a page is a diagram/image page with no useful text.

        A page is considered a diagram page if:
        1. Word count is below the minimum threshold
        2. OR the text is only copyright/header lines after removing them
        """
        if word_count < self.min_words_per_page:
            return True

        # Remove common slide header/footer patterns
        # e.g. "© Ronak Patel, Computer Engineering Department, CSPIT, CHARUSAT"
        cleaned = re.sub(
            r'©.*?(CHARUSAT|University|Institute|College|Department)[^\n]*',
            '', text, flags=re.IGNORECASE
        )
        # Remove slide numbers standing alone
        cleaned = re.sub(r'^\s*\d+\s*$', '', cleaned, flags=re.MULTILINE)
        # Remove unit/chapter title lines (short lines, likely slide titles)
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()]

        # After removing headers if meaningful content is too short → skip
        meaningful_words = len(' '.join(lines).split())
        if meaningful_words < self.min_words_per_page:
            return True

        return False

    def extract_by_page(self, pdf_path: str) -> list[dict]:
        """
        Extract text page by page with diagram skipping.
        Returns list of dicts for pages that have meaningful text.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        return self._extract_pages_smart(pdf_path)

    def get_metadata(self, pdf_path: str) -> dict:
        """Return basic metadata from the PDF."""
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                meta = pdf.metadata or {}
                return {
                    "total_pages": len(pdf.pages),
                    "title":   meta.get("Title", ""),
                    "author":  meta.get("Author", ""),
                    "subject": meta.get("Subject", ""),
                    "creator": meta.get("Creator", ""),
                }
        except Exception:
            pass

        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            meta = reader.metadata or {}
            return {
                "total_pages": len(reader.pages),
                "title":   meta.get("/Title", ""),
                "author":  meta.get("/Author", ""),
                "subject": meta.get("/Subject", ""),
                "creator": meta.get("/Creator", ""),
            }
        except Exception:
            return {"total_pages": 0}

    # ------------------------------------------------------------------ 
    # Private: text cleaning                                               

    def _clean_text(self, text: str) -> str:
        """
        Clean raw PDF-extracted text:
        - Fix hyphenated line breaks
        - Normalize unicode dashes and smart quotes
        - Remove copyright footer lines (common in lecture slides)
        - Remove standalone page numbers
        - Collapse extra blank lines
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

        # Remove copyright footer lines common in lecture slides
        # e.g. "© Ronak Patel, Computer Engineering Department, CSPIT, CHARUSAT"
        text = re.sub(
            r'©[^\n]*(University|Institute|College|Department|CHARUSAT|CSPIT)[^\n]*\n?',
            '', text, flags=re.IGNORECASE
        )

        # Replace form feed with paragraph break
        text = text.replace('\f', '\n\n')

        # Collapse 3+ newlines to double newline
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove standalone page numbers
        text = re.sub(r'^\s*\d{1,4}\s*$', '', text, flags=re.MULTILINE)

        # Remove lines that are only whitespace
        lines = [line for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        # Collapse multiple spaces (not newlines)
        text = re.sub(r'[^\S\n]+', ' ', text)

        return text.strip()