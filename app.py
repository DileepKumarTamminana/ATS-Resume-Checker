"""Streamlit UI for the ATS Resume Checker."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ats.analyzer import WEIGHTS, AnalysisResult, analyze
from ats.parser import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text

st.set_page_config(page_title="ATS Resume Checker", page_icon="📄", layout="wide")

SAMPLES = Path(__file__).parent / "samples"


def _score_color(score: float) -> str:
    if score >= 65:
        return "#1a9850"  # green
    if score >= 45:
        return "#f1a340"  # amber
    return "#d73027"      # red


def _report_text(r: AnalysisResult) -> str:
    lines = [
        "# ATS Resume Checker — Report",
        "",
        f"**Overall match: {r.score:.0f}/100 — {r.grade}**",
        "",
        "## Score breakdown",
        f"- Keyword coverage: {r.keyword_score:.0f}%",
        f"- Semantic similarity: {r.similarity_score:.0f}%",
        f"- Skills coverage: {r.skills_score:.0f}%",
        f"- ATS formatting: {r.formatting_score:.0f}%",
        "",
        "## Suggestions",
        *[f"- {t}" for t in r.suggestions],
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
        *[f"- [{'x' if c.passed else ' '}] {c.name}: {c.message}" for c in r.format_checks],
    ]
    return "\n".join(lines)


def _load_sample() -> None:
    try:
        st.session_state["resume_text"] = (SAMPLES / "resume.txt").read_text(encoding="utf-8")
        st.session_state["jd_text"] = (SAMPLES / "job.txt").read_text(encoding="utf-8")
    except OSError:
        st.warning("Sample files not found.")


def _load_resume() -> str:
    st.subheader("1. Your resume")
    uploaded = st.file_uploader(
        "Upload resume",
        type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS],
        help="PDF, DOCX, or TXT",
    )
    text = ""
    if uploaded is not None:
        try:
            text = extract_text(uploaded.getvalue(), uploaded.name)
            st.success(f"Parsed {uploaded.name} ({len(text.split())} words).")
        except UnsupportedFileType as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - surface any parse error to the user
            st.error(f"Could not parse the file: {exc}")
    with st.expander("…or paste resume text instead", expanded=not text):
        pasted = st.text_area("Resume text", value=text, height=220, key="resume_text")
    return pasted or text


def _load_jd() -> str:
    st.subheader("2. Job description")
    return st.text_area(
        "Paste the job description",
        height=300,
        placeholder="Paste the full job posting here…",
        key="jd_text",
    )


def _render_gauge(result) -> None:
    color = _score_color(result.score)
    pct = min(result.score, 100)
    st.markdown(
        f"""
        <div style="text-align:center; padding:1rem; border-radius:14px;
                    border:1px solid #ddd;">
            <div style="width:150px;height:150px;margin:auto;border-radius:50%;
                        background:conic-gradient({color} {pct * 3.6:.1f}deg, #e5e7eb 0);
                        display:flex;align-items:center;justify-content:center;">
              <div style="width:116px;height:116px;border-radius:50%;background:var(--background-color,#fff);
                          display:flex;flex-direction:column;align-items:center;justify-content:center;">
                <div style="font-size:2.6rem;font-weight:800;color:{color};line-height:1;">
                    {result.score:.0f}</div>
                <div style="font-size:.8rem;color:#888;">/ 100</div>
              </div>
            </div>
            <div style="font-size:1.15rem;font-weight:700;color:{color};margin-top:.6rem;">
                {result.grade}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_breakdown(result) -> None:
    st.markdown("#### Score breakdown")
    rows = [
        ("Keyword coverage", result.keyword_score, WEIGHTS["keywords"]),
        ("Semantic similarity", result.similarity_score, WEIGHTS["similarity"]),
        ("Skills coverage", result.skills_score, WEIGHTS["skills"]),
        ("ATS formatting", result.formatting_score, WEIGHTS["formatting"]),
    ]
    for label, val, wt in rows:
        st.write(f"**{label}** — {val:.0f}%  \n<small>weight {wt * 100:.0f}%</small>",
                 unsafe_allow_html=True)
        st.progress(min(int(val), 100))


def _render_results(result) -> None:
    left, right = st.columns([1, 2])
    with left:
        _render_gauge(result)
        total_kw = len(result.matched_keywords) + len(result.missing_keywords)
        st.caption(
            f"Matched {len(result.matched_keywords)}/{total_kw} keywords · "
            f"{len(result.matched_skills)}/"
            f"{len(result.matched_skills) + len(result.missing_skills)} skills"
        )
        st.download_button(
            "⬇ Download report",
            data=_report_text(result),
            file_name="ats-report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        _render_breakdown(result)

    with right:
        st.markdown("#### 💡 Suggestions")
        for tip in result.suggestions:
            st.markdown(f"- {tip}")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Keywords")
            miss_tab, match_tab = st.tabs(
                [f"Missing ({len(result.missing_keywords)})",
                 f"Matched ({len(result.matched_keywords)})"]
            )
            with miss_tab:
                st.markdown(
                    "\n".join(f"- {k}" for k in result.missing_keywords[:30])
                    if result.missing_keywords else "_All top keywords covered!_"
                )
            with match_tab:
                st.markdown(
                    "\n".join(f"- {k}" for k in result.matched_keywords[:30])
                    if result.matched_keywords else "_None matched._"
                )
        with col_b:
            st.markdown("#### Skills")
            if result.matched_skills:
                st.markdown("**Matched:** " + ", ".join(result.matched_skills))
            if result.missing_skills:
                st.markdown("**Missing:** " + ", ".join(result.missing_skills))
            if not result.matched_skills and not result.missing_skills:
                st.info("No specific skills detected in the job description.")

    st.markdown("#### ATS formatting checks")
    for check in result.format_checks:
        icon = "✅" if check.passed else "⚠️"
        st.markdown(f"{icon} **{check.name}** — {check.message}")


def main() -> None:
    st.title("📄 ATS Resume Checker")
    st.caption(
        "Offline resume vs. job-description analysis — keyword coverage, semantic "
        "similarity, skills gaps, and ATS formatting checks. Nothing leaves your machine."
    )
    st.button("✨ Load sample data", on_click=_load_sample)

    col1, col2 = st.columns(2)
    with col1:
        resume_text = _load_resume()
    with col2:
        jd_text = _load_jd()

    if st.button("Analyze match ⚡", type="primary", use_container_width=True):
        if not resume_text.strip() or not jd_text.strip():
            st.warning("Please provide both a resume and a job description.")
            return
        with st.spinner("Analyzing…"):
            result = analyze(resume_text, jd_text)
        st.divider()
        _render_results(result)


if __name__ == "__main__":
    main()
