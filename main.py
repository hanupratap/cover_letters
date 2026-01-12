from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from textwrap import dedent, wrap

from dotenv import load_dotenv
from openai import OpenAI
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from rich.logging import RichHandler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("cover_letters")

BASE_OUTPUT_DIR = Path("/Users/hanu/Documents/Personal/Cover letters")

DEFAULT_SUMMARY = dedent(
    """
    Hanupratap Singh Chauhan
    +1-510-684-9740| hanupratap.chauhan@berkeley.edu | linkedin.com/in/hanupratap | github.com/hanupratap

    Education
    University of California, Berkeley – Haas School of Business	Expected March 2026
    Master of Financial Engineering	Berkeley, CA

    Birla Institute of Technology & Science, Pilani	July 2021
    Bachelor of Electrical and Electronics Engineering	Hyderabad, India

    Professional Experience
    PanAgora Asset Management	Boston, MA
    Quantitative Research Intern, Dynamic Equity	Oct 2025 – Jan 2026
    Earnings-Call Audio Alpha (Project)
    Timestamp Extraction: Replaced FactSet timestamps with NVIDIA NeMo forced alignment on Azure GPUs; aligned 253K+ calls (2.7TB) to speaker timestamps (30s/call, 99.9% success) and saved ~$36K/yr.
    Feature Extraction: Extracted 50+ features (pitch, stability, spectral texture) via Librosa, Praat, PyTorch.
    Factor + Signal Build: Aggregated segment features into 465 stock factors in Polars (speaker weights + cross-sectional standardization), then combined into one signal using Ridge/XGBoost/ElasticNet.
    Performance: IC t-stat 3.2 and IR 1.23 on US large-cap equities (5D horizon, 13-year backtest; Ridge).

    J.P. Morgan	Mumbai, India
    Quantitative Researcher, Equities QIS (Quantitative Investment Strategies)	Jul 2021 – Mar 2025
    Systematic Execution: Developed and deployed execution logic for 40+ systematic strategies (~$30B notional) in a shared Python framework adopted by 4 desks; standardized workflows and reduced manual execution risk.
    Risk-Parity Optimizer: Implemented a CCD-based risk-parity solver ~20% faster than CVXOPT to scale optimization across large instrument universes.
    Global CTA: Implemented trend-following futures across 5 asset classes using a custom momentum signal with 10% vol targeting and risk-parity sizing.
    Equity Factor L/S: Built delta-neutral Value/Momentum/Quality long/short portfolios with liquidity + borrow-aware constraints; maintained |beta|<0.05.
    Options: Backtested rolling index collars (OTM put-spread + covered call) with delta-based strike/roll rules and Greeks/risk monitoring to quantify protection vs carry.
    Index Product Delivery: Led quant delivery for S&P/BlackRock index products; owned methodology specs, backtest validation, and production handoff through launch.

    Projects
    Agentic Investment Research | GQG Partners	Aug 2025 – Oct 2025
    Built a LangGraph Supervisor/Worker multi-agent system for fundamental research using ReAct-style retrieval/tool-use and a ReWOO-like plan→write flow; enforced claim→evidence→citation outputs with citation-coverage + contradiction checks to generate auditable investment memos.

    FinBERT-Based FOMC Sentiment Rotation Strategy	Apr 2024 – May 2024
    Built an event-driven strategy scoring FOMC text with FinBERT and rotating SPY vs 7–10Y Treasuries using calibrated thresholds, volatility targeting, and transaction-cost modeling; backtests delivered comparable returns to SPY with ~7% lower maximum drawdown.

    Relevant Skills & Interests
    Languages: Python, C++, SQL
    ML/Data: PyTorch, scikit-learn, XGBoost, Polars, Pandas, NumPy; JAX, NeMo, LangGraph
    Quant/Infra: Factor models (Barra/PCA), time series, convex optimization, risk parity; Docker, Git, distributed pipelines
    Interests: Skiing, scuba diving, basketball, cinema
    """
).strip()

DEFAULT_SAMPLE_LETTER = dedent(
    """
    Dear Hiring Team,

    I'm applying for the [Role] position at [Company] in [Location]. Most recently, during my internship at PanAgora Asset Management, I built a production-grade research pipeline from end to end and delivered both measurable investment impact (IC t-stat 3.2; IR 1.23) and meaningful operational savings ($36k/yr), work that resulted in a full-time offer.

    Previously, I spent ~4 years in Equities QIS at J.P. Morgan building systematic strategies and research infrastructure. I’m currently an MFE candidate at UC Berkeley (expected March 2026), where I continue to deepen my work in statistical learning, optimization, and quantitative modeling.

    I'm interested in teams that combine strong research fundamentals with pragmatic engineering to produce scalable, robust alpha. I’d welcome the chance to discuss how my experience in systematic research and productionizing models can contribute to [Company].

    Best regards,
    Hanupratap Singh Chauhan
    """
).strip()


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
    parser.add_argument(
        "--model",
        default="gpt-4-turbo",
        help="OpenAI chat model to use (default: gpt-4-turbo).",
    )
    parser.add_argument(
        "--pdf-out",
        type=Path,
        help="Optional PDF output path. Defaults to CoverLetter_<Company>.pdf.",
    )
    parser.add_argument(
        "--text-out",
        type=Path,
        help="Optional path to save the raw letter text (UTF-8).",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Generate only text output and skip PDF creation.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info logs; only show warnings/errors. Useful when called from Automator.",
    )
    return parser.parse_args()


