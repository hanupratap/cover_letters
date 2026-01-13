from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, field_validator
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from rich.logging import RichHandler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("cover_letters")

BASE_DIR = Path(__file__).resolve().parent
BASE_OUTPUT_DIR = Path("/Users/hanu/Documents/Personal/Cover letters")
INPUT_DIR = BASE_DIR / "inputs"
SUMMARY_PATH = INPUT_DIR / "summary.txt"
SAMPLE_LETTER_PATH = INPUT_DIR / "sample_letter.txt"
PROMPT_PATH = INPUT_DIR / "prompt.txt"
DEFAULT_LLM_MODEL = "gpt-4o"
# DEFAULT_LLM_MODEL = "gpt-5.2-mini"

# PDF layout constants
PDF_PAGE_SIZE = LETTER
PDF_MARGIN = 72
PDF_FONT_NAME = "Helvetica"
PDF_FONT_SIZE = 11
PDF_LINE_HEIGHT = 15
PDF_PARAGRAPH_SPACING = 10
PDF_PARAGRAPH_SPACER = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a cover letter (text + PDF) from a job description using OpenAI."
    )
    parser.add_argument(
        "-j",
        "--job-description",
        required=True,
        help="Job description text or a path to a .txt file containing it.",
    )
    return parser.parse_args()


def load_template(path: Path, label: str) -> str:
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Unable to read {label} from {path}.") from exc
    if not content:
        raise RuntimeError(f"{label} file is empty: {path}.")
    return content


def build_prompt(job_description: str, summary: str, sample_letter: str) -> str:
    template = load_template(PROMPT_PATH, "prompt")
    try:
        return template.format(
            job_description=job_description,
            summary=summary,
            sample_letter=sample_letter,
        ).strip()
    except KeyError as exc:
        raise RuntimeError(f"Prompt template missing placeholder: {exc}") from exc


def load_job_description(value: str) -> str:
    candidate_path = Path(value)
    try:
        if candidate_path.exists():
            return candidate_path.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return value.strip()


class LetterPayload(BaseModel):
    filename: str
    letter: str

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        filename = value.strip()
        if not filename:
            raise ValueError("LLM output missing filename.")
        
        # Remove path separators
        if "/" in filename or "\\" in filename:
            raise ValueError("LLM filename must not include path separators.")
        
        # Remove extension if present
        if filename.lower().endswith((".pdf", ".txt")):
            filename = filename[:-4].strip()
        
        if not filename:
            raise ValueError("LLM filename is empty after cleanup.")
        
        # Validate character constraints
        if not filename.isascii():
            raise ValueError("LLM filename must use ASCII characters only.")
        if " " in filename:
            raise ValueError("LLM filename must use underscores instead of spaces.")
        if not all(ch.isalnum() or ch == "_" for ch in filename):
            raise ValueError(
                "LLM filename must contain only letters, numbers, and underscores."
            )
        
        return filename

    @field_validator("letter")
    @classmethod
    def validate_letter(cls, value: str) -> str:
        letter = value.strip()
        if not letter:
            raise ValueError("LLM output missing letter text.")
        return letter


def generate_letter_payload(client: OpenAI, prompt: str, model: str) -> tuple[str, str]:
    logger.info("Calling OpenAI API...")
    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=LetterPayload,
        )
    except (OSError, ValueError) as exc:
        logger.error(f"[red]API call failed: {exc}[/red]")
        raise
    
    logger.info("[green]✓ API response received[/green]")
    message = response.choices[0].message
    
    if message.refusal:
        raise ValueError(f"LLM refused the request: {message.refusal}")
    
    payload = message.parsed
    if payload is None:
        raise ValueError("LLM output missing structured payload.")
    
    return payload.filename, payload.letter


def default_pdf_path(filename: str) -> Path:
    return BASE_OUTPUT_DIR / f"{filename}.pdf"


def write_pdf(letter_text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generating PDF: [yellow]{output_path}[/yellow]")

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=PDF_PAGE_SIZE,
        leftMargin=PDF_MARGIN,
        rightMargin=PDF_MARGIN,
        topMargin=PDF_MARGIN,
        bottomMargin=PDF_MARGIN,
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName=PDF_FONT_NAME,
        fontSize=PDF_FONT_SIZE,
        leading=PDF_LINE_HEIGHT,
        spaceAfter=PDF_PARAGRAPH_SPACING,
    )

    story: list[Paragraph | Spacer] = []
    for paragraph in letter_text.split("\n\n"):
        if not paragraph.strip():
            continue
        story.append(Paragraph(paragraph.replace("\n", "<br/>"), body))
        story.append(Spacer(1, PDF_PARAGRAPH_SPACER))

    doc.build(story)
    logger.info(f"[green bold]✓ Saved {output_path}[/green bold]")


def write_text_file(letter_text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(letter_text, encoding="utf-8")
    logger.info(f"[green]✓ Saved text to {output_path}[/green]")


def main() -> None:
    args = parse_args()

    job_description = load_job_description(args.job_description)
    summary = load_template(SUMMARY_PATH, "summary")
    sample_letter = load_template(SAMPLE_LETTER_PATH, "sample letter")
    prompt = build_prompt(
        job_description=job_description,
        summary=summary,
        sample_letter=sample_letter,
    )

    logger.info("Generating cover letter from job description")
    client = OpenAI()
    filename, letter_text = generate_letter_payload(
        client=client, prompt=prompt, model=DEFAULT_LLM_MODEL 
    )

    # Always print the letter text so Automator or shell callers can capture it.
    print(letter_text)

    pdf_path = default_pdf_path(filename)
    write_pdf(letter_text, pdf_path)


if __name__ == "__main__":
    main()
