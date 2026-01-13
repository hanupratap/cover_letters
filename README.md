# Cover Letters

CLI tool that generates a tailored cover letter using the OpenAI API. It combines a job description (passed on the command line) with local template files and writes a PDF to a fixed output directory while printing the letter to stdout.

## Project layout

The script reads three input templates:
- `summary.txt`
- `sample_letter.txt`
- `prompt.txt`

By default, `main.py` looks for these under `input/` (singular). This repo currently stores them in `inputs/`, so either rename the folder to `input/` or update `INPUT_DIR` in `main.py` to match.

## Setup
- Python 3.13+
- Install deps (via uv or pip): `uv sync` or `pip install .`
- Set `OPENAI_API_KEY` in your environment or a `.env` file next to `main.py`.

## Usage

```bash
python main.py --job-description /path/to/jd.txt
```

Notes:
- `--job-description` is required and accepts either a `.txt` path or raw text.
- The generated letter is always printed to stdout.
- A PDF is always written to `/Users/hanu/Documents/Personal/Cover letters/<filename>.pdf`.

## Automator app (macOS)

Create an Automator Application that prompts for a job description and runs the script.

Steps:
1. Open Automator and create a new **Application**.
2. Add **Ask for Text** and set the prompt to "Job description".
3. Add **Run Shell Script** and set:
   - Shell: `/bin/zsh`
   - Pass input: `as arguments`
4. Paste this script:

```zsh
#!/bin/zsh
set -eo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

cd /Users/hanu/Projects/cover_letters

job_description="$1"

# Use full path if PATH still doesn't find uv
/opt/homebrew/bin/uv run python main.py \
  --job-description "$job_description"
```

Save the app and run it; the generated letter prints to stdout (Automator Results) and the PDF is written to the default output directory.

## Output format

The model response must include:
- `filename` (ASCII, underscores instead of spaces; no extension)
- `letter` (the full cover letter text)

To change the model or output directory, edit `DEFAULT_LLM_MODEL` or `BASE_OUTPUT_DIR` in `main.py`.
