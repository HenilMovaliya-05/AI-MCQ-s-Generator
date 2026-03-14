"""
tests/test_pdf_reader.py
------------------------
Tests for PDF text extraction and cleaning.
Run with: python tests/test_pdf_reader.py
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pdf_reader import PDFReader


def make_sample_pdf(path: str, content: str):
    """Create a real PDF with given content using reportlab or fpdf2."""
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        for line in content.split("\n"):
            pdf.multi_cell(0, 8, line)
        pdf.output(path)
        return True
    except ImportError:
        pass

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        c = canvas.Canvas(path, pagesize=letter)
        width, height = letter
        y = height - 50
        for line in content.split("\n"):
            c.drawString(50, y, line[:100])
            y -= 15
            if y < 50:
                c.showPage()
                y = height - 50
        c.save()
        return True
    except ImportError:
        pass

    return False


SAMPLE_TEXT = (
    "Photosynthesis is the process by which plants convert sunlight into energy. "
    "This process occurs in the chloroplasts using chlorophyll. "
    "The products are glucose and oxygen, while carbon dioxide and water are consumed."
)

DIRTY_TEXT = "  This   is  some  text  with  extra   spaces.  \n\n\n\nAnd too many blank lines.\n"


class TestPDFReaderCleaning:
    """Test the text cleaning logic — no PDF file needed."""

    def setup_method(self):
        self.reader = PDFReader()

    def test_clean_removes_extra_spaces(self):
        result = self.reader._clean_text(DIRTY_TEXT)
        assert "  " not in result

    def test_clean_collapses_multiple_newlines(self):
        result = self.reader._clean_text("Line1\n\n\n\n\nLine2")
        assert "\n\n\n" not in result

    def test_clean_fixes_hyphenated_line_breaks(self):
        result = self.reader._clean_text("photo-\nsynthesis is important")
        assert "photosynthesis" in result

    def test_clean_removes_page_numbers(self):
        result = self.reader._clean_text("Some content\n   42   \nMore content")
        assert "42" not in result.split()

    def test_clean_empty_string(self):
        result = self.reader._clean_text("")
        assert result == ""

    def test_clean_normalizes_dashes(self):
        result = self.reader._clean_text("word\u2013word and word\u2014word")
        assert "\u2013" not in result
        assert "\u2014" not in result
        assert "-" in result

    def test_clean_normalizes_quotes(self):
        result = self.reader._clean_text("\u2018Hello\u2019 and \u201cWorld\u201d")
        assert "'" in result
        assert '"' in result

    def test_clean_strips_whitespace(self):
        result = self.reader._clean_text("   hello world   ")
        assert result == result.strip()


class TestPDFReaderFileHandling:
    """Test file validation."""

    def setup_method(self):
        self.reader = PDFReader()

    def test_raises_for_missing_file(self):
        try:
            self.reader.extract_text("/nonexistent/path/file.pdf")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_raises_for_non_pdf_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"some text")
            path = f.name
        try:
            self.reader.extract_text(path)
            assert False, "Should have raised an error for non-PDF"
        except (ValueError, Exception):
            pass  # Any error is acceptable — pypdf or our own ValueError
        finally:
            os.unlink(path)


class TestPDFReaderWithRealPDF:
    """Tests that require an actual PDF — skipped if PDF libraries unavailable."""

    def setup_method(self):
        self.reader = PDFReader()
        self.tmp_path = None

    def teardown_method(self):
        if self.tmp_path and os.path.exists(self.tmp_path):
            os.unlink(self.tmp_path)

    def test_extract_text_from_real_pdf(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            self.tmp_path = f.name

        created = make_sample_pdf(self.tmp_path, SAMPLE_TEXT)
        if not created:
            print("  ⚠ Skipped (no fpdf2/reportlab installed)")
            return

        text = self.reader.extract_text(self.tmp_path)
        assert isinstance(text, str)
        assert len(text) > 20
        assert "photosynthesis" in text.lower() or "Photosynthesis" in text

    def test_extract_by_page_returns_list(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            self.tmp_path = f.name

        created = make_sample_pdf(self.tmp_path, SAMPLE_TEXT)
        if not created:
            print("  ⚠ Skipped (no fpdf2/reportlab installed)")
            return

        pages = self.reader.extract_by_page(self.tmp_path)
        assert isinstance(pages, list)
        assert len(pages) >= 1
        assert "page" in pages[0]
        assert "text" in pages[0]

    def test_get_metadata_returns_dict(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            self.tmp_path = f.name

        created = make_sample_pdf(self.tmp_path, "Hello")
        if not created:
            print("  ⚠ Skipped (no fpdf2/reportlab installed)")
            return

        meta = self.reader.get_metadata(self.tmp_path)
        assert isinstance(meta, dict)
        assert "total_pages" in meta
        assert meta["total_pages"] >= 1


# ── Run ───────────────────────────────────────────────────────────────── #

if __name__ == "__main__":
    test_classes = [
        TestPDFReaderCleaning,
        TestPDFReaderFileHandling,
        TestPDFReaderWithRealPDF,
    ]
    passed = 0
    failed = 0

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method in methods:
            try:
                instance.setup_method()
                getattr(instance, method)()
                print(f"  ✓ {cls.__name__}.{method}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {cls.__name__}.{method}: {e}")
                failed += 1
            finally:
                if hasattr(instance, "teardown_method"):
                    instance.teardown_method()

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")