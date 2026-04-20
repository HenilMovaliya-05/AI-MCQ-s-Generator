"""
api/models.py
-------------
Pydantic models for FastAPI request validation and response serialization.
These define the exact shape of API input and output.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ================================================================== 
# Request Models                                                       

class TextRequest(BaseModel):
    """Request body for POST /generate/text"""

    text: str = Field(
        ...,
        min_length=50,
        max_length=50000,
        description="The text passage to generate MCQs from.",
        examples=["Photosynthesis is the process by which plants use sunlight..."],
    )
    num_questions: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Number of MCQs to generate. Must be between 1 and 30.",
        examples=[5],
    )
    difficulty: str = Field(
        default="mixed",
        description="Difficulty level: easy | medium | hard | mixed",
        examples=["mixed"],
    )

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v):
        valid = ["easy", "medium", "hard", "mixed"]
        if v.lower() not in valid:
            raise ValueError(f"difficulty must be one of {valid}")
        return v.lower()

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of glucose. This process takes place in the chloroplasts of plant cells using a green pigment called chlorophyll.",
                "num_questions": 3,
                "difficulty": "medium",
            }
        }
    }


# ================================================================== 
# Response Models                                                      

class MCQResponse(BaseModel):
    """A single MCQ object returned in the API response."""

    question: str = Field(
        ...,
        description="The question text.",
    )
    options: dict = Field(
        ...,
        description="Four answer options as A, B, C, D keys.",
        examples=[{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}],
    )
    correct_answer: str = Field(
        ...,
        description="The key of the correct answer (A, B, C, or D).",
        examples=["B"],
    )
    explanation: str = Field(
        ...,
        description="Brief explanation of why the answer is correct.",
    )
    difficulty: str = Field(
        default="medium",
        description="Difficulty level of this question.",
    )
    topic: str = Field(
        default="general",
        description="Detected topic domain of this question.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "What is the primary function of chlorophyll in photosynthesis?",
                "options": {
                    "A": "To absorb water from the soil",
                    "B": "To capture light energy from the sun",
                    "C": "To produce carbon dioxide",
                    "D": "To store glucose in the roots",
                },
                "correct_answer": "B",
                "explanation": "Chlorophyll captures sunlight energy which drives the photosynthesis process.",
                "difficulty": "medium",
                "topic": "science",
            }
        }
    }


class GenerationResult(BaseModel):
    """Full response for a successful MCQ generation request."""

    success: bool = Field(
        default=True,
        description="Whether the generation was successful.",
    )
    total_generated: int = Field(
        ...,
        description="Total number of MCQs generated.",
    )
    time_taken_seconds: float = Field(
        ...,
        description="Time taken to generate MCQs in seconds.",
    )
    difficulty: str = Field(
        ...,
        description="Difficulty level used for generation.",
    )
    source_filename: Optional[str] = Field(
        default=None,
        description="Name of the uploaded PDF file (if applicable).",
    )
    mcqs: list[MCQResponse] = Field(
        ...,
        description="List of generated MCQ objects.",
    )


class HealthResponse(BaseModel):
    """Response for GET /health endpoint."""

    status: str = Field(
        ...,
        description="API health status: healthy | degraded",
        examples=["healthy"],
    )
    api_key_configured: bool = Field(
        ...,
        description="Whether the Gemini API key is set.",
    )
    model: str = Field(
        ...,
        description="Currently configured Gemini model.",
    )
    message: str = Field(
        ...,
        description="Human readable status message.",
    )


class ErrorResponse(BaseModel):
    """Standard error response shape."""

    success: bool = False
    error: str = Field(..., description="Error message.")
    detail: Optional[str] = Field(default=None, description="Additional error detail.")