"""Rule-based ATS-friendliness checks on the raw resume text.

Real ATS parsers choke on tables, images, multi-column layouts, exotic fonts,
and missing standard sections. We can't see the original layout from extracted
text, but several problems leave detectable fingerprints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"https?://\S+|linkedin\.com/\S+", re.IGNORECASE)
BULLET_RE = re.compile(r"^[\s]*[•\-\*•▪●‣⁃]", re.MULTILINE)

STANDARD_SECTIONS = {
    "experience": ["experience", "employment", "work history", "professional experience"],
    "education": ["education", "academic"],
    "skills": ["skills", "technical skills", "competencies"],
}


@dataclass
class FormatCheck:
    name: str
    passed: bool
    message: str


def check_formatting(text: str) -> list[FormatCheck]:
    """Run all formatting heuristics and return a list of check results."""
    checks: list[FormatCheck] = []
    lower = text.lower()
    word_count = len(text.split())

    # Contact info
    checks.append(
        FormatCheck(
            "Email present",
            bool(EMAIL_RE.search(text)),
            "Found an email address." if EMAIL_RE.search(text)
            else "No email address detected — ATS may fail to route your application.",
        )
    )
    checks.append(
        FormatCheck(
            "Phone present",
            bool(PHONE_RE.search(text)),
            "Found a phone number." if PHONE_RE.search(text)
            else "No phone number detected.",
        )
    )
    checks.append(
        FormatCheck(
            "Links present",
            bool(URL_RE.search(text)),
            "Found a LinkedIn/portfolio link." if URL_RE.search(text)
            else "No LinkedIn or portfolio link found (optional, but recommended).",
        )
    )

    # Standard sections
    for label, aliases in STANDARD_SECTIONS.items():
        present = any(a in lower for a in aliases)
        checks.append(
            FormatCheck(
                f"Section: {label.title()}",
                present,
                f"'{label.title()}' section detected."
                if present
                else f"No clear '{label.title()}' section heading — use a standard heading.",
            )
        )

    # Bullet points aid ATS parsing of accomplishments
    bullets = len(BULLET_RE.findall(text))
    checks.append(
        FormatCheck(
            "Uses bullet points",
            bullets >= 3,
            f"Found {bullets} bullet points."
            if bullets >= 3
            else "Few/no bullet points detected — use bullets to list achievements.",
        )
    )

    # Length sanity: too short usually means parsing failed or resume is thin.
    if word_count < 150:
        length_ok, msg = False, (
            f"Only ~{word_count} words extracted — this may indicate an image-based "
            "or unparseable resume, or one that is too short."
        )
    elif word_count > 1200:
        length_ok, msg = False, (
            f"~{word_count} words — quite long. Aim for 1-2 pages for most roles."
        )
    else:
        length_ok, msg = True, f"~{word_count} words — a reasonable length."
    checks.append(FormatCheck("Length", length_ok, msg))

    # Non-ASCII / special characters can garble in older ATS.
    weird = sum(1 for c in text if ord(c) > 0x2122)
    checks.append(
        FormatCheck(
            "Character encoding",
            weird < 15,
            "No problematic special characters detected."
            if weird < 15
            else f"Found {weird} unusual glyphs — fancy symbols/icons can break ATS parsing.",
        )
    )

    return checks
