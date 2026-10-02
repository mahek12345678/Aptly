"""Regression tests for Profile page data consistency."""
from __future__ import annotations

import re
from pathlib import Path
import pytest

from app.services.resume_parser import DeterministicResumeParser, extract_raw_text


MOCK_DOCX_DIR = Path(
    r"c:\Users\lenovo\OneDrive\Desktop\job tracker\backend\uploads\resumes\abad24ed-52d6-4754-b43b-d0696dcb5d95"
)
MOCK_DOCX_PATH = Path(
    r"c:\Users\lenovo\OneDrive\Desktop\job tracker\backend\uploads\resumes\abad24ed-52d6-4754-b43b-d0696dcb5d95\71fde7b986b049e78d1ce4bb403d5488.docx"
)


def test_mock_swe_resume_fixture_consistency():
    """Verify that mock_swe_resume_aarav_mehta.docx parses deterministically with correct counts and associations."""
    target_path = MOCK_DOCX_PATH
    if not target_path.exists() and MOCK_DOCX_DIR.exists():
        docx_files = list(MOCK_DOCX_DIR.glob("*.docx"))
        if docx_files:
            target_path = docx_files[0]

    assert target_path.exists(), f"Mock resume fixture not found at {MOCK_DOCX_PATH}"

    raw_text = extract_raw_text(target_path)
    parser = DeterministicResumeParser()
    data = parser.parse(raw_text)

    # 1. Projects: Exactly 3 unique parent projects (QueueFlow, CollabCode, TraceLite)
    projects = data.get("projects", [])
    assert len(projects) == 3, f"Expected 3 projects, got {len(projects)}"
    titles = [p["title"] for p in projects]
    assert any("QueueFlow" in t for t in titles), f"QueueFlow not found in {titles}"
    assert any("CollabCode" in t for t in titles), f"CollabCode not found in {titles}"
    assert any("TraceLite" in t for t in titles), f"TraceLite not found in {titles}"

    # Verify no header bleed into project titles
    for t in titles:
        assert not re.search(r"^(achievements?|leadership|skills?|technical skills)", t, re.IGNORECASE)

    # 2. Verified skills: Count > 0 and no category names in skills
    skills = data.get("skills", [])
    assert len(skills) >= 20, f"Expected at least 20 skills, got {len(skills)}"
    skill_categories = data.get("skill_categories", {})
    assert len(skill_categories) == 4, f"Expected 4 categories, got {len(skill_categories)}"
    expected_categories = {"Languages", "Backend & Web", "Data & Systems", "Tools & Cloud"}
    assert set(skill_categories.keys()) == expected_categories

    for cat_name in expected_categories:
        assert cat_name.lower() not in [s.lower() for s in skills]

    # Deduplication within and across skills
    assert len(skills) == len({s.lower() for s in skills}), "Skills list contains duplicates"

    # 3. Experience: Single associated entry with clean date range
    experience = data.get("experience", [])
    assert len(experience) == 1, f"Expected 1 experience entry, got {len(experience)}"
    exp = experience[0]
    assert exp["company"] == "CloudNova Labs"
    assert exp["role"] == "Software Engineering Intern"
    assert exp["location"] == "Bengaluru, India"
    assert "May 2026" in exp["dates"] and "Jul 2026" in exp["dates"]
    assert exp["start_date"] == "May 2026"
    assert exp["end_date"] == "Jul 2026"
    assert len(exp["bullets"]) == 3

    # 4. Text Cleanup: Formatting artifacts resolved
    for bullet in exp["bullets"]:
        assert "client\nside" not in bullet
        assert "high\ntraffic" not in bullet
        assert not re.search(r"\b\w+\s*\n\s*\w+\b", bullet)

    # 5. Education: Full institution name and graduation year
    education = data.get("education", [])
    assert len(education) >= 1
    edu = education[0]
    assert edu["institution"] == "National Institute of Technology, Surat"
    assert edu["grad_year"] == "2027"

    # 6. Achievements: 3 distinct items parsed (including 350+ DSA problems)
    achievements = data.get("achievements", [])
    assert len(achievements) == 3, f"Expected 3 achievements, got {len(achievements)}"
    ach_text = " ".join(achievements)
    assert "350+" in ach_text or "data structures" in ach_text.lower()
    assert "hackathon" in ach_text.lower()

    # 7. Name & Headline
    assert data.get("name") == "AARAV MEHTA"
    headline = data.get("headline", "")
    assert "Software Engineer" in headline


def test_clean_token_removes_accidental_linebreaks():
    """Verify that _clean_token properly joins hyphenated and non-hyphenated newline breaks."""
    parser = DeterministicResumeParser()

    token1 = parser._clean_token("client-\nside rendering")
    assert token1 == "client-side rendering"

    token2 = parser._clean_token("high\ntraffic deployment\nhistory")
    assert token2 == "high traffic deployment history"

    token3 = parser._clean_token("  Docker-based    local\ndevelopment   ")
    assert token3 == "Docker-based local development"


def test_experience_header_parsing_with_subword_boundaries():
    """Verify that company names with substrings matching months or states are not falsely split."""
    parser = DeterministicResumeParser()

    # 'CloudNova Labs' contains 'Nov' and 'wa', which previously broke substring checks
    parsed = parser._parse_experience_header(
        "Software Engineering Intern - CloudNova Labs | Bengaluru, India | May 2026 - Jul 2026"
    )
    assert parsed["company"] == "CloudNova Labs"
    assert parsed["role"] == "Software Engineering Intern"
    assert parsed["location"] == "Bengaluru, India"
    assert "May 2026" in parsed["dates"] and "Jul 2026" in parsed["dates"]
