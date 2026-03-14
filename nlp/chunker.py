"""
nlp/chunker.py
--------------
Handles splitting raw input text into meaningful segments
for better MCQ generation context.
"""

import re


class TextChunker:
    """
    Splits text into chunks based on paragraphs or sentence windows.
    Each chunk becomes the context for one or more MCQs.
    """

    def __init__(self, min_chunk_length: int = 100, max_chunk_length: int = 800):
        """
        Args:
            min_chunk_length: Minimum characters a chunk must have (skip if shorter).
            max_chunk_length: Max characters before splitting a large paragraph.
        """
        self.min_chunk_length = min_chunk_length
        self.max_chunk_length = max_chunk_length

    def chunk_by_paragraph(self, text: str) -> list[str]:
        """
        Split text by double newlines (paragraphs).
        Merges very short paragraphs with the next one.
        """
        raw_chunks = re.split(r'\n\s*\n', text.strip())
        chunks = []
        buffer = ""

        for chunk in raw_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            buffer = (buffer + " " + chunk).strip() if buffer else chunk

            if len(buffer) >= self.min_chunk_length:
                # If buffer is too large, split it further
                if len(buffer) > self.max_chunk_length:
                    sub_chunks = self._split_large_chunk(buffer)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(buffer)
                buffer = ""

        # Add remaining buffer
        if buffer and len(buffer) >= self.min_chunk_length // 2:
            chunks.append(buffer)

        return chunks

    def chunk_by_sentences(self, text: str, window: int = 5, step: int = 3) -> list[str]:
        """
        Sliding window over sentences — useful for dense technical text.

        Args:
            window: Number of sentences per chunk.
            step:   Slide step (overlap = window - step).
        """
        sentences = self._split_sentences(text)
        chunks = []

        for i in range(0, len(sentences), step):
            window_sentences = sentences[i: i + window]
            chunk = " ".join(window_sentences).strip()
            if len(chunk) >= self.min_chunk_length:
                chunks.append(chunk)

        return chunks

    def auto_chunk(self, text: str) -> list[str]:
        """
        Automatically choose chunking strategy based on text structure.
        Uses paragraph chunking if text has clear paragraphs,
        otherwise falls back to sentence windows.
        """
        paragraph_count = len(re.findall(r'\n\s*\n', text))

        if paragraph_count >= 2:
            chunks = self.chunk_by_paragraph(text)
        else:
            chunks = self.chunk_by_sentences(text)

        return chunks if chunks else [text.strip()]

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _split_sentences(self, text: str) -> list[str]:
        """Basic sentence splitter using punctuation patterns."""
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _split_large_chunk(self, text: str) -> list[str]:
        """Split an oversized chunk into smaller pieces at sentence boundaries."""
        sentences = self._split_sentences(text)
        chunks = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) > self.max_chunk_length and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = (current + " " + sentence).strip()

        if current:
            chunks.append(current.strip())

        return chunks