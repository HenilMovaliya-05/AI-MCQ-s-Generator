"""
quiz_to_moodle_auto.py

Pipeline:
- PDF -> text
- Gemini -> JSON MCQs
- JSON -> GIFT
- POST GIFT to Moodle via local_importmcq_import_gift

Requirements:
- python >= 3.8
- pip install google-generativeai requests PyPDF2
- local_importmcq plugin installed in Moodle and added to an external service
- a token for a Moodle user with 'moodle/question:add' capability
"""

import os
import json
import requests
import google.generativeai as genai
import PyPDF2
from typing import List, Dict

# ===== CONFIG - EDIT THESE =====
GENAI_API_KEY = "AIzaSyD7eFVn8vqFADMQgA9M-pzHl1hpY-z-9jE"
MOODLE_URL = "http://localhost/moodle"   # e.g. "http://localhost/moodle"
MOODLE_TOKEN = "6f06cffeae8f2bd1b2b31ecbdadaacb5"
CATEGORY_ID = 5                          # question bank category id
PDF_PATH = "Logistic Regression.pdf"     # path to your PDF
SAVE_GIFT = True                         # save questions.gift locally
GIFT_FILENAME = "questions.gift"
NUM_QUESTIONS = 10
# ================================

# configure Gemini client
genai.configure(api_key=GENAI_API_KEY)

# --- Helpers: PDF -> text ---
def extract_text_from_pdf(pdf_path: str) -> str:
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    text = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            try:
                p = page.extract_text()
            except Exception:
                p = ""
            if p:
                text.append(p)
    return "\n".join(text).strip()

# --- Helpers: handle model output fences & parse JSON ---
def strip_code_fences(raw: str) -> str:
    raw = raw.strip()
    # remove triple backticks if present
    if raw.startswith("```") and "```" in raw[3:]:
        parts = raw.split("```")
        # prefer the middle content
        if len(parts) >= 2:
            inner = parts[1]
            # remove leading "json" if present
            if inner.lower().startswith("json"):
                inner = inner[len("json"):].lstrip()
            return inner.strip()
    # single-line fenced `[...]`
    if raw.startswith("`") and raw.endswith("`"):
        return raw[1:-1].strip()
    return raw

def robust_json_load(raw: str):
    raw = raw.strip()
    raw = strip_code_fences(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # try some common fixes
        cleaned = raw.replace("“", '"').replace("”", '"').replace("’", "'").replace("\r\n", "\n")
        # if single quotes are used heavily, attempt naive swap (risky but often works for AI output)
        if cleaned.count("'") > cleaned.count('"'):
            cleaned2 = cleaned.replace("'", '"')
        else:
            cleaned2 = cleaned
        try:
            return json.loads(cleaned2)
        except Exception:
            # final attempt: extract JSON array substring
            start = cleaned2.find('[')
            end = cleaned2.rfind(']')
            if start != -1 and end != -1 and end > start:
                snippet = cleaned2[start:end+1]
                try:
                    return json.loads(snippet)
                except Exception:
                    pass
            # give up
            raise

# --- MCQ generation using Gemini ---
def generate_mcqs(text: str, num_questions: int = 5) -> List[Dict]:
    # keep chunk small to be safe; you may implement chunking later
    text_snippet = text[:4000]
    prompt = f"""
You are an AI quiz generator.
Read the study material below and generate exactly {num_questions} multiple-choice questions.

IMPORTANT: Output only valid JSON, nothing else (no explanation, no markdown, no code fences).

Schema:
[
  {{
    "question": "string",
    "options": ["A","B","C","D"],
    "answer_index": 0
  }}
]

Study material:
{text_snippet}
"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    raw = response.text or ""
    mcqs = robust_json_load(raw)
    # basic validation
    if not isinstance(mcqs, list) or not all(isinstance(q, dict) for q in mcqs):
        raise ValueError("MCQs returned in unexpected format.")
    return mcqs

# --- convert MCQs to GIFT ---
def mcqs_to_gift_text(mcqs: List[Dict]) -> str:
    parts = []
    for i, mcq in enumerate(mcqs, start=1):
        qtext = str(mcq.get("question", "")).replace("\n", " ").strip()
        parts.append(f"::Q{i}:: {qtext} {{")
        options = mcq.get("options", [])
        answer_index = int(mcq.get("answer_index", 0)) if mcq.get("answer_index") is not None else 0
        for j, opt in enumerate(options):
            opt_clean = str(opt).replace("\n", " ").strip()
            if j == answer_index:
                parts.append(f"    ={opt_clean}")
            else:
                parts.append(f"    ~{opt_clean}")
        parts.append("}\n")
    return "\n".join(parts)

# --- save GIFT file locally ---
def save_gift_file(text: str, filename: str = GIFT_FILENAME) -> str:
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    abs_path = os.path.abspath(filename)
    print(f"✅ GIFT saved to {abs_path}")
    return abs_path

# --- call Moodle webservice plugin local_importmcq_import_gift ---
def import_gift_to_moodle(gift_text: str, categoryid: int = CATEGORY_ID) -> Dict:
    endpoint = f"{MOODLE_URL.rstrip('/')}/webservice/rest/server.php"
    params = {
        "wstoken": MOODLE_TOKEN,
        "wsfunction": "local_importmcq_import_gift",
        "moodlewsrestformat": "json",
    }
    data = {
        "gifttext": gift_text,
        "categoryid": categoryid
    }
    print("Sending GIFT text to Moodle import service...")
    resp = requests.post(endpoint, params=params, data=data, timeout=120)
    # HTTP basic check
    if resp.status_code != 200:
        raise RuntimeError(f"Moodle returned HTTP {resp.status_code}: {resp.text[:1000]}")
    # parse JSON
    try:
        return resp.json()
    except ValueError:
        # show raw response for debugging
        print("Moodle did not return JSON. Raw response (first 2000 chars):")
        print(resp.text[:5000])
        raise

# --- pipeline runner ---
def run_pipeline(pdf_path: str = PDF_PATH, num_questions: int = NUM_QUESTIONS):
    print("Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("No text extracted. Aborting.")
        return

    print("Generating MCQs from text....")
    mcqs = generate_mcqs(text, num_questions=num_questions)
    print(f"Generated {len(mcqs)} MCQs.")

    gift_text = mcqs_to_gift_text(mcqs)

    if SAVE_GIFT:
        save_gift_file(gift_text, GIFT_FILENAME)

    try:
        result = import_gift_to_moodle(gift_text, categoryid=CATEGORY_ID)
        print("Moodle import result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print("Failed to import into Moodle !! :", str(e))

# --- main ---
if __name__ == "__main__":
    # placeholders = []
    # if GENAI_API_KEY.startswith("AIzaSyD7eFV") or not GENAI_API_KEY.strip():
    #     placeholders.append("n8vqFADMQgA9M-pzHl1hpY-z-9jE")
    # if MOODLE_TOKEN.startswith("6f06cffeae8f2bd1") or not MOODLE_TOKEN.strip():
    #     placeholders.append("b2b31ecbdadaacb5")
    # if placeholders:
    #     print("Please set the following configuration placeholders in the script:", ", ".join(placeholders))
    # else:
        run_pipeline(PDF_PATH, NUM_QUESTIONS)
