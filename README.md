# ATS Resume Checker

An **offline** tool that scores how well a resume matches a job description —
the way an Applicant Tracking System (ATS) roughly would. It runs entirely on
your machine: no API keys, no network calls, nothing leaves your computer.

## What it checks

| Signal | What it measures |
|---|---|
| **Keyword coverage** | Fraction of the job description's most important keywords found in your resume (TF-IDF ranked, unigrams + bigrams). |
| **Semantic similarity** | TF-IDF cosine similarity between the full resume and job description. |
| **Skills coverage** | Fraction of recognized skills in the JD (e.g. Python, AWS, Kubernetes) present in your resume. |
| **ATS formatting** | Heuristic checks: contact info, standard section headings, bullet usage, length, and problematic characters. |

These roll up into a weighted **0–100 match score** with concrete, actionable
suggestions.

## Install

```bash
pip install -r requirements.txt
```

## Usage

### Web app — zero dependencies (recommended if you can't `pip install`)

Runs on the Python standard library alone — no packages required:

```bash
python webapp.py            # open http://localhost:8000
python webapp.py --port 9000
```

(PDF/DOCX *upload* additionally needs `pypdf` / `python-docx`; pasting text and
`.txt` upload work with no dependencies.)

### Web app — Streamlit (nicer UI)

```bash
pip install streamlit
streamlit run app.py
```

### Command line

```bash
python cli.py path/to/resume.pdf --jd path/to/job_description.txt
# --jd also accepts literal text instead of a file path
```

## Project layout

```
webapp.py         Zero-dependency web UI (stdlib http.server)
app.py            Streamlit web UI
cli.py            Command-line interface
ats/
  parser.py       Extract text from PDF/DOCX/TXT
  analyzer.py     Scoring engine (keywords, similarity, skills, formatting)
  textstats.py    Pure-Python TF-IDF + cosine similarity (no deps)
  skills.py       Skill/alias dictionary + detection
  formatting.py   Rule-based ATS formatting checks
tests/            Pytest suite
```

## Development

```bash
pip install pytest
pytest
```

## How the score is computed

```
overall = 0.40 * keyword_coverage
        + 0.25 * semantic_similarity
        + 0.25 * skills_coverage
        + 0.10 * formatting
```

Weights live in `ats/analyzer.py` (`WEIGHTS`) and are easy to tune.

## Notes & limitations

- Text is extracted from the file, so the tool can't see the *visual* layout
  (multi-column, tables as images). It infers formatting problems from
  fingerprints in the extracted text.
- The skills dictionary in `ats/skills.py` is a curated signal, not exhaustive —
  extend it for your domain.
- This is a heuristic aid, not a real ATS. Use it to catch obvious gaps, not as
  a guarantee.
