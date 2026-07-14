"""Command-line entry point: `python cli.py resume.pdf --jd job.txt`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ats.analyzer import analyze
from ats.parser import extract_text_from_path


def _read(arg: str) -> str:
    """Treat arg as a file path if it exists, else as literal text."""
    p = Path(arg)
    if p.exists():
        return extract_text_from_path(p)
    return arg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ATS Resume Checker (offline).")
    parser.add_argument("resume", help="Path to resume file (PDF/DOCX/TXT).")
    parser.add_argument(
        "--jd", required=True, help="Path to job-description file, or literal text."
    )
    parser.add_argument(
        "--top-keywords", type=int, default=40, help="Number of JD keywords to score."
    )
    args = parser.parse_args(argv)

    try:
        resume_text = extract_text_from_path(args.resume)
        jd_text = _read(args.jd)
        result = analyze(resume_text, jd_text, top_keywords=args.top_keywords)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"\nOverall match score: {result.score:.1f}/100  ({result.grade})")
    print("-" * 50)
    print(f"  Keyword coverage   : {result.keyword_score:.0f}%")
    print(f"  Semantic similarity: {result.similarity_score:.0f}%")
    print(f"  Skills coverage    : {result.skills_score:.0f}%")
    print(f"  ATS formatting     : {result.formatting_score:.0f}%")

    if result.missing_keywords:
        print("\nMissing keywords:", ", ".join(result.missing_keywords[:15]))
    if result.missing_skills:
        print("Missing skills  :", ", ".join(result.missing_skills))

    print("\nSuggestions:")
    for tip in result.suggestions:
        print(f"  - {tip}")

    print("\nFormatting checks:")
    for check in result.format_checks:
        mark = "OK " if check.passed else "!! "
        print(f"  [{mark}] {check.name}: {check.message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
