"""
Streamlit/streamlit_app.py
--------------------------
Streamlit frontend for the AI MCQ Generator.
Calls the FastAPI backend to generate MCQs.

Run locally:
    streamlit run Streamlit/streamlit_app.py

Make sure FastAPI server is running at http://localhost:8000
OR update API_URL to your deployed Render URL.
"""

import streamlit as st
import requests
import json
import time
import io
from datetime import datetime

# Config 
API_URL = "http://localhost:8000"

# Page Setup 
st.set_page_config(
    page_title="AI MCQ Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS 
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e1e50;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
        font-size: 1rem;
    }
    .mcq-card {
        background: #f8f8fc;
        border-left: 4px solid #1e1e50;
        color: #333;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.2rem;
    }
    .correct-option {
        background: #d4edda;
        border-radius: 6px;
        padding: 0.4rem 0.8rem;
        color: #155724;
        font-weight: 600;
    }
    .wrong-option {
        padding: 0.4rem 0.8rem;
        color: #333;
    }
    .explanation-box {
        background: #e8f0fe;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        color: #1a3c6e;
        font-size: 0.9rem;
        margin-top: 0.8rem;
    }
    .download-section {
        background: #f0f4ff;
        border: 1px solid #c5d0f5;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ================================================================== 
# Helper Functions                                                    

def check_api_health() -> bool:
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def generate_from_text(text: str, num_questions: int, difficulty: str) -> dict:
    response = requests.post(
        f"{API_URL}/generate/text",
        json={"text": text, "num_questions": num_questions, "difficulty": difficulty},
        timeout=120,
    )
    return response.json(), response.status_code


def generate_from_pdf(pdf_file, num_questions: int, difficulty: str) -> dict:
    response = requests.post(
        f"{API_URL}/generate/pdf",
        files={"file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")},
        params={"num_questions": num_questions, "difficulty": difficulty},
        timeout=120,
    )
    return response.json(), response.status_code


def difficulty_badge(difficulty: str) -> str:
    color_map = {"easy": "#28a745", "medium": "#fd7e14", "hard": "#dc3545"}
    color = color_map.get(difficulty.lower(), "#6c757d")
    return f'<span style="background:{color};color:white;padding:2px 10px;border-radius:12px;font-size:0.8rem;font-weight:600;">{difficulty.upper()}</span>'


def topic_badge(topic: str) -> str:
    return f'<span style="background:#e8f0fe;color:#1a3c6e;padding:2px 10px;border-radius:12px;font-size:0.8rem;">{topic.title()}</span>'


def render_mcq(mcq: dict, index: int):
    diff_html  = difficulty_badge(mcq.get("difficulty", "medium"))
    topic_html = topic_badge(mcq.get("topic", "general"))

    st.markdown(f"""
    <div class="mcq-card">
        <div style="margin-bottom:0.6rem;">
            <strong>Q{index}.</strong>&nbsp;&nbsp;{diff_html}&nbsp;{topic_html}
        </div>
        <div style="font-size:1.05rem;font-weight:600;margin-bottom:0.8rem;color:#1e1e50;">
            {mcq.get("question", "")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    options = mcq.get("options", {})
    correct = mcq.get("correct_answer", "")

    for key, value in options.items():
        if key == correct:
            st.markdown(
                f'<div class="correct-option">✓ &nbsp;<strong>{key}.</strong> {value}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="wrong-option">&nbsp;&nbsp;&nbsp;<strong>{key}.</strong> {value}</div>',
                unsafe_allow_html=True
            )

    st.markdown(
        f'<div class="explanation-box">💡 <strong>Explanation:</strong> {mcq.get("explanation", "")}</div>',
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)


# ==================================================================
# Download Helpers                                                     

def prepare_json_download(mcqs: list) -> bytes:
    """Prepare MCQs as JSON bytes for download."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "total_questions": len(mcqs),
        "mcqs": mcqs,
    }
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


