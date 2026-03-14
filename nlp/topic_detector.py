"""
nlp/topic_detector.py
----------------------
Detects the topic and assigns a difficulty level to each text chunk.
Uses heuristics and keyword matching — no external models required.
"""

import re
from collections import Counter


# ------------------------------------------------------------------ #
# Domain keyword maps for topic detection                              #
# ------------------------------------------------------------------ #
TOPIC_KEYWORDS = {
    "science": [
        "cell", "atom", "molecule", "energy", "force", "chemical", "biology",
        "physics", "chemistry", "experiment", "hypothesis", "evolution",
        "dna", "protein", "enzyme", "reaction", "photosynthesis", "gravity",
        "electron", "nucleus", "organism", "ecosystem", "element",
    ],
    "history": [
        "war", "revolution", "empire", "king", "queen", "century", "ancient",
        "civilization", "treaty", "colony", "independence", "government",
        "democracy", "republic", "battle", "period", "era", "historical",
        "nation", "president", "parliament", "constitution",
    ],
    "technology": [
        "software", "algorithm", "computer", "network", "database", "api",
        "machine learning", "artificial intelligence", "data", "programming",
        "code", "system", "server", "cloud", "internet", "digital",
        "application", "processor", "memory", "interface", "protocol",
    ],
    "mathematics": [
        "equation", "theorem", "proof", "function", "derivative", "integral",
        "matrix", "vector", "probability", "statistics", "geometry", "algebra",
        "calculus", "polynomial", "formula", "variable", "constant", "graph",
        "series", "sequence", "limit", "infinity",
    ],
    "economics": [
        "market", "supply", "demand", "price", "inflation", "gdp", "trade",
        "currency", "investment", "capital", "labor", "monopoly", "economy",
        "fiscal", "monetary", "interest", "bank", "profit", "cost", "revenue",
    ],
    "literature": [
        "novel", "poem", "author", "character", "plot", "theme", "narrative",
        "metaphor", "symbolism", "genre", "prose", "verse", "fiction",
        "protagonist", "antagonist", "imagery", "tone", "style", "literary",
    ],
    "geography": [
        "continent", "country", "ocean", "river", "mountain", "climate",
        "population", "region", "latitude", "longitude", "terrain", "coast",
        "desert", "forest", "city", "capital", "border", "island", "valley",
    ],
    "medicine": [
        "disease", "symptom", "diagnosis", "treatment", "drug", "surgery",
        "patient", "hospital", "virus", "bacteria", "immune", "vaccine",
        "organ", "tissue", "blood", "nerve", "therapy", "chronic", "acute",
    ],
}

# ------------------------------------------------------------------ #
# Difficulty indicators                                                #
# ------------------------------------------------------------------ #
EASY_SIGNALS = [
    "simple", "basic", "introduction", "overview", "define", "definition",
    "what is", "example of", "type of", "kinds of", "common", "general",
]

HARD_SIGNALS = [
    "mechanism", "analysis", "synthesis", "evaluate", "complex", "advanced",
    "derive", "prove", "compare", "contrast", "implication", "consequence",
    "critical", "hypothesis", "theoretical", "quantitative", "molecular",
]

SENTENCE_COMPLEXITY_THRESHOLD = 20  # avg words per sentence


class TopicDetector:
    """
    Detects topic category and assigns difficulty to a text chunk.
    """

    def detect_topic(self, text: str) -> str:
        """
        Returns the best-matching topic label for the text.
        Falls back to 'general' if no match is strong enough.
        """
        text_lower = text.lower()
        scores = {}

        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[topic] = score

        best_topic, best_score = max(scores.items(), key=lambda x: x[1])

        return best_topic if best_score >= 2 else "general"

    def detect_difficulty(self, text: str) -> str:
        """
        Estimates difficulty as 'easy', 'medium', or 'hard' based on:
        - Presence of complexity signal words
        - Average sentence length
        - Vocabulary richness (type-token ratio)
        """
        text_lower = text.lower()

        easy_hits = sum(1 for sig in EASY_SIGNALS if sig in text_lower)
        hard_hits = sum(1 for sig in HARD_SIGNALS if sig in text_lower)

        avg_sentence_len = self._avg_sentence_length(text)
        ttr = self._type_token_ratio(text)

        # Scoring heuristic
        difficulty_score = 0
        difficulty_score += hard_hits * 2
        difficulty_score -= easy_hits * 2

        if avg_sentence_len > SENTENCE_COMPLEXITY_THRESHOLD:
            difficulty_score += 2
        elif avg_sentence_len < 12:
            difficulty_score -= 1

        if ttr > 0.65:
            difficulty_score += 1
        elif ttr < 0.45:
            difficulty_score -= 1

        if difficulty_score >= 3:
            return "hard"
        elif difficulty_score <= -1:
            return "easy"
        else:
            return "medium"

    def analyze(self, text: str) -> dict:
        """
        Returns full analysis of a chunk: topic, difficulty, and stats.
        """
        return {
            "topic": self.detect_topic(text),
            "difficulty": self.detect_difficulty(text),
            "word_count": len(text.split()),
            "sentence_count": len(re.findall(r'[.!?]+', text)),
            "avg_sentence_length": round(self._avg_sentence_length(text), 1),
            "vocabulary_richness": round(self._type_token_ratio(text), 2),
        }

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _avg_sentence_length(self, text: str) -> float:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0
        total_words = sum(len(s.split()) for s in sentences)
        return total_words / len(sentences)

    def _type_token_ratio(self, text: str) -> float:
        """Vocabulary richness: unique words / total words."""
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        if not words:
            return 0.0
        return len(set(words)) / len(words)