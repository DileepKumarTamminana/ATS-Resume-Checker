"""Streamlit UI for the ATS Resume Checker."""

from __future__ import annotations

import streamlit as st

from ats.analyzer import analyze
from ats.parser import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text

st.set_page_config(page_title="ATS Resume Checker", page_icon="📄", layout="wide")


def _score_color(score: float) -> str:
    if score >= 65:
        return "#1a9850"  # green
    if score >= 45:
        return "#f1a340"  # amber
    return "#d73027"      # red


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
    with st.expander("…or paste resume text instead"):
        pasted = st.text_area("Resume text", value=text, height=200, key="resume_text")
    return pasted or text


def _load_jd() -> str:
    st.subheader("2. Job description")
    return st.text_area(
        "Paste the job description",
        height=280,
        placeholder="Paste the full job posting here…",
        key="jd_text",
    )


def _render_gauge(result) -> None:
    color = _score_color(result.score)
    st.markdown(
        f"""
        <div style="text-align:center; padding:1rem; border-radius:12px;
                    border:2px solid {color};">
            <div style="font-size:3.5rem; font-weight:700; color:{color};">
                {result.score:.0f}<span style="font-size:1.5rem;">/100</span>
            </div>
            <div style="font-size:1.1rem; color:{color};">{result.grade}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_breakdown(result) -> None:
    st.markdown("#### Score breakdown")
    rows = [
        ("Keyword coverage", result.keyword_score),
        ("Semantic similarity", result.similarity_score),
        ("Skills coverage", result.skills_score),
        ("ATS formatting", result.formatting_score),
    ]
    for label, val in rows:
        st.write(f"**{label}** — {val:.0f}%")
        st.progress(min(int(val), 100))


def _render_results(result) -> None:
    left, right = st.columns([1, 2])
    with left:
        _render_gauge(result)
        _render_breakdown(result)

    with right:
        st.markdown("#### Suggestions")
        for tip in result.suggestions:
            st.markdown(f"- {tip}")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Missing keywords")
            if result.missing_keywords:
                st.markdown("\n".join(f"- {k}" for k in result.missing_keywords[:20]))
            else:
                st.success("All top keywords covered!")
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

    col1, col2 = st.columns(2)
    with col1:
        resume_text = _load_resume()
    with col2:
        jd_text = _load_jd()

    if st.button("Analyze", type="primary", use_container_width=True):
        if not resume_text.strip() or not jd_text.strip():
            st.warning("Please provide both a resume and a job description.")
            return
        with st.spinner("Analyzing…"):
            result = analyze(resume_text, jd_text)
        st.divider()
        _render_results(result)


if __name__ == "__main__":
    main()
