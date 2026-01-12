## Cover Letter Generator

CLI script that turns a fixed candidate summary + fixed sample letter into a tailored cover letter using the OpenAI API, based on a job description, then saves it as text and an optional PDF.

### Setup
- Python 3.13+
- Install deps (via uv or pip): `uv sync` or `pip install .`
- Set `OPENAI_API_KEY` in your environment or a `.env` file next to `main.py`.

### Usage
Capture the generated letter from stdout (for Automator) and optionally write files:

```bash
python main.py \
  --job-description /path/to/jd.txt \
  --pdf-out CoverLetter_JaneStreet.pdf \
  --text-out CoverLetter_JaneStreet.txt
```

Key flags:
- `--job-description` is required; pass text directly or a path to a `.txt` file.
- `--skip-pdf` to only emit text; `--quiet` to silence info logs when Automator is calling.
- `--model`, `--pdf-out`, `--text-out` customize generation and outputs.

The PDF filename defaults to the model-provided `companyName_title.pdf` in `/Users/hanu/Documents/Personal/Cover letters` when `--pdf-out` is omitted.
