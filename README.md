# 🎓 AI MCQ Generator — Hybrid NLP + GenAI Pipeline

A smart Multiple Choice Question generator that uses **NLP for intelligent preprocessing** and **Google Gemini for high-quality question generation**. This hybrid approach produces better MCQs than either approach alone.

---

## 🌐 Live Demo

| Service | URL |
|---------|-----|
| 🔗 REST API | `https://ai-mcq-generator-api.onrender.com` |
| 📖 API Docs (Swagger) | `https://ai-mcq-generator-api.onrender.com/docs` |
| 💻 GitHub | `https://github.com/HenilMovaliya-05/AI-MCQs-Generator` |

---

## 🏗️ Project Architecture

```
MCQ_Generator/
│
├── main.py                    # CLI entry point (interactive mode)
├── pipeline.py                # Master orchestrator (ties all modules)
├── run.py                     # FastAPI server entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Environment config template
├── .gitignore                 # Git ignore rules
├── render.yaml                # Render.com deployment config
├── Procfile                   # Process file for deployment
├── sample_input.txt           # Sample text to test with
│
├── api/                       # FastAPI REST API Layer
│   ├── __init__.py
│   ├── app.py                 # API routes and endpoints
│   └── models.py              # Pydantic request/response models
│
├── Streamlit/                 # Streamlit Web UI
│   └── streamlit_app.py       # Interactive web interface
│
├── nlp/                       # NLP Preprocessing Layer
│   ├── __init__.py
│   ├── chunker.py             # Splits text into meaningful segments
│   ├── keyword_extractor.py   # TF-IDF keyword + named entity extraction
│   └── topic_detector.py      # Topic classification + difficulty scoring
│
├── genai/                     # GenAI API Layer
│   ├── __init__.py
│   ├── prompt_builder.py      # Builds structured prompts from NLP data
│   └── gemini_client.py       # Google Gemini API wrapper + retry logic
│
├── utils/                     # Post-processing & Export
│   ├── __init__.py
│   ├── pdf_reader.py          # PDF text extraction (pdfplumber + pypdf)
│   ├── postprocessor.py       # Dedup, cleaning, validation, filtering
│   └── exporter.py            # Save to JSON / TXT / PDF
│
├── output/                    # Generated MCQ files saved here (auto-created)
│
└── tests/                     # Unit tests
    ├── test_nlp.py            # Tests for chunker, keyword, topic modules
    ├── test_pipeline.py       # Tests for postprocessor and prompt builder
    ├── test_pdf_reader.py     # Tests for PDF extraction and cleaning
    └── test_api.py            # Tests for FastAPI endpoints
```

---

## ⚙️ How the Pipeline Works

```
Input (.pdf / .txt / text string)
   ↓
[PDF Reader]  pdfplumber (primary) + pypdf (fallback)
              Auto-skips diagram/image-only pages
   ↓
[NLP] Text Chunking       →  Split into paragraphs / sentence windows
[NLP] Keyword Extraction  →  TF-IDF scoring + Named Entity Recognition
[NLP] Topic Detection     →  Domain classification + difficulty scoring
   ↓
[BRIDGE] Prompt Builder   →  Combine chunk + keywords + topic + difficulty
   ↓
[GenAI] Gemini API        →  Generate questions + distractors + explanations
   ↓
[NLP] Post-Processing     →  Deduplication + cleaning + answer validation
   ↓
Final MCQ Set → JSON / TXT / PDF  (user chooses at runtime)
```

---

## 🚀 Setup

### 1. Create and activate Virtual Environment (recommended)

```bash
cd MCQ_Generator

# Create virtual environment
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — Mac/Linux
source venv/bin/activate
```

You will see `(venv)` in your terminal when it is active.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get a Gemini API Key

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Create a free API key
3. Copy it

### 4. Configure your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in your key:

```
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
MCQ_PER_CHUNK=3
OUTPUT_FORMAT=pdf
DEFAULT_DIFFICULTY=mixed
MAX_TOKENS=2048
```

### 5. Deactivate when done working

```bash
deactivate
```

---

## 📥 Supported Input Formats

| Format | How to Use |
|--------|-----------|
| `.pdf` | `python main.py --file notes.pdf` |
| `.txt` | `python main.py --file notes.txt` |
| Direct text | `python main.py --text "Your text here..."` |

> **Note:** Scanned/image PDFs are not supported — the PDF must have selectable text.
> Diagram-only pages (lecture slides with only images) are automatically detected and skipped.
> For `.pdf` input, place your file inside the `MCQ_Generator/` folder or provide the full path.

---

## 📤 Output Formats

Generated MCQs can be saved in three formats — chosen interactively at runtime or via `--format` flag:

