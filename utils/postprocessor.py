"""
utils/postprocessor.py
-----------------------
NLP-based post-processing for quality control on generated MCQs.
Handles: deduplication, grammar checks, difficulty filtering, validation.
"""

import re
from difflib import SequenceMatcher


class MCQPostProcessor:
    """
    Cleans, validates, and deduplicates MCQs after GenAI generation.
    This is the 'NLP post-processing' stage of the hybrid pipeline.
    """

    def __init__(self, similarity_threshold: float = 0.75):
        """
        Args:
            similarity_threshold: Questions with similarity > this are considered duplicates.
        """
        self.similarity_threshold = similarity_threshold

    def process(self, mcqs: list[dict]) -> list[dict]:
        """
        Run the full post-processing pipeline on a list of MCQs.

        Steps:
          1. Basic validation (remove malformed MCQs)
          2. Text cleaning (strip extra whitespace, fix casing)
          3. Deduplication (remove similar questions)
          4. Option validation (check 4 options, correct answer valid)

        Returns:
            Cleaned, validated, deduplicated MCQ list.
        """
        if not mcqs:
            return []

        # Step 1: Validate structure
        valid = [m for m in mcqs if self._is_valid(m)]

        # Step 2: Clean text
        cleaned = [self._clean(m) for m in valid]

        # Step 3: Deduplicate
        deduplicated = self._deduplicate(cleaned)

        # Step 4: Validate answer consistency
        final = [m for m in deduplicated if self._answer_is_consistent(m)]

        return final

    def filter_by_difficulty(self, mcqs: list[dict], target: str) -> list[dict]:
        """Return only MCQs matching the target difficulty level."""
        if target == "mixed":
            return mcqs
        return [m for m in mcqs if m.get("difficulty", "").lower() == target.lower()]

    def get_stats(self, mcqs: list[dict]) -> dict:
        """Return summary statistics for the generated MCQ set."""
        if not mcqs:
            return {"total": 0}

        difficulties = [m.get("difficulty", "unknown") for m in mcqs]
        topics = [m.get("topic", "unknown") for m in mcqs]

        from collections import Counter
        return {
            "total": len(mcqs),
            "by_difficulty": dict(Counter(difficulties)),
            "by_topic": dict(Counter(topics)),
            "avg_question_length": round(
                sum(len(m.get("question", "").split()) for m in mcqs) / len(mcqs), 1
            ),
        }

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _is_valid(self, mcq: dict) -> bool:
        """Check if MCQ has minimum required fields."""
        return (
            bool(mcq.get("question", "").strip())
            and isinstance(mcq.get("options"), dict)
            and len(mcq.get("options", {})) >= 4
            and bool(mcq.get("correct_answer", "").strip())
            and bool(mcq.get("explanation", "").strip())
        )

    def _clean(self, mcq: dict) -> dict:
        """Clean whitespace and normalize text fields."""
        def clean_str(s: str) -> str:
            s = re.sub(r'\s+', ' ', s).strip()
            # Capitalize first letter
            return s[0].upper() + s[1:] if s else s

        options = {
            k: clean_str(v) for k, v in mcq.get("options", {}).items()
        }

        return {
            **mcq,
            "question": clean_str(mcq.get("question", "")),
            "options": options,
            "correct_answer": mcq.get("correct_answer", "").upper().strip(),
            "explanation": clean_str(mcq.get("explanation", "")),
        }

    def _deduplicate(self, mcqs: list[dict]) -> list[dict]:
        """Remove near-duplicate questions using string similarity."""
        unique = []
        for candidate in mcqs:
            is_duplicate = False
            cq = candidate.get("question", "").lower()
            for seen in unique:
                sq = seen.get("question", "").lower()
                similarity = SequenceMatcher(None, cq, sq).ratio()
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique.append(candidate)
        return unique

    def _answer_is_consistent(self, mcq: dict) -> bool:
        """Ensure the correct_answer key exists in the options."""
        correct = mcq.get("correct_answer", "").upper()
        options = mcq.get("options", {})
        return correct in options and bool(options.get(correct, "").strip())