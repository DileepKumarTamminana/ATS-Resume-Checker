"""Zero-dependency web UI (Python stdlib only).

A fallback for environments where Streamlit can't be installed. Run:

    python webapp.py           # serves on http://localhost:8000
    python webapp.py --port 9000

Then open the URL in a browser, paste/upload a resume and a job description,
and submit. Uses only the standard library — no pip install required (PDF/DOCX
upload additionally needs pypdf / python-docx if you want those formats).
"""

from __future__ import annotations

import argparse
import html
import http.server
from urllib.parse import parse_qs

from ats.analyzer import AnalysisResult, analyze
from ats.parser import UnsupportedFileType, extract_text

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ATS Resume Checker</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 960px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
  h1 {{ margin-bottom: .2rem; }}
  .sub {{ color: #666; margin-top: 0; }}
  form {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
  fieldset {{ border: 1px solid #ccc; border-radius: 8px; }}
  textarea {{ width: 100%; box-sizing: border-box; min-height: 220px; font: inherit; }}
  button {{ grid-column: 1 / -1; padding: .8rem; font-size: 1.05rem; font-weight: 600;
           border: 0; border-radius: 8px; background: #2563eb; color: #fff; cursor: pointer; }}
  .gauge {{ text-align: center; border: 2px solid var(--c); border-radius: 12px;
           padding: 1rem; }}
  .gauge .n {{ font-size: 3rem; font-weight: 700; color: var(--c); }}
  .bar {{ background: #e5e7eb; border-radius: 6px; overflow: hidden; height: 14px; margin:.2rem 0 .8rem; }}
  .bar > div {{ height: 100%; background: #2563eb; }}
  .cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
  .chip {{ display: inline-block; background: #eef; border-radius: 12px; padding: .1rem .5rem;
          margin: .15rem; font-size: .85rem; }}
  .ok {{ color: #16a34a; }} .warn {{ color: #d97706; }}
  li {{ margin: .2rem 0; }}
</style></head><body>
<h1>📄 ATS Resume Checker</h1>
<p class="sub">Offline resume vs. job-description analysis. Nothing leaves this machine.</p>
<form method="post" enctype="multipart/form-data">
  <fieldset><legend>1. Resume</legend>
    <p><input type="file" name="resume_file" accept=".pdf,.docx,.txt,.md"></p>
    <p>…or paste text:</p>
    <textarea name="resume_text">{resume_text}</textarea>
  </fieldset>
  <fieldset><legend>2. Job description</legend>
    <textarea name="jd_text" placeholder="Paste the full job posting here…">{jd_text}</textarea>
  </fieldset>
  <button type="submit">Analyze</button>
</form>
{result}
</body></html>"""


def _color(score: float) -> str:
    if score >= 65:
        return "#16a34a"
    if score >= 45:
        return "#d97706"
    return "#dc2626"


def _bar(label: str, val: float) -> str:
    return (
        f"<div><strong>{html.escape(label)}</strong> — {val:.0f}%"
        f"<div class='bar'><div style='width:{min(val,100):.0f}%'></div></div></div>"
    )


def _chips(items: list[str]) -> str:
    if not items:
        return "<em>none</em>"
    return "".join(f"<span class='chip'>{html.escape(i)}</span>" for i in items)


def render_result(r: AnalysisResult) -> str:
    checks = "".join(
        f"<li class='{'ok' if c.passed else 'warn'}'>"
        f"{'✅' if c.passed else '⚠️'} <strong>{html.escape(c.name)}</strong> — "
        f"{html.escape(c.message)}</li>"
        for c in r.format_checks
    )
    tips = "".join(f"<li>{html.escape(t)}</li>" for t in r.suggestions)
    return f"""
    <hr>
    <div class="cols">
      <div class="gauge" style="--c:{_color(r.score)}">
        <div class="n">{r.score:.0f}<span style="font-size:1.2rem">/100</span></div>
        <div>{html.escape(r.grade)}</div>
      </div>
      <div>
        {_bar("Keyword coverage", r.keyword_score)}
        {_bar("Semantic similarity", r.similarity_score)}
        {_bar("Skills coverage", r.skills_score)}
        {_bar("ATS formatting", r.formatting_score)}
      </div>
    </div>
    <h3>Suggestions</h3><ul>{tips}</ul>
    <div class="cols">
      <div><h3>Missing keywords</h3>{_chips(r.missing_keywords[:20])}</div>
      <div><h3>Skills</h3>
        <p><strong>Matched:</strong> {_chips(r.matched_skills)}</p>
        <p><strong>Missing:</strong> {_chips(r.missing_skills)}</p>
      </div>
    </div>
    <h3>ATS formatting checks</h3><ul>{checks}</ul>
    """


def _parse_multipart(body: bytes, boundary: bytes) -> dict[str, dict]:
    """Minimal multipart/form-data parser (stdlib `cgi` was removed in 3.13).

    Returns {field_name: {"filename": str|None, "value": bytes}}.
    """
    fields: dict[str, dict] = {}
    delimiter = b"--" + boundary
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        head, _, data = part.partition(b"\r\n\r\n")
        headers = head.decode("utf-8", "replace")
        name = filename = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("content-disposition"):
                for token in line.split(";"):
                    token = token.strip()
                    if token.startswith("name="):
                        name = token[5:].strip('"')
                    elif token.startswith("filename="):
                        filename = token[9:].strip('"')
        if name is not None:
            fields[name] = {"filename": filename, "value": data}
    return fields


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        self._send(PAGE.format(resume_text="", jd_text="", result=""))

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")

        resume_text = jd_text = ""
        error = ""

        if content_type.startswith("multipart/form-data"):
            boundary = content_type.split("boundary=", 1)[-1].strip('"').encode()
            fields = _parse_multipart(body, boundary)

            resume_text = fields.get("resume_text", {}).get("value", b"").decode("utf-8", "replace").strip()
            jd_text = fields.get("jd_text", {}).get("value", b"").decode("utf-8", "replace").strip()

            file_field = fields.get("resume_file")
            if file_field and file_field.get("filename"):
                try:
                    resume_text = extract_text(file_field["value"], file_field["filename"])
                except UnsupportedFileType as exc:
                    error = str(exc)
                except Exception as exc:  # noqa: BLE001
                    error = f"Could not parse file: {exc}"
        else:
            parsed = parse_qs(body.decode("utf-8", "replace"))
            resume_text = (parsed.get("resume_text", [""])[0]).strip()
            jd_text = (parsed.get("jd_text", [""])[0]).strip()

        result_html = ""
        if error:
            result_html = f"<hr><p class='warn'>⚠️ {html.escape(error)}</p>"
        elif resume_text and jd_text:
            result_html = render_result(analyze(resume_text, jd_text))
        elif resume_text or jd_text:
            result_html = "<hr><p class='warn'>⚠️ Please provide both a resume and a job description.</p>"

        self._send(
            PAGE.format(
                resume_text=html.escape(resume_text),
                jd_text=html.escape(jd_text),
                result=result_html,
            )
        )

    def log_message(self, *args) -> None:  # silence per-request logging
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="ATS Resume Checker — stdlib web UI.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = http.server.HTTPServer((args.host, args.port), Handler)
    print(f"ATS Resume Checker running at http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