| Format | Description | Saved To |
|--------|-------------|----------|
| `pdf` | Professional formatted document with colored difficulty tags, highlighted correct answers, and explanation boxes | `output/yourfile_mcqs.pdf` |
| `json` | Structured machine-readable data | `output/yourfile_mcqs.json` |
| `txt` | Plain human-readable text | `output/yourfile_mcqs.txt` |

Output files are saved automatically in the `output/` folder. The filename is auto-generated from your input filename (e.g. `notes.pdf` → `output/notes_mcqs.pdf`).

---

## 💻 Usage — CLI (Command Line)

### Interactive Mode (recommended)

Just provide the input file — the program will ask you everything else:

```bash
python main.py --file notes.pdf
```

You will be prompted to choose:
1. Number of questions (e.g. 10)
2. Difficulty level (Easy / Medium / Hard / Mixed)
3. Output format (JSON / TXT / PDF)
4. Confirm before generating

### Command Line Mode (skip prompts)

```bash
# Basic command
python main.py --file "your\file\path"

# Full command — no prompts shown
python main.py --file notes.pdf --num 10 --difficulty hard --format pdf

# PDF input, medium difficulty, JSON output
python main.py --file lecture.pdf --num 5 --difficulty medium --format json

# TXT input, mixed difficulty, TXT output
python main.py --file notes.txt --num 8 --difficulty mixed --format txt

# Direct text input
python main.py --text "Photosynthesis is the process..." --num 3 --format pdf

# Custom output filename
python main.py --file biology.pdf --num 10 --format pdf --output biology_quiz

# Print MCQs to terminal as well
python main.py --file notes.pdf --num 5 --format pdf --print

# Non-interactive mode — uses .env defaults for everything missing
python main.py --file notes.pdf --no-interactive
```

## 🔌 Usage — FastAPI (REST API)

### Start the API server locally

```bash
python run.py
```

Server starts at: `http://localhost:8000`

Open Swagger UI at: `http://localhost:8000/docs`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info and available endpoints |
| GET | `/health` | Health check + API key status |
| POST | `/generate/text` | Generate MCQs from plain text |
| POST | `/generate/pdf` | Generate MCQs from uploaded PDF file |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/redoc` | ReDoc API documentation |


### Sample API Response

```json
{
  "success": true,
  "total_generated": 3,
  "time_taken_seconds": 4.21,
  "difficulty": "medium",
  "source_filename": "notes.pdf",
  "mcqs": [
    {
      "question": "What is the primary function of chlorophyll in photosynthesis?",
      "options": {
        "A": "To absorb water from the soil",
        "B": "To capture light energy from the sun",
        "C": "To produce carbon dioxide",
        "D": "To store glucose in the roots"
      },
      "correct_answer": "B",
      "explanation": "Chlorophyll captures sunlight energy which drives the photosynthesis process.",
      "difficulty": "medium",
      "topic": "science"
    }
  ]
}
```

---

## 🖥️ Usage — Streamlit Web UI

The Streamlit UI provides an interactive web interface that calls the FastAPI backend.

### Run Streamlit locally

Open **two terminals** — both with venv activated:

**Terminal 1 — Start FastAPI backend:**
```bash
python run.py
```

**Terminal 2 — Start Streamlit frontend:**
```bash
streamlit run Streamlit/streamlit_app.py
```

Browser opens automatically at `http://localhost:8501`

### Streamlit Features

- **Upload PDF tab** — drag and drop any PDF file to generate MCQs
- **Paste Text tab** — paste raw text directly for quick generation
- **Sidebar settings** — choose number of questions (1-20) and difficulty level
- **Download dropdown** — choose between PDF or JSON format to download results
- **Live stats** — shows total questions, time taken, difficulty breakdown, topics detected
- **API health indicator** — shows green/red banner if backend is online or offline


## 🔧 Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(required)* | Your Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Model to use — see table below |
| `MCQ_PER_CHUNK` | `3` | MCQs to generate per text chunk |
| `OUTPUT_FORMAT` | `pdf` | Default output format if not chosen interactively |
| `DEFAULT_DIFFICULTY` | `mixed` | Default difficulty if not chosen interactively |
| `MAX_TOKENS` | `2048` | Max tokens for Gemini response |

### Recommended Gemini Models

| Model | Speed | Quality | Free Quota/Day | Best For |
|-------|-------|---------|----------------|----------|
| `gemini-2.5-flash-lite` | Fastest | Good | 1500 req | Recommended for this project |
| `gemini-2.0-flash-lite` | Fast | Good | 1500 req | Alternative |
| `gemini-2.0-flash` | Fast | Better | 1500 req | Better quality |
| `gemini-1.5-pro` | Slow | Best | 50 req | High quality, low quota |

