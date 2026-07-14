# Running the ATS Resume Checker

All commands are run from the project root:

```bash
cd ATS-Resume-Checker
```

> **Windows note:** if `python` isn't on your PATH, use the `py` launcher
> instead (e.g. `py webapp.py`). On macOS/Linux use `python3`.

## Option 1 — Zero-dependency web app (recommended)

Runs on the Python standard library alone — nothing to install.

```bash
python webapp.py               # open http://localhost:8000
python webapp.py --port 9000   # use a different port
```

Stop the server with **Ctrl+C**.

PDF/DOCX *upload* additionally needs `pypdf` / `python-docx`; pasting text and
`.txt` upload work with no dependencies:

```bash
python -m pip install pypdf python-docx
```

## Option 2 — Streamlit web app (nicer UI)

```bash
python -m pip install streamlit
python -m streamlit run app.py     # opens http://localhost:8501
```

## Option 3 — Command line

```bash
python cli.py samples/resume.txt --jd samples/job.txt
```

`--jd` also accepts literal text instead of a file path. The resume argument
accepts `.pdf`, `.docx`, `.txt`, or `.md`.

## Run the tests

```bash
python -m pip install pytest
python -m pytest -q
```
