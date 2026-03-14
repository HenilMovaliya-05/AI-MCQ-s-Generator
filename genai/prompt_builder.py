"""
genai/prompt_builder.py
------------------------
Constructs rich, structured prompts from NLP analysis output.
This is the critical bridge between the NLP layer and the GenAI API.
Better prompts = better MCQs.
"""


class PromptBuilder:
    """
    Builds structured prompts for MCQ generation using NLP-extracted metadata.
    """

    def build_mcq_prompt(
        self,
        chunk: str,
        keywords: list[str],
        topic: str,
        difficulty: str,
        num_questions: int = 3,
    ) -> str:
        """
        Build the main MCQ generation prompt.

        Args:
            chunk:         The text passage to generate MCQs from.
            keywords:      Top keywords extracted by NLP layer.
            topic:         Detected topic (e.g., 'science', 'history').
            difficulty:    Difficulty level: easy / medium / hard.
            num_questions: Number of MCQs to generate.

        Returns:
            A detailed prompt string ready to send to Gemini.
        """
        keyword_str = ", ".join(keywords) if keywords else "not specified"
        difficulty_guide = self._difficulty_guidance(difficulty)

        prompt = f"""You are an expert educational assessment designer. Your task is to generate high-quality Multiple Choice Questions (MCQs) from the given passage.

## PASSAGE:
{chunk}

## CONTEXT (extracted by NLP analysis):
- Topic domain: {topic}
- Key concepts: {keyword_str}
- Difficulty level: {difficulty}

## DIFFICULTY GUIDANCE:
{difficulty_guide}

## INSTRUCTIONS:
Generate exactly {num_questions} MCQs from this passage. Follow these strict rules:

1. Each question must be clearly answerable from the passage.
2. The correct answer must be unambiguously supported by the text.
3. Generate 3 distractors (wrong options) that are:
   - Plausible and related to the topic (not obviously wrong)
   - Similar in length and grammatical structure to the correct answer
   - Based on common misconceptions or related-but-wrong facts
4. Do NOT use "All of the above" or "None of the above".
5. Shuffle the correct answer position across A/B/C/D randomly.
6. Include a brief explanation for why the correct answer is right.

## OUTPUT FORMAT (strict JSON):
Return ONLY a valid JSON array. No markdown, no extra text, no code blocks.

[
  {{
    "question": "Question text here?",
    "options": {{
      "A": "Option A text",
      "B": "Option B text",
      "C": "Option C text",
      "D": "Option D text"
    }},
    "correct_answer": "A",
    "explanation": "Brief explanation of why this is correct.",
    "difficulty": "{difficulty}",
    "topic": "{topic}"
  }}
]"""
        return prompt

    def build_validation_prompt(self, mcq: dict) -> str:
        """
        Prompt to ask Gemini to validate and fix a generated MCQ.
        Used in the post-processing quality check step.
        """
        return f"""Review this MCQ and fix any issues:

Question: {mcq.get('question')}
Options: {mcq.get('options')}
Correct Answer: {mcq.get('correct_answer')}
Explanation: {mcq.get('explanation')}

Check for:
1. Is the question grammatically correct?
2. Is the correct answer truly correct?
3. Are distractors plausible but wrong?
4. Is the explanation accurate?

Return the corrected MCQ as a single JSON object in the same format. If no fixes needed, return it unchanged."""

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _difficulty_guidance(self, difficulty: str) -> str:
        guides = {
            "easy": (
                "- Ask about definitions, basic facts, or simple recall.\n"
                "- Questions should test whether the student read the passage.\n"
                "- Use straightforward language with no ambiguity.\n"
                "- Example stem: 'What is...?', 'Which of the following is...?'"
            ),
            "medium": (
                "- Ask about relationships, comparisons, or applied concepts.\n"
                "- Require the student to understand, not just recall.\n"
                "- Moderate vocabulary; some inference required.\n"
                "- Example stem: 'Which best explains...?', 'What is the effect of...?'"
            ),
            "hard": (
                "- Ask about mechanisms, causes, implications, or critical analysis.\n"
                "- Require higher-order thinking: analysis, evaluation, synthesis.\n"
                "- May require combining information from multiple parts of the passage.\n"
                "- Example stem: 'Which conclusion can be drawn...?', 'What would happen if...?'"
            ),
        }
        return guides.get(difficulty, guides["medium"])