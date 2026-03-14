"""
nlp/keyword_extractor.py
------------------------
Extracts keywords and named entities from text chunks using
TF-IDF (no external model needed) with an optional KeyBERT upgrade.
"""

import re
import math
from collections import Counter


# ------------------------------------------------------------------ #
# Stopwords (lightweight built-in list — no NLTK required)            #
# ------------------------------------------------------------------ #
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "need", "dare",
    "used", "ought", "to", "of", "in", "on", "at", "by", "for", "with",
    "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "out", "off", "over",
    "under", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "but", "and", "or", "if", "while", "this",
    "that", "these", "those", "it", "its", "i", "me", "my", "we", "our",
    "you", "your", "he", "she", "they", "them", "their", "what", "which",
    "who", "whom", "also", "as", "because", "since", "although", "though",
    "however", "therefore", "thus", "hence", "moreover", "furthermore",
}


class KeywordExtractor:
    """
    Extracts the most important keywords from text using TF-IDF scoring.
    Falls back gracefully — no external models required.
    Optionally upgrades to KeyBERT if installed.
    """

    def __init__(self, top_n: int = 8, use_keybert: bool = False):
        """
        Args:
            top_n:       Maximum keywords to return per chunk.
            use_keybert: Try to use KeyBERT (requires installation).
        """
        self.top_n = top_n
        self.use_keybert = use_keybert
        self._keybert_model = None

        if use_keybert:
            try:
                from keybert import KeyBERT
                self._keybert_model = KeyBERT()
                print("[KeywordExtractor] Using KeyBERT for extraction.")
            except ImportError:
                print("[KeywordExtractor] KeyBERT not installed. Falling back to TF-IDF.")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def extract(self, chunk: str, all_chunks: list[str] = None) -> list[str]:
        """
        Extract top keywords from a single chunk.

        Args:
            chunk:      The text to extract keywords from.
            all_chunks: Optionally pass all chunks for better TF-IDF scoring.

        Returns:
            List of keyword strings.
        """
        if self._keybert_model:
            return self._keybert_extract(chunk)

        corpus = all_chunks if all_chunks else [chunk]
        return self._tfidf_extract(chunk, corpus)

    def extract_named_entities(self, text: str) -> list[str]:
        """
        Simple regex-based named entity extraction.
        Finds capitalized multi-word phrases (e.g., "World War II", "DNA replication").
        """
        # Find capitalized phrases (2-4 words)
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
        matches = re.findall(pattern, text)

        # Also find acronyms (2-5 uppercase letters)
        acronym_pattern = r'\b([A-Z]{2,5})\b'
        acronyms = re.findall(acronym_pattern, text)

        entities = list(set(matches + acronyms))
        return entities[:self.top_n]

    def extract_full(self, chunk: str, all_chunks: list[str] = None) -> dict:
        """
        Returns both keywords and named entities combined.
        """
        keywords = self.extract(chunk, all_chunks)
        entities = self.extract_named_entities(chunk)

        # Combine, deduplicate, limit
        combined = list(dict.fromkeys(keywords + entities))
        return {
            "keywords": keywords,
            "entities": entities,
            "combined": combined[:self.top_n + 4],
        }

    # ------------------------------------------------------------------ #
    # Private methods                                                      #
    # ------------------------------------------------------------------ #

    def _tfidf_extract(self, chunk: str, corpus: list[str]) -> list[str]:
        """TF-IDF keyword extraction without external libraries."""
        tokens = self._tokenize(chunk)
        tf_scores = self._term_frequency(tokens)

        # Build IDF from corpus
        doc_count = len(corpus)
        idf_scores = {}
        all_tokens = set(tokens)

        for term in all_tokens:
            doc_freq = sum(1 for doc in corpus if term in self._tokenize(doc))
            idf_scores[term] = math.log((doc_count + 1) / (doc_freq + 1)) + 1

        # TF-IDF score
        tfidf = {
            term: tf_scores[term] * idf_scores.get(term, 1.0)
            for term in tf_scores
            if term not in STOPWORDS and len(term) > 3
        }

        # Sort and return top N
        ranked = sorted(tfidf.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in ranked[:self.top_n]]

    def _keybert_extract(self, chunk: str) -> list[str]:
        """Use KeyBERT if available."""
        results = self._keybert_model.extract_keywords(
            chunk,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=self.top_n,
        )
        return [kw for kw, _ in results]

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase, remove punctuation, split to words."""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return text.split()

    def _term_frequency(self, tokens: list[str]) -> dict:
        """Compute normalized TF scores."""
        total = len(tokens)
        if total == 0:
            return {}
        counts = Counter(tokens)
        return {term: count / total for term, count in counts.items()}