> **Important:** The old `gemini-1.5-flash` model is deprecated and no longer works.
> Always use `gemini-2.5-flash-lite` or newer.

---

## 📦 Dependencies

| Package | Purpose | Required |
|---------|---------|----------|
| `google-genai` | New official Gemini API SDK | Yes |
| `pdfplumber` | Primary PDF text extraction | Yes |
| `pypdf` | Fallback PDF text extraction | Yes |
| `scikit-learn` | TF-IDF keyword extraction | Yes |
| `python-dotenv` | `.env` file loading | Yes |
| `fpdf2` | PDF export of MCQs | Yes |
| `fastapi` | REST API framework | Yes |
| `uvicorn` | ASGI server for FastAPI | Yes |
| `python-multipart` | File upload support for FastAPI | Yes |
| `pydantic` | Request/response validation | Yes |
| `streamlit` | Web UI framework | Yes |
| `requests` | HTTP calls from Streamlit to FastAPI | Yes |
| `keybert` | Better keyword extraction | Optional |

> **Note:** Use `google-genai` (new SDK). The old `google-generativeai` package is fully deprecated as of August 2025 and will not work.

---

## 🗂️ Where Files Go

```
MCQ_Generator/
├── notes.pdf              ← Put your INPUT PDF here
├── output/
│   └── notes_mcqs.pdf     ← Generated MCQs saved here automatically
```

You can also use a subfolder:
```bash
python main.py --file input/notes.pdf --format pdf
# Saves to → output/notes_mcqs.pdf
```

Or a full path:
```bash
# Windows
python main.py --file "C:\Users\You\Downloads\notes.pdf"

# Mac/Linux
python main.py --file "/home/you/Downloads/notes.pdf"
```

---

## 🧪 Running Tests

All NLP and utility tests work **without a Gemini API key** (no API calls made):

```bash
# Run NLP tests (chunker, keyword extractor, topic detector)
python tests/test_nlp.py

# Run pipeline and postprocessor tests
python tests/test_pipeline.py

# Run PDF reader tests
python tests/test_pdf_reader.py

# Run API endpoint tests (no real API calls — uses mocks)
pytest tests/test_api.py -v

# Run all tests with pytest
pytest tests/ -v
```

Expected: **53+ tests, 0 failures**

---

## 📋 Sample Output (JSON)

```json
{
  "generated_at": "2024-01-15T10:30:00",
  "total_questions": 5,
  "mcqs": [
    {
      "question": "What process converts liquid water into water vapor in the water cycle?",
      "options": {
        "A": "Condensation",
        "B": "Precipitation",
        "C": "Evaporation",
        "D": "Infiltration"
      },
      "correct_answer": "C",
      "explanation": "Evaporation is the process by which liquid water is converted to water vapor using solar energy.",
      "difficulty": "easy",
      "topic": "science"
    }
  ]
}
```

---

## 🚫 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `404 model not found` | Deprecated model name | Change `GEMINI_MODEL=gemini-2.5-flash-lite` in `.env` |
| `429 quota exceeded` | Daily free limit hit | Wait 24hrs or switch to `gemini-2.5-flash-lite` |
| `FutureWarning: google.generativeai deprecated` | Old SDK installed | Run `pip uninstall google-generativeai -y` then `pip install google-genai` |
| `ModuleNotFoundError` | Wrong directory or venv not active | Run from `MCQ_Generator/` folder with venv activated |
| `Could not extract text from PDF` | Scanned/image PDF | Use a PDF with selectable text |
| `0 MCQs generated` | API quota + all chunks failed | Check API key and quota at [ai.dev/rate-limit](https://ai.dev/rate-limit) |
| `API is offline` in Streamlit | FastAPI not running | Run `python run.py` in a separate terminal first |
| Render deploy fails | Missing env variable | Add `GEMINI_API_KEY` in Render dashboard environment variables |
| First Render request slow | Free tier sleep | Normal — waits 30-60s to wake up, subsequent requests are fast |


## 🤖 Why Hybrid (NLP + GenAI)?

| Component | Handled By | Reason |
|-----------|------------|--------|
| Text chunking | NLP | Full control, no API cost |
| Keyword extraction | NLP | Guides GenAI to focus on key concepts |
| Topic detection | NLP | Enables difficulty-appropriate prompting |
| Difficulty scoring | NLP | Automatic per-chunk analysis |
| PDF reading | NLP (pdfplumber) | Layout-aware, table support, diagram skipping |
| Question writing | GenAI | Complex language task — GenAI excels |
| Distractor generation | GenAI | Hardest NLP problem — GenAI handles it well |
| Deduplication | NLP | Fast, deterministic, no API cost |
| Answer validation | NLP | Rule-based, reliable, instant |

