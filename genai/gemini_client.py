# """
# genai/gemini_client.py
# ----------------------
# Handles all communication with the Google Gemini API.
# Includes retry logic, response parsing, and error handling.
# """

# import json
# import time
# import re
# import os


# class GeminiClient:
#     """
#     Wrapper around Google Generative AI (Gemini) for MCQ generation.
#     """

#     def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash-lite"):
#         """
#         Args:
#             api_key: Gemini API key. Reads from GEMINI_API_KEY env var if not provided.
#             model:   Gemini model name.
#         """
#         try:
#             import google.generativeai as genai
#         except ImportError:
#             raise ImportError(
#                 "google-genai is not installed.\n"
#                 "Run: pip install google-genai"
#             )

#         self.api_key = api_key or os.getenv("GEMINI_API_KEY")
#         if not self.api_key:
#             raise ValueError(
#                 "No Gemini API key found.\n"
#                 "Set GEMINI_API_KEY in your .env file or pass it directly."
#             )

#         genai.configure(api_key=self.api_key)
#         self.model = genai.GenerativeModel(model)
#         self.model_name = model

#         # Generation config
#         self.generation_config = genai.types.GenerationConfig(
#             temperature=0.7,       # Some creativity but not too random
#             top_p=0.9,
#             max_output_tokens=2048,
#         )

#     def generate_mcqs(self, prompt: str, retries: int = 3) -> list[dict]:
#         """
#         Send a prompt to Gemini and parse the MCQ response.

#         Args:
#             prompt:  The structured prompt from PromptBuilder.
#             retries: Number of retry attempts on failure.

#         Returns:
#             List of MCQ dicts, each with question/options/correct_answer/explanation.
#         """
#         for attempt in range(1, retries + 1):
#             try:
#                 response = self.model.generate_content(
#                     prompt,
#                     generation_config=self.generation_config,
#                 )
#                 raw_text = response.text
#                 return self._parse_json_response(raw_text)

#             except Exception as e:
#                 error_msg = str(e)
#                 print(f"  [Gemini] Attempt {attempt}/{retries} failed: {error_msg}")

#                 if "429" in error_msg or "quota" in error_msg.lower():
#                     wait = 2 ** attempt  # exponential backoff
#                     print(f"  [Gemini] Rate limited. Waiting {wait}s...")
#                     time.sleep(wait)
#                 elif attempt == retries:
#                     raise RuntimeError(
#                         f"Gemini API failed after {retries} attempts: {error_msg}"
#                     )
#                 else:
#                     time.sleep(1)

#         return []

#     # ------------------------------------------------------------------ #
#     # Private: Response parsing                                           #
#     # ------------------------------------------------------------------ #

#     def _parse_json_response(self, raw_text: str) -> list[dict]:
#         """
#         Parse Gemini's response text into a list of MCQ dicts.
#         Handles common formatting issues (markdown code blocks, extra text).
#         """
#         # Strip markdown code fences if present
#         text = raw_text.strip()
#         text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
#         text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
#         text = text.strip()

#         # Extract JSON array if buried in extra text
#         match = re.search(r'\[.*\]', text, re.DOTALL)
#         if match:
#             text = match.group(0)

#         try:
#             data = json.loads(text)
#         except json.JSONDecodeError as e:
#             # Try to fix common issues
#             text = self._attempt_json_repair(text)
#             try:
#                 data = json.loads(text)
#             except json.JSONDecodeError:
#                 raise ValueError(
#                     f"Could not parse Gemini response as JSON.\n"
#                     f"JSON error: {e}\n"
#                     f"Raw response:\n{raw_text[:500]}"
#                 )

#         if not isinstance(data, list):
#             data = [data]

#         return [self._validate_mcq_structure(mcq) for mcq in data if isinstance(mcq, dict)]

#     def _validate_mcq_structure(self, mcq: dict) -> dict:
#         """Ensure MCQ has all required fields. Fill defaults if missing."""
#         return {
#             "question": mcq.get("question", "").strip(),
#             "options": mcq.get("options", {"A": "", "B": "", "C": "", "D": ""}),
#             "correct_answer": mcq.get("correct_answer", "A").upper().strip(),
#             "explanation": mcq.get("explanation", "").strip(),
#             "difficulty": mcq.get("difficulty", "medium"),
#             "topic": mcq.get("topic", "general"),
#         }

#     def _attempt_json_repair(self, text: str) -> str:
#         """Attempt basic JSON repairs for common Gemini output issues."""
#         # Remove trailing commas before ] or }
#         text = re.sub(r',\s*([\]}])', r'\1', text)
#         # Ensure string ends with ]
#         if not text.rstrip().endswith(']'):
#             text = text.rstrip().rstrip(',') + ']'
#         return text

# limit the auto request to 1 request per second to avoid hitting rate limits

"""
genai/gemini_client.py
----------------------
Handles all communication with the Google Gemini API.
Uses the new `google-genai` SDK (replaces deprecated `google-generativeai`).
Includes retry logic, smart rate-limit handling, and response parsing.
"""

import json
import time
import re
import os


