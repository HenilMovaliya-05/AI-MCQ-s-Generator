"""
tests/test_pipeline.py
----------------------
Tests for post-processing and the full pipeline (mocked GenAI).
Run with: python -m pytest tests/test_pipeline.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.postprocessor import MCQPostProcessor
from genai.prompt_builder import PromptBuilder


# ── Sample MCQ fixtures ───────────────────────────────────────────────── #

VALID_MCQ = {
    "question": "What is the primary function of chlorophyll in photosynthesis?",
    "options": {
        "A": "To absorb water from the soil",
        "B": "To capture light energy from the sun",
        "C": "To produce carbon dioxide",
        "D": "To store glucose in the roots",
    },
    "correct_answer": "B",
    "explanation": "Chlorophyll is the green pigment that absorbs sunlight to drive photosynthesis.",
    "difficulty": "medium",
    "topic": "science",
}

DUPLICATE_MCQ = {
    "question": "What is the main function of chlorophyll during photosynthesis?",
    "options": {
        "A": "Absorb water from the roots",
        "B": "Capture sunlight energy",
        "C": "Release carbon dioxide",
        "D": "Store glucose underground",
    },
    "correct_answer": "B",
    "explanation": "Chlorophyll captures light energy.",
    "difficulty": "medium",
    "topic": "science",
}

MALFORMED_MCQ_MISSING_QUESTION = {
    "question": "",
    "options": {"A": "Yes", "B": "No", "C": "Maybe", "D": "Never"},
    "correct_answer": "A",
    "explanation": "Some explanation.",
    "difficulty": "easy",
    "topic": "general",
}

MALFORMED_MCQ_WRONG_ANSWER_KEY = {
    "question": "Which gas do plants absorb during photosynthesis?",
    "options": {"A": "Oxygen", "B": "Nitrogen", "C": "Carbon dioxide", "D": "Helium"},
    "correct_answer": "Z",  # 'Z' doesn't exist in options
    "explanation": "Plants absorb CO2.",
    "difficulty": "easy",
    "topic": "science",
}

MCQ_WITH_DIRTY_TEXT = {
    "question": "   what  is photosynthesis?   ",
    "options": {
        "A": "  a process  in plants   ",
        "B": "a type of animal movement",
        "C": "a chemical weapon",
        "D": "a form of digestion",
    },
    "correct_answer": "A",
    "explanation": "photosynthesis is a process in plants.",
    "difficulty": "easy",
    "topic": "science",
}


# ── MCQPostProcessor Tests ────────────────────────────────────────────── #

class TestMCQPostProcessor:
    def setup_method(self):
        self.processor = MCQPostProcessor(similarity_threshold=0.75)

    def test_valid_mcq_passes_through(self):
        result = self.processor.process([VALID_MCQ])
        assert len(result) == 1

    def test_malformed_missing_question_is_removed(self):
        result = self.processor.process([MALFORMED_MCQ_MISSING_QUESTION])
        assert len(result) == 0

    def test_malformed_wrong_answer_key_is_removed(self):
        result = self.processor.process([MALFORMED_MCQ_WRONG_ANSWER_KEY])
        assert len(result) == 0

    def test_duplicate_questions_are_removed(self):
        result = self.processor.process([VALID_MCQ, DUPLICATE_MCQ])
        assert len(result) == 1, "Duplicate should be removed"

    def test_text_cleaning_strips_whitespace(self):
        result = self.processor.process([MCQ_WITH_DIRTY_TEXT])
        assert len(result) == 1
        question = result[0]["question"]
        assert "  " not in question, "Double spaces should be removed"
        assert question == question.strip(), "Leading/trailing whitespace should be gone"

    def test_text_cleaning_capitalizes_question(self):
        result = self.processor.process([MCQ_WITH_DIRTY_TEXT])
        assert result[0]["question"][0].isupper()

    def test_filter_by_difficulty_easy(self):
        mcqs = [VALID_MCQ, MCQ_WITH_DIRTY_TEXT]
        processed = self.processor.process(mcqs)
        easy = self.processor.filter_by_difficulty(processed, "easy")
        for m in easy:
            assert m["difficulty"] == "easy"

    def test_filter_by_difficulty_mixed_returns_all(self):
        mcqs = self.processor.process([VALID_MCQ, MCQ_WITH_DIRTY_TEXT])
        result = self.processor.filter_by_difficulty(mcqs, "mixed")
        assert len(result) == len(mcqs)

    def test_get_stats_returns_correct_total(self):
        mcqs = self.processor.process([VALID_MCQ])
        stats = self.processor.get_stats(mcqs)
        assert stats["total"] == 1

    def test_get_stats_empty_list(self):
        stats = self.processor.get_stats([])
        assert stats["total"] == 0

    def test_get_stats_has_difficulty_breakdown(self):
        mcqs = self.processor.process([VALID_MCQ])
        stats = self.processor.get_stats(mcqs)
        assert "by_difficulty" in stats
        assert "medium" in stats["by_difficulty"]

    def test_process_empty_input(self):
        result = self.processor.process([])
        assert result == []

    def test_correct_answer_preserved(self):
        result = self.processor.process([VALID_MCQ])
        assert result[0]["correct_answer"] == "B"

    def test_options_preserved(self):
        result = self.processor.process([VALID_MCQ])
        assert set(result[0]["options"].keys()) == {"A", "B", "C", "D"}


# ── PromptBuilder Tests ───────────────────────────────────────────────── #

class TestPromptBuilder:
    def setup_method(self):
        self.builder = PromptBuilder()

    def test_prompt_contains_chunk(self):
        chunk = "Photosynthesis uses sunlight."
        prompt = self.builder.build_mcq_prompt(chunk, ["sunlight"], "science", "easy", 3)
        assert chunk in prompt

    def test_prompt_contains_keywords(self):
        keywords = ["chlorophyll", "glucose", "sunlight"]
        prompt = self.builder.build_mcq_prompt("Some text.", keywords, "science", "medium", 3)
        for kw in keywords:
            assert kw in prompt

    def test_prompt_contains_topic(self):
        prompt = self.builder.build_mcq_prompt("Some text.", [], "history", "hard", 2)
        assert "history" in prompt

    def test_prompt_contains_difficulty(self):
        prompt = self.builder.build_mcq_prompt("Some text.", [], "science", "hard", 2)
        assert "hard" in prompt

    def test_prompt_specifies_num_questions(self):
        prompt = self.builder.build_mcq_prompt("Some text.", [], "general", "medium", 5)
        assert "5" in prompt

    def test_prompt_requests_json_output(self):
        prompt = self.builder.build_mcq_prompt("Some text.", [], "general", "easy", 2)
        assert "JSON" in prompt

    def test_prompt_contains_difficulty_guidance_easy(self):
        prompt = self.builder.build_mcq_prompt("Text.", [], "general", "easy", 1)
        assert "definition" in prompt.lower() or "recall" in prompt.lower()

    def test_prompt_contains_difficulty_guidance_hard(self):
        prompt = self.builder.build_mcq_prompt("Text.", [], "general", "hard", 1)
        assert "analysis" in prompt.lower() or "critical" in prompt.lower()

    def test_empty_keywords_handled(self):
        prompt = self.builder.build_mcq_prompt("Some text.", [], "science", "medium", 3)
        assert "not specified" in prompt

    def test_validation_prompt_contains_question(self):
        prompt = self.builder.build_validation_prompt(VALID_MCQ)
        assert VALID_MCQ["question"] in prompt


# ── Run Tests ─────────────────────────────────────────────────────────── #

if __name__ == "__main__":
    test_classes = [TestMCQPostProcessor, TestPromptBuilder]
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