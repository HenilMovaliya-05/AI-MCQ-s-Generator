# """
# utils/exporter.py
# -----------------
# Exports the final MCQ set to different formats:
# - JSON  (structured, machine-readable)
# - TXT   (human-readable, plain text)
# - PDF   (requires fpdf2: pip install fpdf2)
# """

# import json
# import os
# from datetime import datetime


# class MCQExporter:
#     """
#     Handles saving MCQs to disk in multiple formats.
#     """

#     def __init__(self, output_dir: str = "output"):
#         self.output_dir = output_dir
#         os.makedirs(output_dir, exist_ok=True)

#     def export(self, mcqs: list[dict], format: str = "json", filename: str = None) -> str:
#         """
#         Export MCQs to the specified format.

#         Args:
#             mcqs:     List of MCQ dicts.
#             format:   'json', 'txt', or 'pdf'.
#             filename: Optional custom filename (without extension).

#         Returns:
#             Path to the saved file.
#         """
#         if not filename:
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             filename = f"mcqs_{timestamp}"

#         format = format.lower()

#         if format == "json":
#             return self._export_json(mcqs, filename)
#         elif format == "txt":
#             return self._export_txt(mcqs, filename)
#         elif format == "pdf":
#             return self._export_pdf(mcqs, filename)
#         else:
#             raise ValueError(f"Unsupported format: '{format}'. Use json, txt, or pdf.")

#     # ------------------------------------------------------------------ #
#     # JSON export                                                          #
#     # ------------------------------------------------------------------ #

#     def _export_json(self, mcqs: list[dict], filename: str) -> str:
#         path = os.path.join(self.output_dir, f"{filename}.json")
#         export_data = {
#             "generated_at": datetime.now().isoformat(),
#             "total_questions": len(mcqs),
#             "mcqs": mcqs,
#         }
#         with open(path, "w", encoding="utf-8") as f:
#             json.dump(export_data, f, indent=2, ensure_ascii=False)
#         return path

#     # ------------------------------------------------------------------ #
#     # TXT export                                                           #
#     # ------------------------------------------------------------------ #

#     def _export_txt(self, mcqs: list[dict], filename: str) -> str:
#         path = os.path.join(self.output_dir, f"{filename}.txt")
#         lines = [
#             "=" * 60,
#             "  MCQ GENERATOR - QUESTION SET",
#             f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
#             f"  Total Questions: {len(mcqs)}",
#             "=" * 60,
#             "",
#         ]

#         for i, mcq in enumerate(mcqs, 1):
#             lines.append(f"Q{i}. [{mcq.get('difficulty', '').upper()}] [{mcq.get('topic', '').title()}]")
#             lines.append(f"    {mcq.get('question', '')}")
#             lines.append("")

#             for key, value in mcq.get("options", {}).items():
#                 marker = "(*)" if key == mcq.get("correct_answer") else "   "
#                 lines.append(f"   {marker} {key}. {value}")

#             lines.append("")
#             lines.append(f"   Answer: {mcq.get('correct_answer', '')}")
#             lines.append(f"   Explanation: {mcq.get('explanation', '')}")
#             lines.append("")
#             lines.append("-" * 60)
#             lines.append("")

#         with open(path, "w", encoding="utf-8") as f:
#             f.write("\n".join(lines))
#         return path

#     # ------------------------------------------------------------------ #
#     # PDF export                                                           #
#     # ------------------------------------------------------------------ #

#     def _export_pdf(self, mcqs: list[dict], filename: str) -> str:
#         try:
#             from fpdf import FPDF
#         except ImportError:
#             raise ImportError(
#                 "fpdf2 is required for PDF export.\n"
#                 "Run: pip install fpdf2"
#             )

#         path = os.path.join(self.output_dir, f"{filename}.pdf")

#         pdf = FPDF()
#         pdf.set_auto_page_break(auto=True, margin=15)
#         pdf.add_page()

