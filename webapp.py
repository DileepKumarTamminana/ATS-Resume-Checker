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
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ats.analyzer import WEIGHTS, AnalysisResult, analyze
from ats.parser import UnsupportedFileType, extract_text

SAMPLES = Path(__file__).parent / "samples"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ATS Resume Checker</title>
<style>
  :root {{
    --bg: #f6f7fb; --card: #ffffff; --fg: #1f2937; --muted: #6b7280;
    --border: #e5e7eb; --accent: #2563eb; --accent-fg: #ffffff;
    --track: #e5e7eb; --chip: #eef2ff; --chip-fg: #3730a3;
    --shadow: 0 1px 3px rgba(0,0,0,.08), 0 8px 24px rgba(0,0,0,.05);
    --ok: #16a34a; --warn: #d97706; --bad: #dc2626;
  }}
  html[data-theme="dark"] {{
    --bg: #0b1020; --card: #131a2b; --fg: #e5e7eb; --muted: #9aa4b2;
    --border: #26314a; --accent: #3b82f6; --accent-fg: #ffffff;
    --track: #26314a; --chip: #1e2a44; --chip-fg: #bfdbfe;
    --shadow: 0 1px 3px rgba(0,0,0,.4), 0 12px 32px rgba(0,0,0,.35);
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         margin: 0; background: var(--bg); color: var(--fg); line-height: 1.55; }}
  .wrap {{ max-width: 1040px; margin: 0 auto; padding: 0 1rem 4rem; }}
  header.top {{ position: sticky; top: 0; z-index: 10; backdrop-filter: blur(8px);
    background: color-mix(in srgb, var(--bg) 82%, transparent);
    border-bottom: 1px solid var(--border); }}
  .topbar {{ max-width: 1040px; margin: 0 auto; padding: .7rem 1rem;
    display: flex; align-items: center; gap: .6rem; }}
  .topbar h1 {{ font-size: 1.15rem; margin: 0; }}
  .topbar .sub {{ color: var(--muted); font-size: .85rem; margin-left: .2rem; }}
  .spacer {{ flex: 1; }}
  .iconbtn {{ background: var(--card); border: 1px solid var(--border); color: var(--fg);
    border-radius: 10px; padding: .45rem .7rem; cursor: pointer; font-size: .9rem; }}
  .iconbtn:hover {{ border-color: var(--accent); }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    padding: 1.1rem 1.2rem; box-shadow: var(--shadow); }}
  form.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1.2rem; }}
  @media (max-width: 760px) {{ form.grid {{ grid-template-columns: 1fr; }} }}
  fieldset {{ border: 0; padding: 0; margin: 0; }}
  legend {{ font-weight: 700; margin-bottom: .5rem; font-size: 1rem; }}
  .legend-row {{ display: flex; align-items: center; gap: .5rem; margin-bottom: .5rem; }}
  .legend-row .count {{ margin-left: auto; color: var(--muted); font-size: .8rem; font-weight: 400; }}
  .drop {{ border: 1.5px dashed var(--border); border-radius: 10px; padding: .75rem;
    text-align: center; color: var(--muted); font-size: .88rem; cursor: pointer;
    transition: border-color .15s, background .15s; margin-bottom: .6rem; }}
  .drop:hover, .drop.drag {{ border-color: var(--accent); background: var(--chip); color: var(--fg); }}
  .drop input {{ display: none; }}
  .drop b {{ color: var(--fg); }}
  textarea {{ width: 100%; min-height: 240px; font: inherit; padding: .7rem;
    border: 1px solid var(--border); border-radius: 10px; resize: vertical;
    background: var(--bg); color: var(--fg); }}
  textarea:focus {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
  .actions {{ grid-column: 1 / -1; display: flex; gap: .6rem; flex-wrap: wrap; }}
  button.primary {{ flex: 1; min-width: 200px; padding: .85rem; font-size: 1.05rem;
    font-weight: 700; border: 0; border-radius: 12px; background: var(--accent);
    color: var(--accent-fg); cursor: pointer; }}
  button.primary:hover {{ filter: brightness(1.05); }}
  button.primary:disabled {{ opacity: .7; cursor: progress; }}
  button.ghost {{ padding: .85rem 1.1rem; border: 1px solid var(--border);
    background: var(--card); color: var(--fg); border-radius: 12px; cursor: pointer; font-weight: 600; }}
  button.ghost:hover {{ border-color: var(--accent); }}

  .results {{ margin-top: 1.4rem; display: grid; gap: 1rem; }}
  .hero {{ display: grid; grid-template-columns: auto 1fr; gap: 1.4rem; align-items: center; }}
  @media (max-width: 620px) {{ .hero {{ grid-template-columns: 1fr; text-align: center; }} }}
  .ring {{ --deg: 0deg; width: 132px; height: 132px; border-radius: 50%;
    display: grid; place-items: center; margin: auto;
    background: conic-gradient(var(--c) var(--deg), var(--track) 0); }}
  .ring .inner {{ width: 104px; height: 104px; border-radius: 50%; background: var(--card);
    display: grid; place-items: center; }}
  .ring .n {{ font-size: 2.3rem; font-weight: 800; color: var(--c); line-height: 1; }}
  .ring .of {{ font-size: .75rem; color: var(--muted); }}
  .grade {{ font-size: 1.35rem; font-weight: 700; color: var(--c); }}
  .grade + p {{ margin: .25rem 0 0; color: var(--muted); }}
  .hero-actions {{ margin-top: .7rem; display: flex; gap: .5rem; flex-wrap: wrap; }}

  .bars {{ display: grid; gap: .75rem; }}
  .metric {{ }}
  .metric .lbl {{ display: flex; align-items: baseline; gap: .4rem; font-size: .92rem; }}
  .metric .lbl b {{ font-weight: 700; }}
  .metric .lbl .wt {{ color: var(--muted); font-size: .75rem; }}
  .metric .lbl .val {{ margin-left: auto; font-weight: 700; }}
  .bar {{ background: var(--track); border-radius: 6px; overflow: hidden; height: 10px; margin-top: .3rem; }}
  .bar > div {{ height: 100%; border-radius: 6px; transition: width .6s ease; }}

  .two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
  @media (max-width: 760px) {{ .two {{ grid-template-columns: 1fr; }} }}
  h3.sec {{ margin: 0 0 .6rem; font-size: 1rem; }}
  .tabs {{ display: flex; gap: .4rem; margin-bottom: .6rem; }}
  .tab {{ border: 1px solid var(--border); background: var(--bg); color: var(--muted);
    padding: .25rem .7rem; border-radius: 999px; cursor: pointer; font-size: .82rem; font-weight: 600; }}
  .tab.active {{ background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }}
  .chip {{ display: inline-block; border-radius: 999px; padding: .2rem .6rem;
    margin: .15rem; font-size: .82rem; background: var(--chip); color: var(--chip-fg); }}
  .chip.ok {{ background: color-mix(in srgb, var(--ok) 18%, transparent); color: var(--ok); }}
  .chip.miss {{ background: color-mix(in srgb, var(--bad) 15%, transparent); color: var(--bad); }}
  ul.tips {{ margin: 0; padding-left: 1.2rem; }}
  ul.tips li {{ margin: .3rem 0; }}
  .checks {{ list-style: none; margin: 0; padding: 0; display: grid; gap: .4rem; }}
  .checks li {{ display: flex; gap: .5rem; align-items: flex-start; padding: .5rem .7rem;
    border: 1px solid var(--border); border-radius: 10px; }}
  .checks li .ic {{ flex: 0 0 auto; }}
  .ok {{ color: var(--ok); }} .warn {{ color: var(--warn); }}
  .flash {{ padding: .8rem 1rem; border-radius: 10px; border: 1px solid var(--border);
    background: color-mix(in srgb, var(--warn) 12%, transparent); color: var(--fg); }}
  .empty {{ color: var(--muted); font-style: italic; }}
  .toast {{ position: fixed; bottom: 1.2rem; left: 50%; transform: translateX(-50%) translateY(20px);
    background: var(--fg); color: var(--bg); padding: .6rem 1rem; border-radius: 10px;
    opacity: 0; transition: all .25s; pointer-events: none; font-size: .9rem; }}
  .toast.show {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
</style></head><body>
<header class="top"><div class="topbar">
  <span style="font-size:1.3rem">📄</span>
  <h1>ATS Resume Checker</h1>
  <span class="sub">offline · private</span>
  <span class="spacer"></span>
  <button class="iconbtn" type="button" id="sampleBtn" title="Fill with sample data">✨ Load sample</button>
  <button class="iconbtn" type="button" id="themeBtn" title="Toggle theme">🌙</button>
</div></header>

<div class="wrap">
<form class="grid" method="post" enctype="multipart/form-data" id="form">
  <fieldset class="card">
    <div class="legend-row"><legend>1 · Resume</legend>
      <span class="count" id="resumeCount">0 words</span></div>
    <label class="drop" id="drop">
      <input type="file" name="resume_file" id="resumeFile" accept=".pdf,.docx,.txt,.md">
      <span id="dropLabel">📎 Drop a file or <b>browse</b> (PDF · DOCX · TXT · MD)</span>
    </label>
    <textarea name="resume_text" id="resumeText" placeholder="…or paste your resume text here">{resume_text}</textarea>
  </fieldset>
  <fieldset class="card">
    <div class="legend-row"><legend>2 · Job description</legend>
      <span class="count" id="jdCount">0 words</span></div>
    <textarea name="jd_text" id="jdText" placeholder="Paste the full job posting here…">{jd_text}</textarea>
  </fieldset>
  <div class="actions">
    <button class="primary" type="submit" id="analyzeBtn">Analyze match ⚡</button>
    <button class="ghost" type="reset" id="clearBtn">Clear</button>
  </div>
</form>
{result}
</div>
<div class="toast" id="toast"></div>

<script>
(function() {{
  var root = document.documentElement;
  var saved = null;
  try {{ saved = localStorage.getItem("ats-theme"); }} catch (e) {{}}
  if (saved) root.setAttribute("data-theme", saved);
  else root.setAttribute("data-theme",
    window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  function syncThemeIcon() {{
    document.getElementById("themeBtn").textContent =
      root.getAttribute("data-theme") === "dark" ? "☀️" : "🌙";
  }}
  syncThemeIcon();
  document.getElementById("themeBtn").addEventListener("click", function() {{
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {{ localStorage.setItem("ats-theme", next); }} catch (e) {{}}
    syncThemeIcon();
  }});

  function words(s) {{ s = (s || "").trim(); return s ? s.split(/\\s+/).length : 0; }}
  function bindCount(area, out) {{
    var a = document.getElementById(area), o = document.getElementById(out);
    function upd() {{ o.textContent = words(a.value) + " words"; }}
    a.addEventListener("input", upd); upd();
  }}
  bindCount("resumeText", "resumeCount");
  bindCount("jdText", "jdCount");

  var drop = document.getElementById("drop"),
      file = document.getElementById("resumeFile"),
      dropLabel = document.getElementById("dropLabel");
  file.addEventListener("change", function() {{
    if (file.files.length) dropLabel.innerHTML = "📄 <b>" + file.files[0].name + "</b> ready to analyze";
  }});
  ["dragenter", "dragover"].forEach(function(ev) {{
    drop.addEventListener(ev, function(e) {{ e.preventDefault(); drop.classList.add("drag"); }});
  }});
  ["dragleave", "drop"].forEach(function(ev) {{
    drop.addEventListener(ev, function(e) {{ e.preventDefault(); drop.classList.remove("drag"); }});
  }});
  drop.addEventListener("drop", function(e) {{
    if (e.dataTransfer.files.length) {{
      file.files = e.dataTransfer.files;
      file.dispatchEvent(new Event("change"));
    }}
  }});

  var form = document.getElementById("form");
  form.addEventListener("submit", function() {{
    var b = document.getElementById("analyzeBtn");
    b.disabled = true; b.textContent = "Analyzing…";
  }});
  document.getElementById("clearBtn").addEventListener("click", function() {{
    setTimeout(function() {{
      document.getElementById("resumeText").dispatchEvent(new Event("input"));
      document.getElementById("jdText").dispatchEvent(new Event("input"));
      dropLabel.innerHTML = "📎 Drop a file or <b>browse</b> (PDF · DOCX · TXT · MD)";
    }}, 0);
  }});

  function toast(msg) {{
    var t = document.getElementById("toast");
    t.textContent = msg; t.classList.add("show");
    setTimeout(function() {{ t.classList.remove("show"); }}, 1800);
  }}

  document.getElementById("sampleBtn").addEventListener("click", function() {{
    fetch("/sample").then(function(r) {{ return r.json(); }}).then(function(d) {{
      document.getElementById("resumeText").value = d.resume || "";
      document.getElementById("jdText").value = d.jd || "";
      document.getElementById("resumeText").dispatchEvent(new Event("input"));
      document.getElementById("jdText").dispatchEvent(new Event("input"));
      toast("Sample data loaded — hit Analyze");
    }}).catch(function() {{ toast("Sample not available"); }});
  }});

  // Keyword tabs
  document.querySelectorAll("[data-tabgroup]").forEach(function(group) {{
    group.querySelectorAll(".tab").forEach(function(tab) {{
      tab.addEventListener("click", function() {{
        group.querySelectorAll(".tab").forEach(function(t) {{ t.classList.remove("active"); }});
        tab.classList.add("active");
        var target = tab.getAttribute("data-target");
        group.parentElement.querySelectorAll("[data-panel]").forEach(function(p) {{
          p.style.display = p.getAttribute("data-panel") === target ? "block" : "none";
        }});
      }});
    }});
  }});

  // Report copy / download
  var reportEl = document.getElementById("reportData");
  if (reportEl) {{
    var report = reportEl.value;
    var dl = document.getElementById("downloadBtn"), cp = document.getElementById("copyBtn");
    if (dl) dl.addEventListener("click", function() {{
      var blob = new Blob([report], {{ type: "text/markdown" }});
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "ats-report.md";
      document.body.appendChild(a); a.click(); a.remove();
    }});
    if (cp) cp.addEventListener("click", function() {{
      navigator.clipboard.writeText(report).then(function() {{ toast("Report copied to clipboard"); }})
        .catch(function() {{ toast("Copy failed"); }});
    }});
    var r = document.querySelector(".results");
    if (r) r.scrollIntoView({{ behavior: "smooth", block: "start" }});
  }}
}})();
</script>
</body></html>"""


def _color(score: float) -> str:
    if score >= 65:
        return "var(--ok)"
    if score >= 45:
        return "var(--warn)"
    return "var(--bad)"


def _bar(label: str, val: float, weight: float | None = None) -> str:
    wt = f"<span class='wt'>weight {weight * 100:.0f}%</span>" if weight is not None else ""
    return (
        f"<div class='metric'><div class='lbl'><b>{html.escape(label)}</b>{wt}"
        f"<span class='val'>{val:.0f}%</span></div>"
        f"<div class='bar'><div style='width:{min(val, 100):.0f}%;"
        f"background:{_color(val)}'></div></div></div>"
    )


def _chips(items: list[str], cls: str = "") -> str:
    if not items:
        return "<span class='empty'>none</span>"
    c = f" {cls}" if cls else ""
    return "".join(f"<span class='chip{c}'>{html.escape(i)}</span>" for i in items)


def _report_text(r: AnalysisResult) -> str:
    """Plain-text / Markdown report the user can copy or download."""
    lines = [
        "# ATS Resume Checker — Report",
        "",
        f"**Overall match: {r.score:.0f}/100 — {r.grade}**",
        "",
        "## Score breakdown",
        f"- Keyword coverage:   {r.keyword_score:.0f}%",
        f"- Semantic similarity:{r.similarity_score:>5.0f}%",
        f"- Skills coverage:    {r.skills_score:.0f}%",
        f"- ATS formatting:     {r.formatting_score:.0f}%",
        "",
        "## Suggestions",
    ]
    lines += [f"- {t}" for t in r.suggestions]
    lines += [
        "",
        f"## Matched keywords ({len(r.matched_keywords)})",
        ", ".join(r.matched_keywords) or "none",
        "",
        f"## Missing keywords ({len(r.missing_keywords)})",
        ", ".join(r.missing_keywords) or "none",
        "",
        "## Skills",
        "Matched: " + (", ".join(r.matched_skills) or "none"),
        "Missing: " + (", ".join(r.missing_skills) or "none"),
        "",
        "## ATS formatting checks",
    ]
    lines += [
        f"- [{'x' if c.passed else ' '}] {c.name}: {c.message}"
        for c in r.format_checks
    ]
    return "\n".join(lines)


def render_result(r: AnalysisResult) -> str:
    color = _color(r.score)
    deg = f"{min(r.score, 100) * 3.6:.1f}deg"
    total_kw = len(r.matched_keywords) + len(r.missing_keywords)

    checks = "".join(
        f"<li class='{'ok' if c.passed else 'warn'}'>"
        f"<span class='ic'>{'✅' if c.passed else '⚠️'}</span>"
        f"<span><strong>{html.escape(c.name)}</strong> — {html.escape(c.message)}</span></li>"
        for c in r.format_checks
    )
    tips = "".join(f"<li>{html.escape(t)}</li>" for t in r.suggestions)

    return f"""
    <div class="results">
      <div class="card hero">
        <div class="ring" style="--c:{color}; --deg:{deg}">
          <div class="inner">
            <div class="n">{r.score:.0f}</div><div class="of">/ 100</div>
          </div>
        </div>
        <div>
          <div class="grade" style="color:{color}">{html.escape(r.grade)}</div>
          <p>Matched <strong>{len(r.matched_keywords)}</strong> of <strong>{total_kw}</strong>
             top job keywords and <strong>{len(r.matched_skills)}</strong> of
             <strong>{len(r.matched_skills) + len(r.missing_skills)}</strong> detected skills.</p>
          <div class="hero-actions">
            <button class="iconbtn" type="button" id="downloadBtn">⬇ Download report</button>
            <button class="iconbtn" type="button" id="copyBtn">📋 Copy report</button>
          </div>
        </div>
      </div>

      <div class="card">
        <h3 class="sec">Score breakdown</h3>
        <div class="bars">
          {_bar("Keyword coverage", r.keyword_score, WEIGHTS["keywords"])}
          {_bar("Semantic similarity", r.similarity_score, WEIGHTS["similarity"])}
          {_bar("Skills coverage", r.skills_score, WEIGHTS["skills"])}
          {_bar("ATS formatting", r.formatting_score, WEIGHTS["formatting"])}
        </div>
      </div>

      <div class="card">
        <h3 class="sec">💡 Suggestions</h3>
        <ul class="tips">{tips}</ul>
      </div>

      <div class="two">
        <div class="card">
          <h3 class="sec">Keywords</h3>
          <div class="tabs" data-tabgroup="kw">
            <span class="tab active" data-target="missing">Missing ({len(r.missing_keywords)})</span>
            <span class="tab" data-target="matched">Matched ({len(r.matched_keywords)})</span>
          </div>
          <div data-panel="missing">{_chips(r.missing_keywords[:30], "miss")}</div>
          <div data-panel="matched" style="display:none">{_chips(r.matched_keywords[:30], "ok")}</div>
        </div>
        <div class="card">
          <h3 class="sec">Skills</h3>
          <p style="margin:.2rem 0 .4rem"><strong>Matched</strong></p>
          {_chips(r.matched_skills, "ok")}
          <p style="margin:.7rem 0 .4rem"><strong>Missing from resume</strong></p>
          {_chips(r.missing_skills, "miss")}
        </div>
      </div>

      <div class="card">
        <h3 class="sec">ATS formatting checks</h3>
        <ul class="checks">{checks}</ul>
      </div>
    </div>
    <textarea id="reportData" style="display:none">{html.escape(_report_text(r))}</textarea>
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
    def _send(self, body: str, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = urlparse(self.path).path
        if path == "/sample":
            resume = jd = ""
            try:
                resume = (SAMPLES / "resume.txt").read_text(encoding="utf-8")
                jd = (SAMPLES / "job.txt").read_text(encoding="utf-8")
            except OSError:
                pass
            self._send(
                json.dumps({"resume": resume, "jd": jd}),
                content_type="application/json; charset=utf-8",
            )
            return
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
            result_html = f"<div class='results'><div class='flash'>⚠️ {html.escape(error)}</div></div>"
        elif resume_text and jd_text:
            result_html = render_result(analyze(resume_text, jd_text))
        elif resume_text or jd_text:
            result_html = (
                "<div class='results'><div class='flash'>⚠️ Please provide both a "
                "resume and a job description.</div></div>"
            )

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
