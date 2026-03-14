"""
tests/test_nlp.py
-----------------
Unit tests for the NLP preprocessing layer.
Run with: python -m pytest tests/test_nlp.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.chunker import TextChunker
from nlp.keyword_extractor import KeywordExtractor
from nlp.topic_detector import TopicDetector


# ── Sample Texts ──────────────────────────────────────────────────────── #

SCIENCE_TEXT = """
Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide
to produce oxygen and energy in the form of glucose. This process takes place in the
chloroplasts of plant cells, specifically using a green pigment called chlorophyll.

The light-dependent reactions occur in the thylakoid membranes, where light energy
is converted into chemical energy (ATP and NADPH). The light-independent reactions,
also known as the Calvin cycle, take place in the stroma and use the chemical energy
to convert carbon dioxide into glucose.

Photosynthesis is fundamental to life on Earth as it produces the oxygen we breathe
and forms the base of almost all food chains through primary production.
"""

HISTORY_TEXT = """
The French Revolution began in 1789 and fundamentally transformed French society.
The revolution was driven by social inequality, financial crisis, and Enlightenment ideas.

The storming of the Bastille on July 14, 1789 became a symbol of the revolution.
The National Assembly abolished feudalism and adopted the Declaration of the Rights
of Man and Citizen. King Louis XVI was eventually executed in January 1793.

The revolution led to the rise of Napoleon Bonaparte and spread revolutionary ideals
across Europe, influencing subsequent democratic movements worldwide.
"""

SHORT_TEXT = "Photosynthesis is how plants make food."


# ── TextChunker Tests ─────────────────────────────────────────────────── #

class TestTextChunker:
    def setup_method(self):
        self.chunker = TextChunker(min_chunk_length=50, max_chunk_length=500)

    def test_chunk_by_paragraph_splits_correctly(self):
        chunks = self.chunker.chunk_by_paragraph(SCIENCE_TEXT)
        assert len(chunks) >= 2, "Should produce at least 2 paragraphs"
        for chunk in chunks:
            assert len(chunk) >= 50, "Each chunk should meet min length"

    def test_auto_chunk_paragraph_text(self):
        chunks = self.chunker.auto_chunk(SCIENCE_TEXT)
        assert len(chunks) >= 1
        assert all(isinstance(c, str) for c in chunks)

    def test_auto_chunk_returns_list(self):
        result = self.chunker.auto_chunk(HISTORY_TEXT)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_short_text_returns_single_chunk(self):
        chunks = self.chunker.auto_chunk(SHORT_TEXT)
        assert len(chunks) >= 1

    def test_chunk_by_sentences(self):
        chunks = self.chunker.chunk_by_sentences(SCIENCE_TEXT, window=3, step=2)
        assert isinstance(chunks, list)


# ── KeywordExtractor Tests ────────────────────────────────────────────── #

class TestKeywordExtractor:
    def setup_method(self):
        self.extractor = KeywordExtractor(top_n=6, use_keybert=False)

    def test_extracts_keywords_from_text(self):
        keywords = self.extractor.extract(SCIENCE_TEXT)
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert len(keywords) <= 6

    def test_keywords_are_strings(self):
        keywords = self.extractor.extract(SCIENCE_TEXT)
        assert all(isinstance(k, str) for k in keywords)

    def test_keywords_not_stopwords(self):
        from nlp.keyword_extractor import STOPWORDS
        keywords = self.extractor.extract(SCIENCE_TEXT)
        for kw in keywords:
            assert kw.lower() not in STOPWORDS, f"Stopword found in keywords: {kw}"

    def test_named_entity_extraction(self):
        entities = self.extractor.extract_named_entities(HISTORY_TEXT)
        assert isinstance(entities, list)
        # Should find "French Revolution", "National Assembly", etc.

    def test_full_extraction_returns_dict(self):
        result = self.extractor.extract_full(SCIENCE_TEXT)
        assert "keywords" in result
        assert "entities" in result
        assert "combined" in result

    def test_tfidf_with_multiple_chunks(self):
        chunks = [SCIENCE_TEXT, HISTORY_TEXT]
        keywords = self.extractor.extract(SCIENCE_TEXT, all_chunks=chunks)
        assert len(keywords) > 0


# ── TopicDetector Tests ───────────────────────────────────────────────── #

class TestTopicDetector:
    def setup_method(self):
        self.detector = TopicDetector()

    def test_detects_science_topic(self):
        topic = self.detector.detect_topic(SCIENCE_TEXT)
        assert topic == "science", f"Expected 'science', got '{topic}'"

    def test_detects_history_topic(self):
        topic = self.detector.detect_topic(HISTORY_TEXT)
        assert topic == "history", f"Expected 'history', got '{topic}'"

    def test_detect_difficulty_returns_valid_level(self):
        difficulty = self.detector.detect_difficulty(SCIENCE_TEXT)
        assert difficulty in ["easy", "medium", "hard"]

    def test_short_text_defaults_to_general(self):
        topic = self.detector.detect_topic("Hello world. This is a test.")
        assert topic == "general"

    def test_analyze_returns_full_dict(self):
        result = self.detector.analyze(SCIENCE_TEXT)
        assert "topic" in result
        assert "difficulty" in result
        assert "word_count" in result
        assert "avg_sentence_length" in result
        assert result["word_count"] > 0


# ── Run Tests ─────────────────────────────────────────────────────────── #

if __name__ == "__main__":
    import traceback

    test_classes = [TestTextChunker, TestKeywordExtractor, TestTopicDetector]
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

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")