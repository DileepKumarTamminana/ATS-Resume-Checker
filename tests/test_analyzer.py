"""Tests for the ATS analyzer, skills, and formatting modules."""

import pytest

from ats.analyzer import analyze, extract_keywords
from ats.formatting import check_formatting
from ats.skills import find_skills

RESUME = """
Jane Doe
jane.doe@example.com | +1 555 123 4567 | linkedin.com/in/janedoe

Professional Experience
- Built REST APIs in Python using Django and FastAPI on AWS.
- Deployed microservices with Docker and Kubernetes.
- Wrote SQL queries against PostgreSQL and built CI/CD pipelines with Jenkins.

Skills
Python, SQL, Docker, Kubernetes, AWS, Django, FastAPI, Git

Education
B.S. in Computer Science
"""

JOB_DESCRIPTION = """
We are hiring a Senior Python Engineer. You will build REST APIs and
microservices deployed on AWS using Docker and Kubernetes. Experience with
Terraform and Kafka is a strong plus. Strong SQL and PostgreSQL skills required.
"""


def test_find_skills_detects_known_skills():
    skills = find_skills(RESUME)
    assert "python" in skills
    assert "kubernetes" in skills
    assert "aws" in skills


def test_find_skills_word_boundary():
    # "go" should not match inside "goal"; "r" is not a tracked alias alone
    assert "go" not in find_skills("We set a clear goal for the team.")


def test_extract_keywords_nonempty():
    kws = extract_keywords(JOB_DESCRIPTION, top_n=20)
    assert kws
    assert any("python" in k for k in kws)


def test_analyze_returns_scores_in_range():
    result = analyze(RESUME, JOB_DESCRIPTION)
    for val in (
        result.score,
        result.keyword_score,
        result.similarity_score,
        result.skills_score,
        result.formatting_score,
    ):
        assert 0 <= val <= 100


def test_analyze_identifies_missing_skills():
    result = analyze(RESUME, JOB_DESCRIPTION)
    # Terraform and Kafka are in the JD but not the resume
    assert "terraform" in result.missing_skills
    assert "kafka" in result.missing_skills
    # Python is in both
    assert "python" in result.matched_skills


def test_analyze_good_resume_scores_reasonably():
    result = analyze(RESUME, JOB_DESCRIPTION)
    assert result.score > 40


def test_analyze_requires_both_inputs():
    with pytest.raises(ValueError):
        analyze("", JOB_DESCRIPTION)
    with pytest.raises(ValueError):
        analyze(RESUME, "   ")


def test_formatting_flags_missing_contact_info():
    checks = {c.name: c for c in check_formatting("Just some words without contact info.")}
    assert not checks["Email present"].passed


def test_formatting_passes_full_resume():
    checks = {c.name: c for c in check_formatting(RESUME)}
    assert checks["Email present"].passed
    assert checks["Section: Experience"].passed
