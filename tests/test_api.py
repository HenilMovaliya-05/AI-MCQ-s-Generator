"""
tests/test_api.py
-----------------
Tests for FastAPI endpoints.
Uses TestClient — no real server needed, no Gemini API calls.

Run with:
    pytest tests/test_api.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

# Sample MCQ for mocking
MOCK_MCQ = {
    "question": "What is photosynthesis?",
    "options": {
        "A": "A process in animals",
        "B": "A process in plants using sunlight",
        "C": "A type of respiration",
        "D": "A chemical reaction in rocks",
    },
    "correct_answer": "B",
    "explanation": "Photosynthesis is the process by which plants convert sunlight into energy.",
    "difficulty": "easy",
    "topic": "science",
}


# ================================================================== 
# General Endpoint Tests                                               

class TestGeneralEndpoints:

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_name(self):
        response = client.get("/")
        data = response.json()
        assert "name" in data
        assert "AI MCQ Generator" in data["name"]

    def test_root_has_endpoints(self):
        response = client.get("/")
        data = response.json()
        assert "endpoints" in data
        assert "generate_text" in data["endpoints"]
        assert "generate_pdf" in data["endpoints"]

    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_status(self):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]

    def test_health_has_model(self):
        response = client.get("/health")
        data = response.json()
        assert "model" in data
        assert "api_key_configured" in data

    def test_docs_accessible(self):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_accessible(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/generate/text" in schema["paths"]
        assert "/generate/pdf" in schema["paths"]


# ==================================================================
# Text Generation Endpoint Tests                                        

class TestTextGeneration:

    def test_short_text_returns_400(self):
        response = client.post("/generate/text", json={
            "text": "Too short",
            "num_questions": 3,
        })
        assert response.status_code == 400

    def test_invalid_difficulty_returns_422(self):
        response = client.post("/generate/text", json={
            "text": "A" * 100,
            "num_questions": 3,
            "difficulty": "super_hard",
        })
        assert response.status_code == 422

    def test_num_questions_above_limit_returns_422(self):
        response = client.post("/generate/text", json={
            "text": "A" * 100,
            "num_questions": 999,
        })
        assert response.status_code == 422

    def test_num_questions_zero_returns_422(self):
        response = client.post("/generate/text", json={
            "text": "A" * 100,
            "num_questions": 0,
        })
        assert response.status_code == 422

    @patch("api.app.get_pipeline")
    def test_valid_text_returns_200(self, mock_get_pipeline):
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = [MOCK_MCQ]
        mock_get_pipeline.return_value = mock_pipeline

        response = client.post("/generate/text", json={
            "text": "Photosynthesis is the process by which plants use sunlight to produce energy.",
            "num_questions": 1,
            "difficulty": "easy",
        })
        assert response.status_code == 200

    @patch("api.app.get_pipeline")
    def test_response_has_mcqs(self, mock_get_pipeline):
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = [MOCK_MCQ]
        mock_get_pipeline.return_value = mock_pipeline

        response = client.post("/generate/text", json={
            "text": "Photosynthesis is the process by which plants convert sunlight into food.",
            "num_questions": 1,
            "difficulty": "easy",
        })
        data = response.json()
        assert "mcqs" in data
        assert len(data["mcqs"]) == 1
        assert data["total_generated"] == 1

    @patch("api.app.get_pipeline")
    def test_mcq_has_required_fields(self, mock_get_pipeline):
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = [MOCK_MCQ]
        mock_get_pipeline.return_value = mock_pipeline

        response = client.post("/generate/text", json={
            "text": "Photosynthesis is the process by which plants convert sunlight into food.",
            "num_questions": 1,
        })
        mcq = response.json()["mcqs"][0]
        assert "question" in mcq
        assert "options" in mcq
        assert "correct_answer" in mcq
        assert "explanation" in mcq
        assert "difficulty" in mcq
        assert "topic" in mcq

    @patch("api.app.get_pipeline")
    def test_response_has_time_taken(self, mock_get_pipeline):
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = [MOCK_MCQ]
        mock_get_pipeline.return_value = mock_pipeline

        response = client.post("/generate/text", json={
            "text": "Photosynthesis is the process by which plants convert sunlight into food.",
            "num_questions": 1,
        })
        data = response.json()
        assert "time_taken_seconds" in data
        assert isinstance(data["time_taken_seconds"], float)


# ================================================================== 
# PDF Generation Endpoint Tests                                        

class TestPDFGeneration:

    def test_non_pdf_file_returns_400(self):
        response = client.post(
            "/generate/pdf",
            files={"file": ("notes.txt", b"some text content", "text/plain")},
        )
        assert response.status_code == 400

    def test_empty_file_returns_400(self):
        response = client.post(
            "/generate/pdf",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert response.status_code == 400

    def test_invalid_difficulty_returns_400(self):
        response = client.post(
            "/generate/pdf",
            files={"file": ("test.pdf", b"%PDF-1.4 fake content", "application/pdf")},
            params={"difficulty": "invalid_level"},
        )
        assert response.status_code == 400

    def test_valid_difficulty_values_accepted(self):
        """Test that all valid difficulty values pass validation."""
        for diff in ["easy", "medium", "hard", "mixed"]:
            # This will fail at pipeline stage but NOT at validation stage
            response = client.post(
                "/generate/pdf",
                files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
                params={"difficulty": diff},
            )
            # Should not be 400 (validation error)
            assert response.status_code != 400, f"Difficulty '{diff}' was rejected"


# Run

if __name__ == "__main__":
    test_classes = [
        TestGeneralEndpoints,
        TestTextGeneration,
        TestPDFGeneration,
    ]
    passed = 0
    failed = 0

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method in methods:
            try:
                getattr(instance, method)()
                print(f"  ✓ {cls.__name__}.{method}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {cls.__name__}.{method}: {e}")
                failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")