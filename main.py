"""
main.py
-------
Command-line interface for the MCQ Generator.
Supports interactive prompts for output format, difficulty, and question count.

Usage examples:
  python main.py --file notes.txt           (fully interactive mode)
  python main.py --file notes.pdf --num 5   (semi-interactive)
  python main.py --file notes.txt --num 10 --difficulty hard --format pdf
  python main.py --text "Photosynthesis is..." --num 3 --format json
"""

import argparse
import sys
import os


# ------------------------------------------------------------------ #
# Color helpers for terminal output                                    #
# ------------------------------------------------------------------ #

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    GRAY   = "\033[90m"
    WHITE  = "\033[97m"

def cprint(color: str, text: str):
    print(f"{color}{text}{C.RESET}")

def banner():
    print()
    cprint(C.BOLD + C.BLUE,  "  ╔══════════════════════════════════════════╗")
    cprint(C.BOLD + C.BLUE,  "  ║       AI MCQ Generator  v1.0             ║")
    cprint(C.BOLD + C.BLUE,  "  ║   Hybrid NLP + GenAI Pipeline            ║")
    cprint(C.BOLD + C.BLUE,  "  ╚══════════════════════════════════════════╝")
    print()


# ------------------------------------------------------------------ #
# Interactive choosers                                                 #
# ------------------------------------------------------------------ #

def ask_output_format() -> str:
    """Interactively ask user to choose output format."""
    print()
    cprint(C.BOLD + C.CYAN, "  📄 Choose Output Format:")
    print()
    print("     1.  JSON  — structured data file (.json)")
    print("     2.  TXT   — plain readable text  (.txt)")
    print("     3.  PDF   — formatted document   (.pdf)  ← recommended")
    print()

    format_map = {"1": "json", "2": "txt", "3": "pdf",
                  "json": "json", "txt": "txt", "pdf": "pdf"}

    while True:
        choice = input("  Enter choice (1/2/3) or type format name: ").strip().lower()
        if choice in format_map:
            selected = format_map[choice]
            cprint(C.GREEN, f"  ✔ Output format selected: {selected.upper()}")
            return selected
        cprint(C.RED, "  Invalid choice. Please enter 1, 2, 3, json, txt, or pdf.")


def ask_difficulty() -> str:
    """Interactively ask user to choose difficulty level."""
    print()
    cprint(C.BOLD + C.CYAN, "  🎯 Choose Difficulty Level:")
    print()
    print("     1.  Easy   — definitions and basic recall")
    print("     2.  Medium — understanding and relationships")
    print("     3.  Hard   — analysis and critical thinking")
    print("     4.  Mixed  — auto-detect per paragraph      ← recommended")
    print()

    diff_map = {
        "1": "easy", "2": "medium", "3": "hard", "4": "mixed",
        "easy": "easy", "medium": "medium", "hard": "hard", "mixed": "mixed",
    }

    while True:
        choice = input("  Enter choice (1/2/3/4) or type level name: ").strip().lower()
        if choice in diff_map:
            selected = diff_map[choice]
            cprint(C.GREEN, f"  ✔ Difficulty selected: {selected.upper()}")
            return selected
        cprint(C.RED, "  Invalid choice. Please enter 1, 2, 3, 4, easy, medium, hard, or mixed.")