#         # Title
#         pdf.set_font("Helvetica", "B", 16)
#         pdf.cell(0, 10, "MCQ Question Set", new_x="LMARGIN", new_y="NEXT", align="C")
#         pdf.set_font("Helvetica", "", 10)
#         pdf.cell(
#             0, 6,
#             f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Total: {len(mcqs)} questions",
#             new_x="LMARGIN", new_y="NEXT", align="C"
#         )
#         pdf.ln(6)

#         for i, mcq in enumerate(mcqs, 1):
#             # Question number + metadata
#             pdf.set_font("Helvetica", "B", 11)
#             tag = f"[{mcq.get('difficulty','').upper()}] [{mcq.get('topic','').title()}]"
#             pdf.set_text_color(100, 100, 100)
#             pdf.cell(0, 6, tag, new_x="LMARGIN", new_y="NEXT")

#             # Question text
#             pdf.set_text_color(0, 0, 0)
#             pdf.set_font("Helvetica", "B", 11)
#             pdf.multi_cell(0, 7, f"Q{i}. {mcq.get('question', '')}")
#             pdf.ln(2)

#             # Options
#             pdf.set_font("Helvetica", "", 10)
#             for key, value in mcq.get("options", {}).items():
#                 is_correct = key == mcq.get("correct_answer")
#                 if is_correct:
#                     pdf.set_text_color(0, 120, 0)
#                     pdf.set_font("Helvetica", "B", 10)
#                 else:
#                     pdf.set_text_color(0, 0, 0)
#                     pdf.set_font("Helvetica", "", 10)
#                 pdf.cell(0, 6, f"  {key}. {value}", new_x="LMARGIN", new_y="NEXT")

#             # Explanation
#             pdf.set_text_color(60, 60, 60)
#             pdf.set_font("Helvetica", "I", 9)
#             pdf.ln(1)
#             pdf.multi_cell(0, 5, f"Explanation: {mcq.get('explanation', '')}")
#             pdf.set_text_color(0, 0, 0)
#             pdf.ln(5)

#         pdf.output(path)
#         return path

"""
utils/exporter.py
-----------------
Exports the final MCQ set to different formats:
- JSON  (structured, machine-readable)
- TXT   (human-readable, plain text)
- PDF   (professional layout using fpdf2)
"""

import json
import os
from datetime import datetime


