"""
run.py
------
Entry point to start the FastAPI server.

Usage:
    python run.py                   (development)
    uvicorn run:app --host 0.0.0.0  (production)
"""

import uvicorn
from api.app import app

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="localhost",
        port=8000,
        reload=True,       # Auto-reload on code changes (dev mode)
        log_level="info",
    )
    