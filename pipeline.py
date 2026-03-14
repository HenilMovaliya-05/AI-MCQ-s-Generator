"""
pipeline.py
-----------
The main orchestrator of the hybrid NLP + GenAI MCQ generation pipeline.
Ties together all modules: chunking → keyword extraction → topic detection
→ prompt building → Gemini generation → post-processing → export.
"""

import os
from dotenv import load_dotenv

from nlp.chunker import TextChunker
from nlp.keyword_extractor import KeywordExtractor
from nlp.topic_detector import TopicDetector
from genai.prompt_builder import PromptBuilder
from genai.gemini_client import GeminiClient
from utils.postprocessor import MCQPostProcessor
from utils.exporter import MCQExporter
from utils.pdf_reader import PDFReader


# Load environment variables from .env file
load_dotenv()


class MCQPipeline:
    """
    End-to-end MCQ generation pipeline.

    Usage:
        pipeline = MCQPipeline()
        mcqs = pipeline.run(text="Your passage here...", num_questions=5)
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        output_dir: str = "output",
        use_keybert: bool = False,
    ):
        model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        # NLP Layer
        self.chunker = TextChunker(min_chunk_length=100, max_chunk_length=800)
        self.keyword_extractor = KeywordExtractor(top_n=8, use_keybert=use_keybert)
        self.topic_detector = TopicDetector()

        # GenAI Layer
        self.prompt_builder = PromptBuilder()
        self.gemini = GeminiClient(api_key=api_key, model=model)

        # Post-processing + Export
        self.postprocessor = MCQPostProcessor(similarity_threshold=0.75)
        self.exporter = MCQExporter(output_dir=output_dir)
        self.pdf_reader = PDFReader()

    def run(
        self,
        text: str,
        num_questions: int = None,
        difficulty: str = None,
        export_format: str = None,
        filename: str = None,
        verbose: bool = True,
    ) -> list[dict]:
        """
        Run the full pipeline on input text.

        Args:
            text:           Input text string OR path to a .pdf file.
            num_questions:  Total MCQs to generate (default from .env or 5).
            difficulty:     Override difficulty: easy/medium/hard/mixed.
            export_format:  'json', 'txt', 'pdf', or None to skip saving.
            filename:       Output filename without extension.
            verbose:        Print progress messages.

        Returns:
            List of MCQ dicts.
        """
        # Auto-detect if text is actually a PDF file path
        if text.strip().lower().endswith(".pdf"):
            return self.run_from_pdf(
                pdf_path=text.strip(),
                num_questions=num_questions,
                difficulty=difficulty,
                export_format=export_format,
                filename=filename,
                verbose=verbose,
            )
        num_questions = num_questions or int(os.getenv("MCQ_PER_CHUNK", 3))
        difficulty = difficulty or os.getenv("DEFAULT_DIFFICULTY", "mixed")
        export_format = export_format or os.getenv("OUTPUT_FORMAT", "json")

        self._log(verbose, "\n🚀 MCQ Generator Pipeline Starting...")
        self._log(verbose, f"   Target: {num_questions} questions | Difficulty: {difficulty}\n")

        # ── Step 1: NLP - Text Chunking ─────────────────────────────────
        self._log(verbose, "📄 Step 1: Chunking text...")
        chunks = self.chunker.auto_chunk(text)
        self._log(verbose, f"   → {len(chunks)} chunk(s) created\n")

        # ── Step 2: NLP - Analysis per chunk ────────────────────────────
        all_mcqs = []
        mcqs_per_chunk = max(1, round(num_questions / len(chunks)))

        for i, chunk in enumerate(chunks, 1):
            self._log(verbose, f"🔬 Step 2: Analyzing chunk {i}/{len(chunks)}...")

            # Keyword extraction
            kw_data = self.keyword_extractor.extract_full(chunk, all_chunks=chunks)
            keywords = kw_data["combined"]

            # Topic + difficulty detection
            analysis = self.topic_detector.analyze(chunk)
            topic = analysis["topic"]
            chunk_difficulty = difficulty if difficulty != "mixed" else analysis["difficulty"]

            self._log(verbose, f"   → Topic: {topic} | Difficulty: {chunk_difficulty} | Keywords: {', '.join(keywords[:5])}\n")

            # ── Step 3: Build structured prompt ─────────────────────────
            self._log(verbose, f"📝 Step 3: Building prompt for chunk {i}...")
            prompt = self.prompt_builder.build_mcq_prompt(
                chunk=chunk,
                keywords=keywords,
                topic=topic,
                difficulty=chunk_difficulty,
                num_questions=mcqs_per_chunk,
            )

            # ── Step 4: GenAI - Generate MCQs ───────────────────────────
            self._log(verbose, f"🤖 Step 4: Calling Gemini API for chunk {i}...")
            try:
                chunk_mcqs = self.gemini.generate_mcqs(prompt)
                self._log(verbose, f"   → {len(chunk_mcqs)} MCQ(s) generated\n")
                all_mcqs.extend(chunk_mcqs)
            except Exception as e:
                self._log(verbose, f"   ⚠ Skipping chunk {i} due to error: {e}\n")

        # ── Step 5: NLP Post-processing ──────────────────────────────────
        self._log(verbose, "🧹 Step 5: Post-processing (dedup, validation, cleaning)...")
        processed = self.postprocessor.process(all_mcqs)

        # Trim to requested count
        processed = processed[:num_questions]

        stats = self.postprocessor.get_stats(processed)
        self._log(verbose, f"   → {stats['total']} final MCQs | By difficulty: {stats.get('by_difficulty', {})}\n")

        # ── Step 6: Export ───────────────────────────────────────────────
        if export_format and processed:
            self._log(verbose, f"💾 Step 6: Exporting as {export_format.upper()}...")
            path = self.exporter.export(processed, format=export_format, filename=filename)
            self._log(verbose, f"   → Saved to: {path}\n")

        self._log(verbose, f"✅ Pipeline complete! {len(processed)} MCQs generated.\n")
        return processed

    def _log(self, verbose: bool, message: str):
        if verbose:
            print(message)

    def run_from_pdf(
        self,
        pdf_path: str,
        num_questions: int = None,
        difficulty: str = None,
        export_format: str = None,
        filename: str = None,
        verbose: bool = True,
    ) -> list[dict]:
        """
        Convenience method: extract text from a PDF then run the pipeline.

        Args:
            pdf_path: Path to the .pdf input file.
            (all other args same as run())

        Returns:
            List of MCQ dicts.
        """
        self._log(verbose, f"\n📖 Reading PDF: {pdf_path}")

        # Show PDF metadata
        meta = self.pdf_reader.get_metadata(pdf_path)
        if meta.get("total_pages"):
            title_info = f" | Title: {meta['title']}" if meta.get("title") else ""
            self._log(verbose, f"   → {meta['total_pages']} page(s){title_info}\n")

        # Extract text
        text = self.pdf_reader.extract_text(pdf_path)
        word_count = len(text.split())
        self._log(verbose, f"   → Extracted {word_count} words from PDF\n")

        # Auto-set filename from PDF name if not provided
        if not filename:
            base = os.path.splitext(os.path.basename(pdf_path))[0]
            filename = f"{base}_mcqs"

        return self.run(
            text=text,
            num_questions=num_questions,
            difficulty=difficulty,
            export_format=export_format,
            filename=filename,
            verbose=verbose,
        )