class MCQExporter:
    """
    Handles saving MCQs to disk in multiple formats.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export(self, mcqs: list[dict], format: str = "pdf", filename: str = None) -> str:
        """
        Export MCQs to the specified format.

        Args:
            mcqs:     List of MCQ dicts.
            format:   'json', 'txt', or 'pdf'.
            filename: Optional custom filename (without extension).

        Returns:
            Path to the saved file.
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mcqs_{timestamp}"

        format = format.lower()

        if format == "json":
            return self._export_json(mcqs, filename)
        elif format == "txt":
            return self._export_txt(mcqs, filename)
        elif format == "pdf":
            return self._export_pdf(mcqs, filename)
        else:
            raise ValueError(f"Unsupported format: '{format}'. Use json, txt, or pdf.")

    # ------------------------------------------------------------------ #
    # JSON export                                                          #
    # ------------------------------------------------------------------ #

    def _export_json(self, mcqs: list[dict], filename: str) -> str:
        path = os.path.join(self.output_dir, f"{filename}.json")
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "total_questions": len(mcqs),
            "mcqs": mcqs,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        return path

    # ------------------------------------------------------------------ #
    # TXT export                                                           #
    # ------------------------------------------------------------------ #

    def _export_txt(self, mcqs: list[dict], filename: str) -> str:
        path = os.path.join(self.output_dir, f"{filename}.txt")
        lines = [
            "=" * 60,
            "  MCQ GENERATOR - QUESTION SET",
            f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"  Total Questions: {len(mcqs)}",
            "=" * 60,
            "",
        ]

        for i, mcq in enumerate(mcqs, 1):
            lines.append(f"Q{i}. [{mcq.get('difficulty', '').upper()}] [{mcq.get('topic', '').title()}]")
            lines.append(f"    {mcq.get('question', '')}")
            lines.append("")

            for key, value in mcq.get("options", {}).items():
                marker = "(*)" if key == mcq.get("correct_answer") else "   "
                lines.append(f"   {marker} {key}. {value}")

            lines.append("")
            lines.append(f"   Answer: {mcq.get('correct_answer', '')}")
            lines.append(f"   Explanation: {mcq.get('explanation', '')}")
            lines.append("")
            lines.append("-" * 60)
            lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path

    # ------------------------------------------------------------------ #
    # PDF export                                                           #
    # ------------------------------------------------------------------ #

    def _export_pdf(self, mcqs: list[dict], filename: str) -> str:
        try:
            from fpdf import FPDF
        except ImportError:
            raise ImportError(
                "fpdf2 is required for PDF export.\n"
                "Run: pip install fpdf2"
            )

        path = os.path.join(self.output_dir, f"{filename}.pdf")

        # ── Difficulty color map ──────────────────────────────────────────
        DIFF_COLORS = {
            "easy":   (34,  139, 34),   # green
            "medium": (255, 140,  0),   # orange
            "hard":   (180,  0,   0),   # red
        }

        # ── Unicode -> latin-1 replacement map ───────────────────────────
        # Gemini often returns smart quotes, em dashes, ellipsis etc.
        # fpdf2 built-in fonts (Helvetica) only support latin-1.
        # We replace known Unicode chars with proper ASCII equivalents
        # instead of ugly "?" fallbacks.
        UNICODE_MAP = {
            # Dashes
            "\u2014": "-",    # em dash        -
            "\u2013": "-",    # en dash        -
            "\u2012": "-",    # figure dash    -
            "\u2015": "-",    # horizontal bar -
            # Quotes
            "\u2018": "'",    # left single quotation
            "\u2019": "'",    # right single quotation
            "\u201a": ",",    # single low-9 quotation
            "\u201b": "'",    # single high reversed
            "\u201c": '"',    # left double quotation
            "\u201d": '"',    # right double quotation
            "\u201e": '"',    # double low-9 quotation
            "\u201f": '"',    # double high reversed
            "\u2032": "'",    # prime
            "\u2033": '"',    # double prime
            # Ellipsis
            "\u2026": "...",  # ellipsis
            # Spaces
            "\u00a0": " ",    # non-breaking space
            "\u2009": " ",    # thin space
            "\u200b": "",     # zero-width space
            "\u200c": "",     # zero-width non-joiner
            "\u200d": "",     # zero-width joiner
            "\ufeff": "",     # BOM
            # Bullets and symbols
            "\u2022": "-",    # bullet
            "\u2023": "-",    # triangular bullet
            "\u25cf": "-",    # black circle
            "\u25cb": "-",    # white circle
            "\u2713": "OK",   # check mark
            "\u2714": "OK",   # heavy check mark
            "\u2717": "X",    # ballot X
            "\u2718": "X",    # heavy ballot X
            # Math / fractions
            "\u00d7": "x",    # multiplication sign
            "\u00f7": "/",    # division sign
            "\u2212": "-",    # minus sign
            "\u00b1": "+/-",  # plus-minus
            "\u00b2": "2",    # superscript 2
            "\u00b3": "3",    # superscript 3
            "\u00b9": "1",    # superscript 1
            "\u00bc": "1/4",  # vulgar fraction 1/4
            "\u00bd": "1/2",  # vulgar fraction 1/2
            "\u00be": "3/4",  # vulgar fraction 3/4
            # Arrows
            "\u2192": "->",   # rightwards arrow
            "\u2190": "<-",   # leftwards arrow
            "\u2194": "<->",  # left right arrow
            "\u21d2": "=>",   # rightwards double arrow
            # Misc
            "\u00ae": "(R)",  # registered sign
            "\u00a9": "(C)",  # copyright sign
            "\u2122": "TM",   # trade mark sign
            "\u00b0": "deg",  # degree sign
        }

        def safe(text: str) -> str:
            """
            Convert text to latin-1 safe string for fpdf2 Helvetica font.
            Step 1: Replace known Unicode chars with clean ASCII equivalents.
            Step 2: Drop anything still outside latin-1 range silently.
            """
            if not text:
                return ""
            for unicode_char, replacement in UNICODE_MAP.items():
                text = text.replace(unicode_char, replacement)
            # Final fallback: drop any remaining non-latin-1 characters
            return text.encode("latin-1", errors="ignore").decode("latin-1")

        # ── Build PDF ─────────────────────────────────────────────────────
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.set_margins(20, 20, 20)
        pdf.add_page()

        # ── Cover header ──────────────────────────────────────────────────
        pdf.set_fill_color(30, 30, 80)
        pdf.rect(0, 0, 210, 38, style="F")

        pdf.set_y(8)
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "MCQ Question Set", align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(200, 200, 220)
        meta_line = (
            f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}   |   "
            f"Total Questions: {len(mcqs)}"
        )
        pdf.cell(0, 7, safe(meta_line), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(18)

        # ── Difficulty legend ─────────────────────────────────────────────
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 5, "Difficulty:  Easy   Medium   Hard", align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # ── Questions ─────────────────────────────────────────────────────
        for i, mcq in enumerate(mcqs, 1):
            difficulty  = mcq.get("difficulty", "medium").lower()
            topic       = mcq.get("topic", "general").title()
            question    = safe(mcq.get("question", ""))
            options     = mcq.get("options", {})
            answer      = mcq.get("correct_answer", "")
            explanation = safe(mcq.get("explanation", ""))

            diff_color = DIFF_COLORS.get(difficulty, (80, 80, 80))

            # ── Question card background ───────────────────────────────────
            card_y = pdf.get_y()
            pdf.set_fill_color(248, 248, 252)
            pdf.rect(18, card_y, 174, 8, style="F")

            # ── Difficulty color bar on left edge ──────────────────────────
            pdf.set_fill_color(*diff_color)
            pdf.rect(18, card_y, 4, 8, style="F")

            # Q number
            pdf.set_xy(24, card_y)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(30, 30, 80)
            pdf.cell(12, 8, f"Q{i}.", new_x="RIGHT", new_y="TOP")

            # Topic + difficulty badge
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(100, 100, 140)
            pdf.cell(0, 8, safe(f"[{topic}]  [{difficulty.upper()}]"),
                     new_x="LMARGIN", new_y="NEXT")

            # ── Question text ──────────────────────────────────────────────
            pdf.set_x(24)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(166, 6, question)
            pdf.ln(3)

            # ── Options ────────────────────────────────────────────────────
            for key, value in options.items():
                is_correct = (key == answer)
                safe_value = safe(str(value))

                pdf.set_x(26)

                if is_correct:
                    opt_y = pdf.get_y()
                    pdf.set_fill_color(220, 245, 220)
                    pdf.rect(26, opt_y, 162, 7, style="F")
                    pdf.set_xy(26, opt_y)
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.set_text_color(0, 110, 0)
                    pdf.cell(8, 7, f"{key}.", new_x="RIGHT", new_y="TOP")
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.multi_cell(154, 7, f"{safe_value}  [CORRECT]")
                else:
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(50, 50, 50)
                    pdf.cell(8, 6, f"{key}.", new_x="RIGHT", new_y="TOP")
                    pdf.set_x(34)
                    pdf.multi_cell(154, 6, safe_value)

            pdf.ln(2)

            # ── Explanation box ────────────────────────────────────────────
            exp_y = pdf.get_y()
            pdf.set_fill_color(240, 245, 255)
            pdf.rect(26, exp_y, 162, 6, style="F")
            pdf.set_xy(26, exp_y)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(60, 60, 120)
            pdf.multi_cell(162, 5, f"Explanation: {explanation}")

            pdf.ln(6)

            # ── Divider between questions ──────────────────────────────────
            if i < len(mcqs):
                pdf.set_draw_color(200, 200, 220)
                pdf.set_line_width(0.3)
                line_y = pdf.get_y()
                pdf.line(20, line_y, 190, line_y)
                pdf.ln(6)

        # ── Footer ────────────────────────────────────────────────────────
        pdf.set_y(-18)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(160, 160, 160)
        pdf.cell(0, 6,
                 safe(f"Generated by AI MCQ Generator  |  {datetime.now().strftime('%Y-%m-%d')}"),
                 align="C")

        pdf.output(path)
        return path