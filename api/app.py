"""
api/app.py
----------
FastAPI application for the AI MCQ Generator.
Exposes REST API endpoints for MCQ generation from text or PDF.

Endpoints:
  GET  /                     → Health check + API info
  GET  /health               → Health status
  POST /generate/text        → Generate MCQs from plain text
  POST /generate/pdf         → Generate MCQs from uploaded PDF
  GET  /docs                 → Auto-generated Swagger UI (built-in)
  GET  /redoc                → ReDoc API documentation (built-in)
"""

import os
import sys
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from api.models import (
    TextRequest,
    MCQResponse,
    GenerationResult,
    HealthResponse,
    ErrorResponse,
)

# Add project root to path so pipeline imports work
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import MCQPipeline
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI MCQ Generator API",
    description="""
## AI MCQ Generator — Hybrid NLP + Google Gemini Pipeline

A REST API that automatically generates Multiple Choice Questions
from PDF documents or plain text using a hybrid NLP + GenAI pipeline.

### Features
- **PDF & Text input** — upload a PDF or send raw text
- **Smart preprocessing** — TF-IDF keyword extraction, topic detection, difficulty scoring
- **Gemini-powered generation** — contextual questions with distractors and explanations
- **Multiple output formats** — JSON response or downloadable PDF

### Quick Start
1. Use **POST /generate/text** with a JSON body to generate from text
2. Use **POST /generate/pdf** with a file upload to generate from PDF
""",
    version="1.0.0",
    contact={
        "name": "AI MCQ Generator",
        "url": "https://github.com/HenilMovaliya-05/AI-MCQs-Generator",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS middleware (allows frontend to call this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # In production restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy pipeline initialization 
_pipeline: MCQPipeline = None

def get_pipeline() -> MCQPipeline:
    """Get or create the MCQ pipeline (singleton)."""
    global _pipeline
    if _pipeline is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY not configured. Set it in your .env file."
            )
        _pipeline = MCQPipeline(api_key=api_key)
    return _pipeline


# ================================================================== 
# Routes                                                               

@app.get(
    "/",
    response_model=dict,
    summary="API Info",
    tags=["General"],
)
async def root():
    """Returns basic API information and available endpoints."""
    return {
        "name": "AI MCQ Generator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health":          "GET  /health",
            "generate_text":   "POST /generate/text",
            "generate_pdf":    "POST /generate/pdf",
            "documentation":   "GET  /docs",
            "redoc":           "GET  /redoc",
        },
        "github": "https://github.com/HenilMovaliya-05/AI-MCQs-Generator",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    tags=["General"],
)
async def health_check():
    """Check if the API is running and Gemini API key is configured."""
    api_key_set = bool(os.getenv("GEMINI_API_KEY"))
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    return HealthResponse(
        status="healthy" if api_key_set else "degraded",
        api_key_configured=api_key_set,
        model=model,
        message="API is running. Gemini API key is configured." if api_key_set
                else "API is running but GEMINI_API_KEY is not set.",
    )


@app.post(
    "/generate/text",
    response_model=GenerationResult,
    summary="Generate MCQs from Text",
    tags=["Generation"],
    responses={
        200: {"description": "MCQs generated successfully"},
        400: {"description": "Invalid input"},
        500: {"description": "Generation failed"},
    },
)
async def generate_from_text(request: TextRequest):
    """
    Generate MCQs from plain text input.

    **Request body:**
    - `text` — the passage to generate MCQs from (min 50 chars)
    - `num_questions` — number of MCQs to generate (1-30, default 5)
    - `difficulty` — easy | medium | hard | mixed (default: mixed)

    **Returns:** List of MCQ objects with question, options, answer, explanation.
    """
    if len(request.text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Text is too short. Please provide at least 50 characters."
        )

    try:
        pipeline = get_pipeline()
        start_time = time.time()

        mcqs = pipeline.run(
            text=request.text,
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            export_format=None,   # No file export for API — return JSON
            verbose=False,
        )

        elapsed = round(time.time() - start_time, 2)

        if not mcqs:
            raise HTTPException(
                status_code=500,
                detail="No MCQs were generated. Check your Gemini API quota."
            )

        return GenerationResult(
            success=True,
            total_generated=len(mcqs),
            time_taken_seconds=elapsed,
            difficulty=request.difficulty,
            mcqs=[MCQResponse(**mcq) for mcq in mcqs],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/generate/pdf",
    response_model=GenerationResult,
    summary="Generate MCQs from PDF",
    tags=["Generation"],
    responses={
        200: {"description": "MCQs generated successfully"},
        400: {"description": "Invalid file type"},
        500: {"description": "Generation failed"},
    },
)
async def generate_from_pdf(
    file: UploadFile = File(..., description="PDF file to generate MCQs from"),
    num_questions: int = Query(default=5,  ge=1, le=30, description="Number of MCQs to generate"),
    difficulty:    str = Query(default="mixed", description="easy | medium | hard | mixed"),
):
    """
    Generate MCQs from an uploaded PDF file.

    **Parameters:**
    - `file` — PDF file upload (multipart/form-data)
    - `num_questions` — number of MCQs to generate (1-30, default 5)
    - `difficulty` — easy | medium | hard | mixed (default: mixed)

    **Returns:** List of MCQ objects with question, options, answer, explanation.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.filename}'. Only PDF files are accepted."
        )

    # Validate difficulty
    valid_difficulties = ["easy", "medium", "hard", "mixed"]
    if difficulty not in valid_difficulties:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid difficulty '{difficulty}'. Choose from: {valid_difficulties}"
        )

    # Save uploaded PDF to a temp file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
            prefix="mcq_upload_"
        ) as tmp:
            content = await file.read()

            if len(content) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")

            if len(content) > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(
                    status_code=400,
                    detail="File too large. Maximum size is 10MB."
                )

            tmp.write(content)
            tmp_path = tmp.name

        pipeline = get_pipeline()
        start_time = time.time()

        mcqs = pipeline.run_from_pdf(
            pdf_path=tmp_path,
            num_questions=num_questions,
            difficulty=difficulty,
            export_format=None,   # No file export for API — return JSON
            verbose=False,
        )

        elapsed = round(time.time() - start_time, 2)

        if not mcqs:
            raise HTTPException(
                status_code=500,
                detail="No MCQs were generated. The PDF may have no extractable text, or check your Gemini API quota."
            )

        return GenerationResult(
            success=True,
            total_generated=len(mcqs),
            time_taken_seconds=elapsed,
            difficulty=difficulty,
            source_filename=file.filename,
            mcqs=[MCQResponse(**mcq) for mcq in mcqs],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)