class GeminiClient:
    """
    Wrapper around Google GenAI (Gemini) for MCQ generation.
    Uses the new google-genai SDK (google.genai).
    """

    def __init__(self, api_key: str = None, model: str = None):
        """
        Args:
            api_key: Gemini API key. Reads from GEMINI_API_KEY env var if not provided.
            model:   Gemini model name. Reads from GEMINI_MODEL env var if not provided.
        """
        try:
            from google import genai
            from google.genai import types
            self._genai = genai
            self._types = types
        except ImportError:
            raise ImportError(
                "google-genai is not installed.\n"
                "Run: pip install google-genai"
            )

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No Gemini API key found.\n"
                "Set GEMINI_API_KEY in your .env file or pass it directly."
            )

        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

        # Initialize the new client
        self.client = self._genai.Client(api_key=self.api_key)

        print(f"  [Gemini] Using model: {self.model_name}")

    def generate_mcqs(self, prompt: str, retries: int = 3) -> list[dict]:
        """
        Send a prompt to Gemini and parse the MCQ response.

        Args:
            prompt:  The structured prompt from PromptBuilder.
            retries: Number of retry attempts on failure.

        Returns:
            List of MCQ dicts with question/options/correct_answer/explanation.
        """
        for attempt in range(1, retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self._types.GenerateContentConfig(
                        temperature=0.7,
                        top_p=0.9,
                        max_output_tokens=2048,
                    ),
                )
                raw_text = response.text
                return self._parse_json_response(raw_text)

            except Exception as e:
                error_msg = str(e)

                # Rate limit / quota exceeded
                if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                    # Try to extract the retry delay from the error message
                    retry_secs = self._extract_retry_delay(error_msg)

                    if retry_secs and retry_secs > 60:
                        # Daily quota exhausted — no point retrying
                        print(f"\n  ❌ [Gemini] Daily quota exhausted for '{self.model_name}'.")
                        print(f"     Suggested fix: switch to 'gemini-2.0-flash-lite' in your .env")
                        print(f"     Or wait {retry_secs}s (~{retry_secs//60} min) for quota reset.\n")
                        raise RuntimeError(
                            f"Daily quota exhausted for model '{self.model_name}'.\n"
                            f"Change GEMINI_MODEL=gemini-2.0-flash-lite in your .env file."
                        )

                    # Short wait — retry makes sense
                    wait = retry_secs if retry_secs else (2 ** attempt)
                    print(f"  [Gemini] Attempt {attempt}/{retries} rate limited. Waiting {wait}s...")
                    time.sleep(wait)

                elif attempt == retries:
                    raise RuntimeError(
                        f"Gemini API failed after {retries} attempts: {error_msg}"
                    )
                else:
                    print(f"  [Gemini] Attempt {attempt}/{retries} failed: {error_msg[:120]}")
                    time.sleep(1)

        return []

    # ------------------------------------------------------------------ #
    # Private: retry delay extraction                                      #
    # ------------------------------------------------------------------ #

    def _extract_retry_delay(self, error_msg: str) -> int:
        """Extract the suggested retry delay in seconds from the error message."""
        # Matches: "retry_delay { seconds: 56 }" or "Please retry in 56.97s"
        match = re.search(r'seconds[:\s]+(\d+)', error_msg)
        if match:
            return int(match.group(1))
        match = re.search(r'retry in (\d+)', error_msg)
        if match:
            return int(match.group(1))
        return None

    # ------------------------------------------------------------------ #
    # Private: response parsing                                            #
    # ------------------------------------------------------------------ #

    def _parse_json_response(self, raw_text: str) -> list[dict]:
        """
        Parse Gemini's response text into a list of MCQ dicts.
        Handles markdown code fences and extra text gracefully.
        """
        text = raw_text.strip()

        # Strip markdown code fences if present
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
        text = text.strip()

        # Extract JSON array if buried in extra text
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            text = self._attempt_json_repair(text)
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                raise ValueError(
                    f"Could not parse Gemini response as JSON.\n"
                    f"Error: {e}\nRaw response:\n{raw_text[:500]}"
                )

        if not isinstance(data, list):
            data = [data]

        return [self._validate_mcq_structure(mcq) for mcq in data if isinstance(mcq, dict)]

    def _validate_mcq_structure(self, mcq: dict) -> dict:
        """Ensure MCQ has all required fields. Fill defaults if missing."""
        return {
            "question":       mcq.get("question", "").strip(),
            "options":        mcq.get("options", {"A": "", "B": "", "C": "", "D": ""}),
            "correct_answer": mcq.get("correct_answer", "A").upper().strip(),
            "explanation":    mcq.get("explanation", "").strip(),
            "difficulty":     mcq.get("difficulty", "medium"),
            "topic":          mcq.get("topic", "general"),
        }

    def _attempt_json_repair(self, text: str) -> str:
        """Attempt basic JSON repairs for common Gemini output issues."""
        text = re.sub(r',\s*([\]}])', r'\1', text)
        if not text.rstrip().endswith(']'):
            text = text.rstrip().rstrip(',') + ']'
        return text 