def prepare_pdf_download(mcqs: list) -> bytes:
    """
    Generate a professional PDF from MCQs using fpdf2.
    Returns PDF as bytes for Streamlit download button.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        st.error("fpdf2 not installed. Run: pip install fpdf2")
        return None

    # Unicode replacement map 
    UNICODE_MAP = {
        "\u2014": "-", "\u2013": "-", "\u2012": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u00a0": " ", "\u200b": "", "\u200c": "",
        "\u200d": "", "\ufeff": "", "\u2022": "-", "\u2192": "->",
        "\u00b0": "deg", "\u00ae": "(R)", "\u2122": "TM",
        "\u00d7": "x", "\u00f7": "/", "\u2212": "-", "\u00b1": "+/-",
    }

    def safe(text: str) -> str:
        if not text:
            return ""
        for uc, rep in UNICODE_MAP.items():
            text = text.replace(uc, rep)
        return text.encode("latin-1", errors="ignore").decode("latin-1")

    DIFF_COLORS = {
        "easy":   (34,  139, 34),
        "medium": (255, 140,  0),
        "hard":   (180,   0,  0),
    }

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Header bar
    pdf.set_fill_color(30, 30, 80)
    pdf.rect(0, 0, 210, 38, style="F")
    pdf.set_y(8)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "MCQ Question Set", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 200, 220)
    pdf.cell(0, 7,
             safe(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}   |   Total: {len(mcqs)} questions"),
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(18)

    # Legend
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, "Difficulty:  Easy   Medium   Hard", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    for i, mcq in enumerate(mcqs, 1):
        difficulty  = mcq.get("difficulty", "medium").lower()
        topic       = mcq.get("topic", "general").title()
        question    = safe(mcq.get("question", ""))
        options     = mcq.get("options", {})
        answer      = mcq.get("correct_answer", "")
        explanation = safe(mcq.get("explanation", ""))
        diff_color  = DIFF_COLORS.get(difficulty, (80, 80, 80))

        # Question card
        card_y = pdf.get_y()
        pdf.set_fill_color(248, 248, 252)
        pdf.rect(18, card_y, 174, 8, style="F")
        pdf.set_fill_color(*diff_color)
        pdf.rect(18, card_y, 4, 8, style="F")

        pdf.set_xy(24, card_y)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(30, 30, 80)
        pdf.cell(12, 8, f"Q{i}.", new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 100, 140)
        pdf.cell(0, 8, safe(f"[{topic}]  [{difficulty.upper()}]"),
                 new_x="LMARGIN", new_y="NEXT")

        pdf.set_x(24)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(166, 6, question)
        pdf.ln(3)

        for key, value in options.items():
            is_correct = (key == answer)
            safe_value = safe(str(value))
            pdf.set_x(26)
            if is_correct:
                opt_y = pdf.get_y()
                pdf.set_fill_color(220, 245, 220)
                pdf.rect(26, opt_y, 162, 7, style="F")
                pdf.set_xy(26, opt_y)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(0, 110, 0)
                pdf.cell(8, 7, f"{key}.", new_x="RIGHT", new_y="TOP")
                pdf.multi_cell(154, 7, f"{safe_value}  [CORRECT]")
            else:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(8, 6, f"{key}.", new_x="RIGHT", new_y="TOP")
                pdf.set_x(34)
                pdf.multi_cell(154, 6, safe_value)

        pdf.ln(2)
        exp_y = pdf.get_y()
        pdf.set_fill_color(240, 245, 255)
        pdf.rect(26, exp_y, 162, 6, style="F")
        pdf.set_xy(26, exp_y)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(60, 60, 120)
        pdf.multi_cell(162, 5, f"Explanation: {explanation}")
        pdf.ln(6)

        if i < len(mcqs):
            pdf.set_draw_color(200, 200, 220)
            pdf.set_line_width(0.3)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(6)

    # Footer
    pdf.set_y(-18)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(160, 160, 160)
    pdf.cell(0, 6,
             safe(f"Generated by AI MCQ Generator  |  {datetime.now().strftime('%Y-%m-%d')}"),
             align="C")

    # Return as bytes
    return bytes(pdf.output())


def render_download_section(mcqs: list, source: str):
    """
    Renders the download section with a format dropdown
    and a single dynamic download button.
    """
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown("#### ⬇️ Download Generated MCQs")

    col_select, col_btn = st.columns([1, 1])

    with col_select:
        download_format = st.selectbox(
            "Choose format",
            options=["PDF — Formatted document (.pdf)", "JSON — Structured data (.json)"],
            index=0,
            label_visibility="collapsed",
            key="download_format_select",
        )

    # Generate filename from source
    base_name = source.replace(".pdf", "").replace(" ", "_").replace("input", "mcqs")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    is_pdf = download_format.startswith("PDF")

    with col_btn:
        if is_pdf:
            pdf_bytes = prepare_pdf_download(mcqs)
            if pdf_bytes:
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_bytes,
                    file_name=f"{base_name}_{timestamp}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
        else:
            json_bytes = prepare_json_download(mcqs)
            st.download_button(
                label="⬇️ Download JSON",
                data=json_bytes,
                file_name=f"{base_name}_{timestamp}.json",
                mime="application/json",
                use_container_width=True,
                type="primary",
            )

    st.markdown('</div>', unsafe_allow_html=True)


# ================================================================== 
# Main App Layout                                                       

# Header
st.markdown('<div class="main-title">🎓 AI MCQ Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Generate Multiple Choice Questions from PDF or Text using Hybrid NLP + Google Gemini</div>',
    unsafe_allow_html=True
)

# API Health Check
api_online = check_api_health()
if api_online:
    st.success("✅ API is online and ready")
else:
    st.error(
        f"❌ Cannot connect to API at `{API_URL}`. "
        "Make sure the FastAPI server is running (`python run.py`) "
        "or update the API_URL in this file to your deployed URL."
    )

st.divider()

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=80)
    st.markdown("## ⚙️ Settings")

    num_questions = st.slider(
        "Number of Questions",
        min_value=1, max_value=20, value=5, step=1,
        help="How many MCQs to generate"
    )

    difficulty = st.selectbox(
        "Difficulty Level",
        options=["mixed", "easy", "medium", "hard"],
        index=0,
        help="mixed = auto-detect per paragraph"
    )

    st.divider()
    st.markdown("### 📊 Difficulty Guide")
    st.markdown("🟢 **Easy** — definitions, basic recall")
    st.markdown("🟡 **Medium** — understanding, relationships")
    st.markdown("🔴 **Hard** — analysis, critical thinking")
    st.markdown("🔀 **Mixed** — auto-detect from content")

    st.divider()
    st.markdown("### 🔗 Links")
    st.markdown("[📖 API Docs](http://localhost:8000/docs)")
    st.markdown("[💻 GitHub](https://github.com/YourUsername/AI-MCQs-Generator)")

# Input Tabs
tab1, tab2 = st.tabs(["📄 Upload PDF", "✏️ Paste Text"])

# Tab 1: PDF Upload
with tab1:
    st.markdown("### Upload your PDF file")
    st.caption("Supports lecture notes, textbooks, research papers (max 10MB). Diagram-only pages are automatically skipped.")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload a PDF with selectable text"
    )

    if uploaded_file:
        file_size_kb = len(uploaded_file.getvalue()) / 1024
        st.info(f"📎 **{uploaded_file.name}** — {file_size_kb:.1f} KB uploaded")

        if st.button("🚀 Generate MCQs from PDF", type="primary", use_container_width=True):
            if not api_online:
                st.error("API is offline. Please start the FastAPI server first.")
            else:
                with st.spinner(f"Generating {num_questions} MCQs... This may take 20-60 seconds."):
                    try:
                        start = time.time()
                        result, status_code = generate_from_pdf(uploaded_file, num_questions, difficulty)
                        elapsed = round(time.time() - start, 2)

                        if status_code == 200 and result.get("success"):
                            st.session_state["mcqs"]    = result["mcqs"]
                            st.session_state["source"]  = uploaded_file.name
                            st.session_state["elapsed"] = elapsed
                            st.session_state["total"]   = result["total_generated"]
                            st.success(f"✅ Generated {result['total_generated']} MCQs in {elapsed}s!")
                            st.rerun()
                        else:
                            st.error(f"❌ Generation failed: {result.get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"❌ Request failed: {str(e)}")

# Tab 2: Text Input
with tab2:
    st.markdown("### Paste your text")
    st.caption("Paste any study material, notes, or paragraph (minimum 50 characters)")

    user_text = st.text_area(
        "Input Text",
        height=250,
        placeholder="Paste your study material here...\n\nExample: Photosynthesis is the process by which plants use sunlight...",
        label_visibility="collapsed",
    )

    char_count = len(user_text.strip())
    if char_count > 0:
        color = "green" if char_count >= 50 else "red"
        st.markdown(f"<small style='color:{color}'>{char_count} characters</small>", unsafe_allow_html=True)

    if st.button("🚀 Generate MCQs from Text", type="primary", use_container_width=True):
        if not api_online:
            st.error("API is offline. Please start the FastAPI server first.")
        elif char_count < 50:
            st.warning("⚠️ Text is too short. Please enter at least 50 characters.")
        else:
            with st.spinner(f"Generating {num_questions} MCQs... This may take 20-60 seconds."):
                try:
                    start = time.time()
                    result, status_code = generate_from_text(user_text, num_questions, difficulty)
                    elapsed = round(time.time() - start, 2)

                    if status_code == 200 and result.get("success"):
                        st.session_state["mcqs"]    = result["mcqs"]
                        st.session_state["source"]  = "text_input"
                        st.session_state["elapsed"] = elapsed
                        st.session_state["total"]   = result["total_generated"]
                        st.success(f"✅ Generated {result['total_generated']} MCQs in {elapsed}s!")
                        st.rerun()
                    else:
                        st.error(f"❌ Generation failed: {result.get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Request failed: {str(e)}")

# Results Section
if "mcqs" in st.session_state and st.session_state["mcqs"]:
    mcqs    = st.session_state["mcqs"]
    source  = st.session_state.get("source", "mcqs")
    elapsed = st.session_state.get("elapsed", 0)
    total   = st.session_state.get("total", len(mcqs))

    st.divider()
    st.markdown("## 📋 Generated MCQs")

    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Questions", total)
    with col2:
        st.metric("Time Taken", f"{elapsed}s")
    with col3:
        diff_counts = {}
        for m in mcqs:
            d = m.get("difficulty", "medium")
            diff_counts[d] = diff_counts.get(d, 0) + 1
        most_common = max(diff_counts, key=diff_counts.get) if diff_counts else "-"
        st.metric("Most Common Difficulty", most_common.title())
    with col4:
        topics = list(set(m.get("topic", "general") for m in mcqs))
        st.metric("Topics Detected", len(topics))

    st.caption(f"Source: {source}")
    st.divider()

    # Download Section with format dropdown 
    render_download_section(mcqs, source)

    # Render MCQs 
    for i, mcq in enumerate(mcqs, 1):
        render_mcq(mcq, i)

    # Clear button
    if st.button("🗑️ Clear Results", use_container_width=False):
        del st.session_state["mcqs"]
        st.rerun()