"""Core scoring: keyword overlap, TF-IDF similarity, skills gap, formatting.

The overall score is a weighted blend of:
  * keyword coverage  — fraction of the JD's important keywords present in the resume
  * semantic similarity — TF-IDF cosine similarity between resume and JD
  * skills coverage    — fraction of JD-detected skills present in the resume
  * formatting         — fraction of ATS formatting checks passed
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .formatting import FormatCheck, check_formatting
from .skills import find_skills
from .textstats import WORD_RE, cosine_similarity, rank_keywords

# Weights for the composite score (must sum to 1.0).
WEIGHTS = {
    "keywords": 0.40,
    "similarity": 0.25,
    "skills": 0.25,
    "formatting": 0.10,
}


@dataclass
class AnalysisResult:
    score: float                              # 0-100 overall
    keyword_score: float                      # 0-100
    similarity_score: float                   # 0-100
    skills_score: float                       # 0-100
    formatting_score: float                   # 0-100
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    format_checks: list[FormatCheck] = field(default_factory=list)

    @property
    def grade(self) -> str:
        if self.score >= 80:
            return "Excellent match"
        if self.score >= 65:
            return "Strong match"
        if self.score >= 50:
            return "Moderate match — room to improve"
        if self.score >= 35:
            return "Weak match"
        return "Poor match"

    @property
    def suggestions(self) -> list[str]:
        tips: list[str] = []
        if self.missing_keywords:
            top = ", ".join(self.missing_keywords[:10])
            tips.append(f"Add or emphasize these job keywords where truthful: {top}.")
        if self.missing_skills:
            tips.append(
                "Highlight these skills from the job description if you have them: "
                + ", ".join(self.missing_skills[:10])
                + "."
            )
        for check in self.format_checks:
            if not check.passed:
                tips.append(check.message)
        if self.similarity_score < 50:
            tips.append(
                "Mirror the job description's language more closely — reuse its exact "
                "role titles, tools, and phrasing where accurate."
            )
        if not tips:
            tips.append("Strong alignment. Tailor the summary line to the exact role title.")
        return tips


def extract_keywords(text: str, top_n: int = 40) -> list[str]:
    """Pick the most salient JD keywords via TF-IDF over its own sentences."""
    return rank_keywords(text, top_n=top_n, ngram_range=(1, 2))


def _keyword_coverage(resume_text: str, jd_keywords: list[str]) -> tuple[list[str], list[str]]:
    resume_lower = resume_text.lower()
    matched, missing = [], []
    for kw in jd_keywords:
        # word-boundary-ish containment; multi-word keywords checked as substrings
        pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
        if re.search(pattern, resume_lower):
            matched.append(kw)
        else:
            missing.append(kw)
    return matched, missing


def _similarity(resume_text: str, jd_text: str) -> float:
    return cosine_similarity(resume_text, jd_text)


def analyze(resume_text: str, jd_text: str, top_keywords: int = 40) -> AnalysisResult:
    """Analyze a resume against a job description. Text in, structured result out."""
    resume_text = (resume_text or "").strip()
    jd_text = (jd_text or "").strip()

    if not resume_text or not jd_text:
        raise ValueError("Both resume text and job description text are required.")

    # Keyword coverage
    jd_keywords = extract_keywords(jd_text, top_n=top_keywords)
    matched_kw, missing_kw = _keyword_coverage(resume_text, jd_keywords)
    keyword_score = (len(matched_kw) / len(jd_keywords) * 100) if jd_keywords else 0.0

    # Semantic similarity
    similarity_score = _similarity(resume_text, jd_text) * 100

    # Skills gap
    jd_skills = find_skills(jd_text)
    resume_skills = find_skills(resume_text)
    matched_skills = sorted(jd_skills & resume_skills)
    missing_skills = sorted(jd_skills - resume_skills)
    skills_score = (len(matched_skills) / len(jd_skills) * 100) if jd_skills else 100.0

    # Formatting
    format_checks = check_formatting(resume_text)
    passed = sum(1 for c in format_checks if c.passed)
    formatting_score = (passed / len(format_checks) * 100) if format_checks else 0.0

    overall = (
        keyword_score * WEIGHTS["keywords"]
        + similarity_score * WEIGHTS["similarity"]
        + skills_score * WEIGHTS["skills"]
        + formatting_score * WEIGHTS["formatting"]
    )

    return AnalysisResult(
        score=round(overall, 1),
        keyword_score=round(keyword_score, 1),
        similarity_score=round(similarity_score, 1),
        skills_score=round(skills_score, 1),
        formatting_score=round(formatting_score, 1),
        matched_keywords=matched_kw,
        missing_keywords=missing_kw,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        format_checks=format_checks,
    )