def ask_num_questions() -> int:
    """Interactively ask user how many MCQs to generate."""
    print()
    cprint(C.BOLD + C.CYAN, "  🔢 How many MCQs to generate?")
    print()
    print("     Recommended: 5–15 for a short text, 15–30 for a long document.")
    print()

    while True:
        choice = input("  Enter number of questions (e.g. 10): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= 100:
            selected = int(choice)
            cprint(C.GREEN, f"  ✔ Will generate: {selected} questions")
            return selected
        cprint(C.RED, "  Please enter a number between 1 and 100.")


def confirm_settings(fmt: str, diff: str, num: int, source: str):
    """Show a summary of settings before running."""
    print()
    cprint(C.BOLD + C.WHITE, "  ─────────────────────────────────────────")
    cprint(C.BOLD + C.WHITE, "  📋 Confirm Settings:")
    print(f"     Input   : {source}")
    print(f"     Questions: {num}")
    print(f"     Difficulty: {diff.upper()}")
    print(f"     Output  : {fmt.upper()}")
    cprint(C.BOLD + C.WHITE, "  ─────────────────────────────────────────")
    print()

    while True:
        confirm = input("  Start generating? (y/n): ").strip().lower()
        if confirm in ("y", "yes"):
            return True
        elif confirm in ("n", "no"):
            cprint(C.YELLOW, "  Cancelled.")
            sys.exit(0)
        cprint(C.RED, "  Please enter y or n.")


# ------------------------------------------------------------------ #
# Argument parser                                                      #
# ------------------------------------------------------------------ #

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI MCQ Generator — Hybrid NLP + GenAI Pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Input source (mutually exclusive)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--text", "-t",
        type=str,
        help="Input text directly as a string.",
    )
    source.add_argument(
        "--file", "-f",
        type=str,
        help="Path to a .txt or .pdf file.",
    )

    # Optional overrides — if NOT provided, interactive prompts are shown
    parser.add_argument(
        "--num", "-n",
        type=int,
        default=None,
        help="Number of MCQs to generate. If omitted, you will be asked interactively.",
    )
    parser.add_argument(
        "--difficulty", "-d",
        choices=["easy", "medium", "hard", "mixed"],
        default=None,
        help="Difficulty level. If omitted, you will be asked interactively.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "txt", "pdf"],
        default=None,
        help="Output format: json | txt | pdf. If omitted, you will be asked interactively.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output filename without extension (default: auto-generated).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Gemini API key (overrides .env file).",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress pipeline progress output.",
    )
    parser.add_argument(
        "--print", "-p",
        action="store_true",
        help="Print generated MCQs to terminal after generation.",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable interactive prompts. Uses defaults from .env for missing values.",
    )

    return parser.parse_args()


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def load_text_from_file(filepath: str) -> str:
    if not os.path.exists(filepath):
        cprint(C.RED, f"  ❌ File not found: {filepath}")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def print_mcqs(mcqs: list[dict]):
    print()
    cprint(C.BOLD + C.WHITE, "=" * 62)
    cprint(C.BOLD + C.WHITE, f"  GENERATED MCQs  ({len(mcqs)} total)")
    cprint(C.BOLD + C.WHITE, "=" * 62)

    for i, mcq in enumerate(mcqs, 1):
        diff  = mcq.get("difficulty", "").upper()
        topic = mcq.get("topic", "").title()
        diff_color = {"EASY": C.GREEN, "MEDIUM": C.YELLOW, "HARD": C.RED}.get(diff, C.GRAY)

        print()
        print(f"  {C.BOLD}Q{i}.{C.RESET} ", end="")
        print(f"{diff_color}[{diff}]{C.RESET} {C.GRAY}[{topic}]{C.RESET}")
        print(f"  {C.BOLD}{mcq.get('question', '')}{C.RESET}")
        print()

        for key, value in mcq.get("options", {}).items():
            if key == mcq.get("correct_answer"):
                print(f"  {C.GREEN}{C.BOLD}  ✓ {key}. {value}{C.RESET}")
            else:
                print(f"     {key}. {value}")

        print()
        cprint(C.CYAN, f"  💡 {mcq.get('explanation', '')}")
        print()
        cprint(C.GRAY, "  " + "─" * 58)


# ------------------------------------------------------------------ #
# Main                                                                 #
# ------------------------------------------------------------------ #

def main():
    banner()
    args = parse_args()

    # ── Resolve input ─────────────────────────────────────────────────
    if args.text:
        text     = args.text
        pdf_path = None
        source_label = "direct text input"
    else:
        if not os.path.exists(args.file):
            cprint(C.RED, f"  ❌ File not found: {args.file}")
            sys.exit(1)

        if args.file.lower().endswith(".pdf"):
            text      = None
            pdf_path  = args.file
            source_label = args.file
        else:
            text      = load_text_from_file(args.file)
            pdf_path  = None
            source_label = args.file

    if text is not None and len(text.strip()) < 50:
        cprint(C.RED, "  ❌ Input text is too short. Please provide at least 50 characters.")
        sys.exit(1)

    # ── Interactive prompts for missing options ────────────────────────
    interactive = not args.no_interactive

    num_questions = args.num
    difficulty    = args.difficulty
    output_format = args.format

    if interactive:
        if num_questions is None:
            num_questions = ask_num_questions()

        if difficulty is None:
            difficulty = ask_difficulty()

        if output_format is None:
            output_format = ask_output_format()

        confirm_settings(output_format, difficulty, num_questions, source_label)
    else:
        # Non-interactive: use .env defaults for missing values
        num_questions = num_questions or int(os.getenv("MCQ_PER_CHUNK", 5))
        difficulty    = difficulty    or os.getenv("DEFAULT_DIFFICULTY", "mixed")
        output_format = output_format or os.getenv("OUTPUT_FORMAT", "json")

    # ── Import pipeline ───────────────────────────────────────────────
    try:
        from pipeline import MCQPipeline
    except ImportError as e:
        cprint(C.RED, f"  ❌ Import error: {e}")
        cprint(C.RED, "     Make sure you're running from the mcq_generator/ directory.")
        sys.exit(1)

    # ── Run pipeline ──────────────────────────────────────────────────
    pipeline = MCQPipeline(api_key=args.api_key)

    if pdf_path:
        mcqs = pipeline.run_from_pdf(
            pdf_path=pdf_path,
            num_questions=num_questions,
            difficulty=difficulty,
            export_format=output_format,
            filename=args.output,
            verbose=not args.quiet,
        )
    else:
        mcqs = pipeline.run(
            text=text,
            num_questions=num_questions,
            difficulty=difficulty,
            export_format=output_format,
            filename=args.output,
            verbose=not args.quiet,
        )

    # ── Print to terminal if requested ────────────────────────────────
    if args.print and mcqs:
        print_mcqs(mcqs)

    if not mcqs:
        cprint(C.RED, "\n   No MCQs were generated. Check your API key and quota.")

    return mcqs


if __name__ == "__main__":
    main()