def build_prompt(job_description: str) -> str:
    return dedent(
        f"""
        Write a professional cover letter.
        Rules:
        - Use ONLY facts from the summary or sample
        - Use simple and easy to read language, avoiding complex vocabulary
        - 120-180 words
        - Match the tone and structure of the sample
        - Do NOT invent metrics or offers
        - Return a JSON object with keys "filename" and "letter"
        - "filename" must be companyName_title using underscores instead of spaces (ASCII letters/numbers/underscore only, no extension)
        - "letter" must be the final letter text only
        - Encode line breaks in "letter" as \\n so the JSON is valid
        - Do not wrap the JSON in code fences
        - Tailor the letter to the job description if provided; otherwise keep it general
        - Use the company name and role title from the job description; do not leave placeholders

        Job description (optional):
        {job_description}

        Candidate summary:
        {DEFAULT_SUMMARY}

        Sample letter:
        {DEFAULT_SAMPLE_LETTER}
        """
    ).strip()


def unwrap_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def parse_llm_payload(raw_content: str) -> tuple[str, str]:
    cleaned = unwrap_code_fence(raw_content)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("[red]Invalid JSON from LLM output.[/red]")
        raise ValueError("LLM output was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("LLM output JSON must be an object.")

    filename = str(payload.get("filename", "")).strip()
    letter_text = str(payload.get("letter", "")).strip()

    if not filename:
        raise ValueError("LLM output missing filename.")
    if not letter_text:
        raise ValueError("LLM output missing letter text.")
    if "/" in filename or "\\" in filename:
        raise ValueError("LLM filename must not include path separators.")

    if filename.lower().endswith(".pdf"):
        filename = filename[:-4]
    if filename.lower().endswith(".txt"):
        filename = filename[:-4]

    filename = filename.strip()
    if not filename:
        raise ValueError("LLM output filename is empty after cleanup.")
    if not filename.isascii():
        raise ValueError("LLM filename must use ASCII characters only.")
    if " " in filename:
        raise ValueError("LLM filename must use underscores instead of spaces.")
    if not all(ch.isalnum() or ch == "_" for ch in filename):
        raise ValueError(
            "LLM filename must contain only letters, numbers, and underscores."
        )

    return filename, letter_text


def generate_letter_payload(client: OpenAI, prompt: str, model: str) -> tuple[str, str]:
    try:
        logger.info("Calling OpenAI API...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        logger.info("[green]✓ API response received[/green]")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[red]API call failed: {exc}[/red]")
        raise

    content = response.choices[0].message.content.strip()
    return parse_llm_payload(content)


def default_pdf_path(filename: str) -> Path:
    return BASE_OUTPUT_DIR / f"{filename}.pdf"


def write_pdf(letter_text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=LETTER)
    _, height = LETTER
    x_margin = 72
    y_margin = 72
    y = height - y_margin
    line_height = 14

    logger.info(f"Generating PDF: [yellow]{output_path}[/yellow]")
    c.setFont("Times-Roman", 12)

    for paragraph in letter_text.split("\n\n"):
        lines = wrap(paragraph, 95)
        for line in lines:
            c.drawString(x_margin, y, line)
            y -= line_height
            if y < y_margin:
                c.showPage()
                c.setFont("Times-Roman", 12)
                y = height - y_margin
        y -= line_height

    c.save()
    logger.info(f"[green bold]✓ Saved {output_path}[/green bold]")


def write_text_file(letter_text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(letter_text, encoding="utf-8")
    logger.info(f"[green]✓ Saved text to {output_path}[/green]")


def load_job_description(value: str) -> str:
    candidate_path = Path(value)
    try:
        if candidate_path.exists():
            return candidate_path.read_text(encoding="utf-8").strip()
    except OSError:
        # Treat overly long or invalid paths as inline text.
        return value.strip()
    return value.strip()


def main() -> None:
    args = parse_args()
    if args.quiet:
        logger.setLevel(logging.WARNING)

    job_description = load_job_description(args.job_description)
    prompt = build_prompt(job_description=job_description)

    logger.info("Generating cover letter from job description")
    client = OpenAI()
    filename, letter_text = generate_letter_payload(
        client=client, prompt=prompt, model=args.model
    )

    # Always print the letter text so Automator or shell callers can capture it.
    print(letter_text)

    if args.text_out:
        write_text_file(letter_text, args.text_out)

    if not args.skip_pdf:
        pdf_path = args.pdf_out or default_pdf_path(filename)
        write_pdf(letter_text, pdf_path)


if __name__ == "__main__":
    main()
