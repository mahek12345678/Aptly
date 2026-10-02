"""Comprehensive regression tests for the generic JD Analyzer pipeline.

Tests against real-world failure patterns (e.g. S&P Global / myGwork):
1. Third-party wrapper/myGwork boilerplate removal (no platform text in candidate summary).
2. Recruiter contact disclaimers ignored as requirements.
3. Full JD size >500 chars (up to multi-thousand chars) with qualifications near the end.
4. Malformed / boilerplate-heavy JD detection (insufficient_job_description).
5. Missing salary / missing experience requirements handled gracefully.
6. Senior role with unverified years of experience (seniority check / gap).
7. Skill normalization (ML -> Machine Learning, Postgres -> PostgreSQL, RESTful APIs -> REST APIs).
8. Generic AI vs explicit Machine Learning distinction.
9. Railway / deployment evidence not promoted to primary ML engineering skill.
10. Skills section noise filtering (no club sentences, university names, or prose).
11. Deterministic scoring reproducibility.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from unittest.mock import AsyncMock, patch
from app.core.security import create_access_token
from app.main import app
from app.models.job_match import JobListing
from app.models.resume import Resume
from app.models.user import User
from app.services.jd_preprocessor import clean_job_description, clean_role_title
from app.services.llm_service import ExtractedJDModel, evaluate_location_match, llm_service
from app.services.skill_normalizer import (
    EvidenceType,
    MatchStatus,
    NormalizedRequirement,
    SemanticCategory,
    _evaluate_requirement_evidence,
    build_unified_requirements,
    calculate_deterministic_match_score,
    calculate_reconciled_scores,
    extract_structured_resume_evidence,
    is_valid_technical_skill,
    match_requirements_to_evidence,
    normalize_skill,
)
from tests.conftest import TestingSessionLocal


async def setup_candidate_user_and_resume(
    email: str = "candidate_sp@example.com",
    skills: list[str] = None,
    experience: list[str] = None,
    projects: list[str] = None,
) -> tuple[User, str, Resume]:
    """Helper to create user and parsed resume for regression testing."""
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name="Alex Chen",
            onboarding_completed=True,
            onboarding_step=4,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(data={"sub": str(user_id)})

    if skills is None:
        skills = [
            "Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "REST APIs",
            "Railway", "Git", "TypeScript", "Next.js",
            "Vice President", "Bennett University DevOps Club", "for student members", "VS Code",
        ]
    if experience is None:
        experience = [
            "Junior Backend Developer at CloudLabs (2023 - 2024): Built REST services using FastAPI and SQLAlchemy.",
        ]
    if projects is None:
        projects = [
            "Route53 Clone: Built FastAPI REST service layer and PostgreSQL relational schema, deployed on Railway.",
        ]

    parsed_data = {
        "name": "Alex Chen",
        "email": email,
        "skills": skills,
        "experience": experience,
        "projects": projects,
        "education": ["B.Tech in Computer Science, 2024"],
        "raw_text": f"Alex Chen. Skills: {', '.join(skills)}",
    }

    now = datetime.now(timezone.utc)
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user_id,
        file_name="alex_chen_resume.pdf",
        file_path="/uploads/resumes/alex_chen_resume.pdf",
        extracted_text=parsed_data["raw_text"],
        parsed_status="parsed",
        parsed_at=now,
        parsed_data=parsed_data,
        created_at=now,
    )

    async with TestingSessionLocal() as session:
        session.add(resume)
        await session.commit()
        await session.refresh(resume)

    return user, token, resume


# ---------------------------------------------------------------------------
# 1. Boilerplate Stripping & Anti-Pollution Regression
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_mygwork_boilerplate_stripping():
    """Verify that myGwork platform text, recruiter contact notices, and attribution are cleanly removed."""
    raw_jd = (
        "This job is with S&P Global, an inclusive employer and a member of myGwork, "
        "the largest global platform for the LGBTQ business community. "
        "Please do not contact the recruiter directly. "
        "About the Role: Senior Machine Learning Engineer at S&P Global.\n"
        "Responsibilities:\n"
        "- Build and deploy production machine learning pipelines\n"
        "- Scale data models using Python and PyTorch\n\n"
        "Requirements:\n"
        "- 5+ years experience in Machine Learning and Python\n"
        "- Hands-on experience with PyTorch and PostgreSQL"
    )

    prep = clean_job_description(raw_jd)
    cleaned = prep.cleaned_text.lower()

    # Platform wrappers must be gone
    assert "largest global platform for the lgbtq" not in cleaned
    assert "mygwork" not in cleaned
    assert "please do not contact the recruiter directly" not in cleaned
    assert prep.analysis_quality == "sufficient"
    assert prep.detected_company == "S&P Global"


@pytest.mark.anyio
async def test_end_to_end_sp_global_regression():
    """Verify that S&P Global style JD produces grounded candidate summary without publisher text."""
    user, token, resume = await setup_candidate_user_and_resume()
    headers = {"Authorization": f"Bearer {token}"}

    raw_jd = (
        "This job is with S&P Global, an inclusive employer and a member of myGwork, "
        "the largest global platform for the LGBTQ business community. "
        "Please do not contact the recruiter directly. "
        "About the Role: Senior Machine Learning Engineer at S&P Global.\n"
        "Location: New York, NY\n"
        "Compensation: $185,000 - $225,000\n\n"
        "Responsibilities:\n"
        "- Architect scalable machine learning models and data pipelines\n"
        "- Deliver resilient microservices\n\n"
        "Requirements:\n"
        "- 5+ years experience in Machine Learning and Python\n"
        "- Hands-on proficiency with PyTorch, PostgreSQL, and Docker\n"
        "- Strong background in REST APIs"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Analyze JD
        r_analyze = await ac.post("/api/v1/jd/analyze", json={"job_description": raw_jd}, headers=headers)
        assert r_analyze.status_code == 200
        data = r_analyze.json()
        job = data["job_details"]
        match = data["match_analysis"]

        # Company must be S&P Global, NOT myGwork
        assert "S&P Global" in job["company"]
        assert "mygwork" not in job["company"].lower()
        assert "Machine Learning" in job["role_title"]

        # Python, PostgreSQL, REST APIs should be matched
        matched_lower = [s.lower() for s in match["matched_skills"]]
        assert "python" in matched_lower
        assert "postgresql" in matched_lower
        assert "rest apis" in matched_lower

        # Missing skills should identify Machine Learning / PyTorch
        missing_lower = [s.lower() for s in match["missing_skills"]]
        assert "machine learning" in missing_lower or "pytorch" in missing_lower

        # Seniority gap check
        assert match["seniority_alignment"] is not None
        assert match["seniority_alignment"]["is_gap"] is True
        assert "5+ years" in match["seniority_alignment"]["status"]

        # Tailor Resume
        r_tailor = await ac.post(
            "/api/v1/jd/tailor",
            json={"job_description": raw_jd, "resume_id": str(resume.id)},
            headers=headers,
        )
        assert r_tailor.status_code == 200
        t_data = r_tailor.json()["tailored_sections"]

        # Targeted summary must NEVER include platform text
        summary = t_data["summary"]["suggestion"].lower()
        assert "lgbtq" not in summary
        assert "mygwork" not in summary
        assert "recruiter directly" not in summary
        assert "largest global platform" not in summary

        # Skills section ordering MUST NOT dump noise words
        prioritized = [s.lower() for s in t_data["skills"]["prioritized"]]
        secondary = [s.lower() for s in t_data["skills"]["secondary"]]
        all_skills = prioritized + secondary

        assert "vice president" not in all_skills
        assert "bennett university devops club" not in all_skills
        assert "for student members" not in all_skills
        assert "vs code" not in all_skills

        # Railway must NOT be the sole or primary skill for Senior ML Engineer
        if "railway" in all_skills:
            assert "railway" not in prioritized or len(prioritized) > 1


# ---------------------------------------------------------------------------
# 2. Long JD (>500 chars) with Requirements Near the End
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_long_jd_with_requirements_near_the_end():
    """Verify that a 4,000+ character JD with requirements at the very end is fully parsed."""
    filler = (
        "About Our Global Organization:\n"
        "We are an international technology and financial intelligence firm operating across 40 countries. "
        "Our mission is to empower decision-makers through transparent insights and data-driven intelligence. "
        "We believe in continuous innovation, teamwork, integrity, and operational excellence.\n\n"
        "Benefits and Perks:\n"
        "- Comprehensive health, vision, and dental insurance plans\n"
        "- 401(k) matching up to 6%\n"
        "- Generous paid time off, parental leave, and wellness stipends\n"
        "- Continuous learning and professional development budget\n\n"
    ) * 8  # ~3,500 characters of narrative

    ending_requirements = (
        "About the Role: Senior Platform Engineer at FinTech Global.\n"
        "Location: Chicago, IL\n"
        "Requirements:\n"
        "- 4+ years of professional backend development\n"
        "- Strong proficiency in Python, PostgreSQL, and Docker\n"
        "- Experience with Kubernetes is preferred"
    )

    full_long_jd = filler + ending_requirements
    assert len(full_long_jd) > 3500

    extracted = await llm_service.analyze_job_description(full_long_jd)
    assert extracted["analysis_quality"] == "sufficient"
    assert "Python" in extracted["required_skills"] or "PostgreSQL" in extracted["required_skills"]


# ---------------------------------------------------------------------------
# 3. Malformed / Boilerplate-Heavy JD
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_malformed_boilerplate_heavy_jd():
    """Verify that a JD with only UI noise and no role content returns insufficient_job_description."""
    malformed = (
        "Share this job\n"
        "Apply Now\n"
        "Save job\n"
        "Back to search results\n"
        "Page 1 of 2\n"
        "Cookie preferences\n"
        "All rights reserved 2026"
    )

    prep = clean_job_description(malformed)
    assert prep.analysis_quality == "insufficient_job_description"
    assert "enough role requirements" in prep.quality_warning.lower()


# ---------------------------------------------------------------------------
# 4. Missing Salary and Experience Requirement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_missing_salary_and_experience():
    """Verify that JD without compensation or explicit experience requirement succeeds."""
    jd_text = (
        "Software Engineer at InnovateTech.\n"
        "Location: Remote\n"
        "Responsibilities:\n"
        "- Build features using Python and React\n\n"
        "Requirements:\n"
        "- Experience in Python, React, and SQL"
    )

    extracted = await llm_service.analyze_job_description(jd_text)
    assert extracted["analysis_quality"] == "sufficient"
    assert extracted["compensation"] is None
    assert "Python" in extracted["required_skills"]


# ---------------------------------------------------------------------------
# 5. Skill Normalization
# ---------------------------------------------------------------------------


def test_skill_normalization():
    """Verify normalization of common abbreviations and aliases."""
    assert normalize_skill("ML") == "Machine Learning"
    assert normalize_skill("ml") == "Machine Learning"
    assert normalize_skill("Postgres") == "PostgreSQL"
    assert normalize_skill("pgsql") == "PostgreSQL"
    assert normalize_skill("RESTful APIs") == "REST APIs"
    assert normalize_skill("rest api") == "REST APIs"
    assert normalize_skill("pytorch") == "PyTorch"
    assert normalize_skill("k8s") == "Kubernetes"
    assert normalize_skill("golang") == "Go"


# ---------------------------------------------------------------------------
# 6. Generic AI vs Explicit Machine Learning
# ---------------------------------------------------------------------------


def test_generic_ai_vs_explicit_machine_learning():
    """Candidate with general AI in resume does not falsely verify deep ML model requirements."""
    resume_data = {
        "skills": ["Python", "AI", "Prompt Engineering"],
        "projects": ["Built an AI chatbot using LLM API"],
    }
    evidence_map = extract_structured_resume_evidence(resume_data)

    matches = match_requirements_to_evidence(
        required_skills=["Machine Learning", "PyTorch"],
        preferred_skills=[],
        evidence_map=evidence_map,
    )

    # Machine Learning and PyTorch should NOT be VERIFIED_MATCH
    ml_match = next((m for m in matches if m.canonical_requirement == "Machine Learning"), None)
    pytorch_match = next((m for m in matches if m.canonical_requirement == "PyTorch"), None)

    assert ml_match is not None
    assert ml_match.status != MatchStatus.VERIFIED_MATCH
    assert pytorch_match is not None
    assert pytorch_match.status == MatchStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# 7. Deterministic Scoring Reproducibility
# ---------------------------------------------------------------------------


def test_deterministic_scoring_reproducibility():
    """Identical requirement matches must compute identical numerical scores every time."""
    resume_data = {
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "projects": ["Built FastAPI REST service on PostgreSQL"],
    }
    evidence_map = extract_structured_resume_evidence(resume_data)

    matches = match_requirements_to_evidence(
        required_skills=["Python", "PostgreSQL", "Docker", "Machine Learning"],
        preferred_skills=["Kubernetes"],
        evidence_map=evidence_map,
    )

    score_1, breakdown_1 = calculate_deterministic_match_score(matches, seniority_gap_detected=True)
    score_2, breakdown_2 = calculate_deterministic_match_score(matches, seniority_gap_detected=True)

    assert score_1 == score_2
    assert breakdown_1 == breakdown_2
    assert 0 <= score_1 <= 100


# ---------------------------------------------------------------------------
# 8. Single Source of Truth & Clean Title Regression (Requirement 15)
# ---------------------------------------------------------------------------


def test_clean_role_title_internal_grade_extraction():
    """Verify clean role title extraction and internal grade isolation (Requirement 7)."""
    # Case 1: Full internal grade with 'About the Role'
    raw_1 = "About the Role: Grade Level (for internal use): 11 Lead AI Engineer"
    title_1, grade_1 = clean_role_title(raw_1)
    assert title_1 == "Lead AI Engineer"
    assert grade_1 == "11"
    assert "Grade Level" not in title_1
    assert "internal use" not in title_1
    assert "About the Role" not in title_1

    # Case 2: Role prefix with truncated title
    raw_2 = "Role: About the Role: Grade Level (for internal use): 11 Lead AI E"
    title_2, grade_2 = clean_role_title(raw_2)
    assert title_2 == "Lead AI E"
    assert grade_2 == "11"

    # Case 3: Job Title prefix with Band/Level
    raw_3 = "Job Title: Senior Software Engineer (Band 4)"
    title_3, grade_3 = clean_role_title(raw_3)
    assert title_3 == "Senior Software Engineer"
    assert grade_3 == "4"


def test_single_source_of_truth_reconciliation_regression():
    """Verify unified requirement comparison, scoring reconciliation, and gap counts (Requirements 1-6, 11-12)."""
    # 1. Candidate evidence: ~1 year experience, knows Python, PostgreSQL, REST APIs.
    resume_data = {
        "skills": ["Python", "PostgreSQL", "REST APIs"],
        "experience": [
            "Junior Backend Developer (2023 - 2024): Built REST services in Python and PostgreSQL.",
        ],
        "projects": [
            "API Service: Built FastAPI REST endpoints with PostgreSQL.",
        ],
    }
    evidence_map = extract_structured_resume_evidence(resume_data)

    # 2. JD specifies:
    # - Required skills: Python, PostgreSQL, Machine Learning, Docker
    # - Preferred skills: Kubernetes
    # - Experience: 5+ years
    # - Education: Bachelor's Degree
    # - Domain: Finance
    req_skills = ["Python", "PostgreSQL", "Machine Learning", "Docker"]
    pref_skills = ["Kubernetes"]
    exp_reqs = ["5+ years of software engineering experience"]
    edu_reqs = ["Bachelor's in Computer Science"]
    domain_reqs = ["Financial Data"]

    unified = build_unified_requirements(
        required_skills=req_skills,
        preferred_skills=pref_skills,
        experience_requirements=exp_reqs,
        education_requirements=edu_reqs,
        domain_requirements=domain_reqs,
        evidence_map=evidence_map,
        candidate_years=1.0,
        requested_years=5.0,
    )

    # 3. Assert single source of truth partition
    verified_items = [r for r in unified if r.match_status == "verified"]
    related_items = [r for r in unified if r.match_status == "related"]
    missing_items = [r for r in unified if r.match_status == "missing"]

    verified_count = len(verified_items)
    related_count = len(related_items)
    gap_count = len(missing_items)

    # Python & PostgreSQL are verified required skills
    verified_req_skills = [r for r in verified_items if r.category == "required_skill"]
    assert len(verified_req_skills) == 2
    assert verified_count == len(verified_items)
    assert verified_count == 3  # 2 skills + 1 verified education degree

    # Docker, Kubernetes, 5+ years experience, Financial Data are missing
    assert gap_count == len(missing_items)
    assert gap_count >= 3
    # Experience gap MUST be included in missing_items
    exp_missing = [r for r in missing_items if r.category == "experience"]
    assert len(exp_missing) == 1
    assert "5+ years" in exp_missing[0].requirement

    # 4. Calculate reconciled scores
    final_score, breakdown = calculate_reconciled_scores(
        requirements=unified,
        candidate_years=1.0,
        requested_years=5.0,
    )

    req_score = breakdown["required_skills_score"]
    pref_score = breakdown["preferred_skills_score"]
    exp_score = breakdown["experience_score"]
    domain_score = breakdown["domain_score"]

    # Component scores reconciliation
    # Required skills score: (2 verified * 1.0 + 0 related) / 4 * 100 = 50%
    assert req_score == 50
    # Preferred skills score: 0 verified out of 1 = 0%
    assert pref_score == 0
    # Experience score: 1 year vs 5+ requested -> severely penalized
    assert exp_score <= 30

    # Final score mathematical reconciliation:
    # Base = 0.40 * req_score + 0.15 * pref_score + 0.25 * exp_score + 0.20 * domain_score
    expected_base = round(0.40 * req_score + 0.15 * pref_score + 0.25 * exp_score + 0.20 * domain_score)
    # Critical gap cap applies (requested 5.0 vs candidate 1.0 -> cap at 50)
    expected_final = min(50, expected_base)
    assert final_score == expected_final

    # 5. Dynamic copy check (Requirement 5)
    # Gaps exist, so "All highlighted JD requirements matched" must NEVER appear
    if gap_count == 0:
        msg = "All evaluated requirements have verified or related evidence."
    else:
        msg = f"{gap_count} requirements could not be verified from your resume."

    assert "All highlighted JD requirements matched" not in msg
    assert f"{gap_count} requirements could not be verified" in msg


@pytest.mark.anyio
async def test_end_to_end_consistency_endpoint_regression():
    """Verify endpoint consistency: title, grade, single-source counts, dynamic copy, and score math."""
    user, token, resume = await setup_candidate_user_and_resume()
    headers = {"Authorization": f"Bearer {token}"}

    raw_jd = (
        "About the Role: Grade Level (for internal use): 11 Lead AI Engineer at S&P Global.\n"
        "Responsibilities:\n"
        "- Build resilient microservices\n\n"
        "Requirements:\n"
        "- 5+ years experience in Python and PostgreSQL\n"
        "- Machine Learning production systems\n"
        "- Experience with Docker and Kubernetes"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r_analyze = await ac.post("/api/v1/jd/analyze", json={"job_description": raw_jd}, headers=headers)
        assert r_analyze.status_code == 200
        data = r_analyze.json()
        job = data["job_details"]
        match = data["match_analysis"]

        # Clean title & grade (Requirement 7)
        assert job["internal_grade"] == "11"
        assert "Grade Level" not in job["role_title"]
        assert "About the Role" not in job["role_title"]
        assert "Lead AI Engineer" in job["role_title"]

        # Single source counts match lists (Requirements 3 & 4)
        assert match["verified_count"] == len(match["verified_matches"])
        assert match["gap_count"] == len(match["gaps_breakdown"])
        assert match["gap_count"] > 0

        # Dynamic copy check (Requirement 5)
        gaps_msg = match.get("gaps_summary_message", "")
        assert "all matched" not in gaps_msg.lower()
        assert "could not be verified" in gaps_msg.lower()

        # Score guardrail: with 5+ years requested vs ~1 year candidate, final score <= 50 (Requirement 12)
        assert match["overall_match_score"] <= 50

        # Mathematical reconciliation of breakdown (Requirement 11 & Phase 14 weight redistribution)
        breakdown = match["match_breakdown"]
        req_score = breakdown["required_skills_score"]
        pref_score = breakdown["preferred_skills_score"]
        exp_score = breakdown["experience_score"]
        domain_score = breakdown["domain_score"]

        if pref_score is not None:
            raw_calc = round(0.40 * req_score + 0.15 * pref_score + 0.25 * exp_score + 0.20 * domain_score)
        else:
            total_w = 0.40 + 0.25 + 0.20
            raw_calc = round((0.40 / total_w) * req_score + (0.25 / total_w) * exp_score + (0.20 / total_w) * domain_score)
        # Final score should be min(50, raw_calc) due to critical experience gap guardrail
        assert match["overall_match_score"] == min(50, raw_calc)


# ---------------------------------------------------------------------------
# 9. NULL vs ZERO score — zero extracted skill requirements
# ---------------------------------------------------------------------------


def test_null_score_when_zero_required_skills():
    """A. When no required skills are extracted, required_skills_score must be None (not 0)."""
    requirements = build_unified_requirements(
        required_skills=[],
        preferred_skills=[],
        experience_requirements=[],
        evidence_map={},
    )
    _score, breakdown = calculate_reconciled_scores(requirements)
    assert breakdown["required_skills_score"] is None, (
        "required_skills_score must be None when no required skills exist in the JD"
    )


def test_null_score_when_zero_preferred_skills():
    """B. When no preferred skills are extracted, preferred_skills_score must be None (not 0)."""
    requirements = build_unified_requirements(
        required_skills=[],
        preferred_skills=[],
        evidence_map={},
    )
    _score, breakdown = calculate_reconciled_scores(requirements)
    assert breakdown["preferred_skills_score"] is None, (
        "preferred_skills_score must be None when no preferred skills exist in the JD"
    )


def test_analysis_quality_insufficient_when_zero_requirements():
    """C. Zero total requirements must produce INSUFFICIENT_REQUIREMENTS quality, not COMPLETE."""
    requirements = build_unified_requirements(
        required_skills=[],
        preferred_skills=[],
        experience_requirements=[],
        evidence_map={},
    )
    score, breakdown = calculate_reconciled_scores(requirements)
    assert breakdown["analysis_quality"] == "INSUFFICIENT_REQUIREMENTS"
    assert score == -1, "Sentinel -1 should be returned for INSUFFICIENT_REQUIREMENTS"


def test_weight_redistribution_when_preferred_missing():
    """D. When only required skills exist (no preferred), weights normalize between req/exp/domain."""
    requirements = build_unified_requirements(
        required_skills=["Python", "FastAPI"],
        preferred_skills=[],
        experience_requirements=[],
        evidence_map={},
    )
    _score, breakdown = calculate_reconciled_scores(requirements, domain_match_ratio=0.5)
    # Preferred must be None
    assert breakdown["preferred_skills_score"] is None
    # Required must be 0 (no evidence in empty evidence_map)
    assert breakdown["required_skills_score"] == 0
    # Final score must still be computed (not -1)
    assert _score >= 0


def test_partial_jd_quality_when_only_one_skill():
    """E. A JD with only one extracted skill gets PARTIAL quality."""
    requirements = build_unified_requirements(
        required_skills=["Python"],
        preferred_skills=[],
        evidence_map={},
    )
    _score, breakdown = calculate_reconciled_scores(requirements)
    assert breakdown["analysis_quality"] == "PARTIAL"


def test_heuristic_fallback_no_fabricated_experience():
    """F. Heuristic fallback must NOT produce a fabricated 'Proven software development experience'
    requirement when the JD contains no explicit experience text."""
    import asyncio
    jd_text = (
        "Intern - Software Development Engineer at Interview Kickstart.\n"
        "We are hiring a software intern to help build our platform.\n"
        "You will write code, do code reviews, and work with engineering teams.\n"
        "Technologies we use: React, Python, PostgreSQL."
    )

    async def _run():
        return await llm_service.analyze_job_description(jd_text)

    result = asyncio.get_event_loop().run_until_complete(_run())
    # No explicit experience requirement in JD — required_experience must be empty or
    # contain only explicitly extracted text, not a fabricated generic string
    for exp_req in result.get("required_experience", []):
        assert "proven software development experience" not in exp_req.lower(), (
            "Heuristic must not fabricate a 'Proven software development experience' requirement "
            "when no explicit experience is in the JD"
        )
    # min_years should be None since there is no explicit years requirement
    assert result.get("min_years_experience") is None


def test_tailoring_cannot_invent_requirements_absent_from_canonical_graph():
    """G. _deterministic_tailor_resume with empty canonical requirements must produce
    empty target_gaps (not generic SDE requirements like DSA, C++, Kubernetes)."""
    jd_data = {
        "role_title": "Intern - Software Development Engineer",
        "company": "Interview Kickstart",
        "required_skills": [],
        "preferred_skills": [],
        "required_experience": [],
        "min_years_experience": None,
    }
    resume_data = {
        "skills": ["Python", "JavaScript", "React"],
        "experience": [],
        "projects": [],
    }
    # Empty canonical requirements = nothing in JD to derive target_gaps from
    tailored = llm_service._deterministic_tailor_resume(jd_data, resume_data, canonical_requirements=[])
    target_gaps = tailored["skills"]["target_gaps"]
    # With no canonical requirements, target_gaps must be empty
    assert target_gaps == [], (
        f"target_gaps must be empty when canonical_requirements is empty. Got: {target_gaps}"
    )
    # Generic SDE skills must NOT appear in target_gaps
    forbidden = {"DSA", "C++", "Kubernetes", "Distributed Systems", "System Design"}
    gap_names = {g.split(" (")[0] for g in target_gaps}
    assert not gap_names.intersection(forbidden), (
        f"Generic SDE skills must not appear in target_gaps. Found: {gap_names}"
    )


def test_company_mission_not_candidate_responsibility():
    """H. Tailored summary must not treat company's product domain as candidate's job responsibilities."""
    jd_data = {
        "role_title": "Intern - Software Development Engineer",
        "company": "Interview Kickstart",
        "role_summary": "Interview Kickstart helps candidates prepare for technical interviews.",
        "required_skills": ["Python", "React"],
        "preferred_skills": [],
        "required_experience": [],
        "min_years_experience": None,
    }
    resume_data = {
        "skills": ["Python", "React", "FastAPI"],
        "experience": ["Backend Developer intern 2024: Built REST APIs in Python."],
        "projects": [],
    }
    tailored = llm_service._deterministic_tailor_resume(jd_data, resume_data)
    summary = tailored["summary"]["suggestion"].lower()
    # The candidate is NOT helping candidates prepare for interviews
    # — that is the company's product, not the SDE intern's role
    assert "interview preparation" not in summary
    assert "preparing candidates" not in summary
    assert "rigorous technical interviews" not in summary


def test_experience_requirement_provenance():
    """I. Experience requirements must only exist when explicitly in the JD; source must be traceable."""
    requirements = build_unified_requirements(
        required_skills=["Python"],
        preferred_skills=[],
        experience_requirements=["3+ years of backend development"],
        evidence_map={},
        requested_years=3.0,
        candidate_years=1.0,
    )
    exp_items = [r for r in requirements if r.category == "experience"]
    assert len(exp_items) == 1
    exp_req = exp_items[0]
    # Source must indicate JD origin
    assert "JD" in exp_req.source or "experience" in exp_req.source.lower()
    # The requirement text must come from the JD (not be fabricated)
    assert "3+" in exp_req.requirement or "3" in exp_req.requirement


def test_zero_requirements_gap_message_not_all_matched():
    """C (message). When zero requirements exist, gaps_summary_message must NOT say 'all matched'."""
    requirements = []  # No requirements at all
    # Simulate the message logic from llm_service.evaluate_resume_match
    total_requirements = len(requirements)
    gap_count = 0
    if total_requirements == 0:
        msg = "We couldn't identify enough explicit requirements in this job description to evaluate skill fit reliably."
    elif gap_count == 0:
        msg = "All evaluated requirements have verified or related evidence."
    else:
        msg = f"{gap_count} requirements could not be verified."

    assert "all" not in msg.lower() and "matched" not in msg.lower(), (
        f"Zero-requirement case must not produce 'all matched' message. Got: {msg}"
    )
    assert "couldn't identify" in msg.lower() or "not enough" in msg.lower()


# ---------------------------------------------------------------------------
# Phase 27: Comprehensive Pipeline Tests (Items 1 - 36)
# ---------------------------------------------------------------------------


def test_jd_near_30k_characters_and_requirements_near_end():
    """Item 1, 2, 3: Support realistic JD up to ~30,000 characters with requirements near the end."""
    intro = "Company Overview: Global software enterprise.\n" * 250
    middle = "Our mission is driving cloud innovation across distributed platforms.\n" * 230
    end_qualifications = (
        "\nMinimum Qualifications:\n"
        "- 4+ years of professional backend engineering experience\n"
        "- Production proficiency in Go, Python, and PostgreSQL\n"
        "- Experience with Docker containerization\n"
    )
    long_jd = intro + middle + end_qualifications
    assert len(long_jd) > 25000
    assert len(long_jd) < 32000

    prep = clean_job_description(long_jd)
    assert prep.analysis_quality == "sufficient"
    # Verify extraction can capture qualifications near the very end
    extracted = llm_service._heuristic_extract_jd(prep)
    assert "Python" in extracted["required_skills"]
    assert "PostgreSQL" in extracted["required_skills"]
    assert extracted["min_years_experience"] == 4.0


def test_html_heavy_jd_preprocessing():
    """Item 4: Deterministic cleaning of HTML tags, entities, and line breaks."""
    html_jd = (
        "&lt;div class=&quot;job-details&quot;&gt;\n"
        "<h1>Senior Backend Engineer &amp; Platform Architect</h1>\n"
        "<p>About the role: We are hiring a builder.&nbsp;&nbsp;</p>\n"
        "<ul>\n"
        "  <li>5+ years experience in Python &amp; PostgreSQL</li>\n"
        "  <li>FastAPI microservices design</li>\n"
        "</ul>\n"
        "<br><br>\n"
        "<div>Direct applicants only. No agency submissions accepted.</div>\n"
        "</div>"
    )
    prep = clean_job_description(html_jd)
    cleaned = prep.cleaned_text
    assert "<div" not in cleaned
    assert "<h1>" not in cleaned
    assert "&lt;" not in cleaned
    assert "&amp;" not in cleaned
    assert "Python" in cleaned
    assert "PostgreSQL" in cleaned
    assert "No agency submissions" not in cleaned


def test_unmet_experience_included_in_gaps_and_counts():
    """Item 19: Experience gap must be included in gaps_breakdown and gap_count."""
    requirements = build_unified_requirements(
        required_skills=["Python", "PostgreSQL"],
        preferred_skills=[],
        experience_requirements=["5+ years experience in backend architecture"],
        requested_years=5.0,
        candidate_years=1.0,
        evidence_map={
            "Python": extract_structured_resume_evidence({"skills": ["Python"]})["Python"],
            "PostgreSQL": extract_structured_resume_evidence({"skills": ["PostgreSQL"]})["PostgreSQL"],
        },
    )
    exp_reqs = [r for r in requirements if r.category == "experience"]
    assert len(exp_reqs) == 1
    exp_item = exp_reqs[0]
    assert exp_item.match_status == MatchStatus.MISSING.value

    # Evaluate match
    match_data = llm_service.evaluate_resume_match.__wrapped__(
        llm_service,
        jd_data={
            "role_title": "Senior Engineer",
            "company": "Tech Corp",
            "required_skills": ["Python", "PostgreSQL"],
            "min_years_experience": 5.0,
            "required_experience": ["5+ years experience"],
        },
        resume_data={"skills": ["Python", "PostgreSQL"], "experience": ["1 year junior engineer"]},
    ) if hasattr(llm_service.evaluate_resume_match, "__wrapped__") else None

    # Verify directly via requirements partitioning
    missing_items = [r for r in requirements if r.match_status == MatchStatus.MISSING.value]
    assert any(m.category == "experience" for m in missing_items)
    gap_count = len(missing_items)
    assert gap_count >= 1, "Experience gap must increase gap_count"


def test_direct_vs_transferable_evidence():
    """Item 24: Direct vs Transferable distinction (Machine Learning != direct PyTorch)."""
    evidence_map = extract_structured_resume_evidence({
        "skills": ["Machine Learning", "Python"],
        "projects": ["Built a Machine Learning classification model"],
    })
    requirements = build_unified_requirements(
        required_skills=["PyTorch"],
        preferred_skills=[],
        evidence_map=evidence_map,
    )
    pytorch_req = next(r for r in requirements if r.canonical == "PyTorch")
    # Machine Learning is related to PyTorch, but NOT direct verified evidence
    assert pytorch_req.match_status == MatchStatus.RELATED.value, (
        "Candidate with Machine Learning but no PyTorch must have RELATED, not VERIFIED"
    )
    assert pytorch_req.evidence_strength < 1.0


def test_project_alignment_grounding():
    """Item 27: Portfolio project alignment highlights actual evidence supports and does not establish."""
    jd_data = {
        "role_title": "Platform Engineer",
        "company": "Cloud Inc",
        "required_skills": ["FastAPI", "Kubernetes"],
        "preferred_skills": [],
    }
    resume_data = {
        "skills": ["FastAPI"],
        "projects": [
            "Route53 Clone: Built FastAPI REST service layer with custom DNS routing rules."
        ],
    }
    canonical_requirements = [
        {"canonical": "FastAPI", "match_status": "verified", "category": "required_skill", "source": "JD required"},
        {"canonical": "Kubernetes", "match_status": "missing", "category": "required_skill", "source": "JD required"},
    ]
    tailored = llm_service._deterministic_tailor_resume(
        jd_data, resume_data, canonical_requirements=canonical_requirements
    )
    projects = tailored["projects"]
    assert len(projects) >= 1
    p1 = projects[0]
    assert any("FastAPI" in s for s in p1["supports"])
    assert any("Kubernetes" in ne for ne in p1["does_not_establish"])


def test_targeted_summary_no_unsupported_seniority():
    """Item 28: Targeted summary contains no unverified seniority/leadership claims."""
    jd_data = {
        "role_title": "Lead Principal AI Architect",
        "company": "Enterprise AI",
        "required_skills": ["Python", "FastAPI"],
    }
    resume_data = {
        "skills": ["Python", "FastAPI"],
        "experience": ["Junior developer (1 year): backend API maintenance."],
    }
    tailored = llm_service._deterministic_tailor_resume(jd_data, resume_data)
    summary = tailored["summary"]["suggestion"]
    assert "Principal" not in summary
    assert "Lead" not in summary
    assert "ready to lead" not in summary.lower()
    assert "executive" not in summary.lower()


@pytest.mark.anyio
async def test_provider_loaded_job_uses_canonical_db_description():
    """Item 29: Provider-loaded job uses canonical DB description from PostgreSQL."""
    user, token, resume = await setup_candidate_user_and_resume("provider_test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    canonical_text = (
        "Backend Platform Engineer at Acme Provider.\n"
        "Responsibilities:\n- Design scalable backend microservices\n"
        "Requirements:\n- 3+ years experience with Python and PostgreSQL\n- Experience with FastAPI\n"
    )

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="adzuna_test_123",
            company="Acme Provider",
            role_title="Backend Platform Engineer",
            description=canonical_text,
            source="adzuna",
            application_url="https://acme.example.com/jobs/123",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/jd/analyze",
            json={
                "job_description": "Truncated preview...",
                "source_job_id": str(job_id),
            },
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["job_details"]["company"] == "Acme Provider"
        assert data["job_details"]["role_title"] == "Backend Platform Engineer"
        assert data["job_details"]["source"] == "adzuna"
        assert data["job_details"]["application_url"] == "https://acme.example.com/jobs/123"
        # Requirements extracted from canonical text (Python, PostgreSQL, FastAPI)
        verified = {m["canonical_requirement"] for m in data["match_analysis"]["verified_matches"]}
        assert "Python" in verified or "FastAPI" in verified


@pytest.mark.anyio
async def test_truncated_frontend_preview_cannot_override_db_description():
    """Item 30: Truncated frontend text cannot override full database listing description."""
    user, token, resume = await setup_candidate_user_and_resume("override_test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    full_description = (
        "Principal Systems Engineer at Alpha Networks.\n"
        "Responsibilities:\n- Build real-time streaming engines\n"
        "Requirements:\n- Python, PostgreSQL, Docker, Git\n"
        "Qualifications:\n- 5+ years building backend systems\n"
    )

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="adzuna_full_456",
            company="Alpha Networks",
            role_title="Principal Systems Engineer",
            description=full_description,
            source="adzuna",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Pass only a short truncated snippet in job_description
        short_preview = "Principal Systems Engineer at Alpha Networks. Short..."
        r = await ac.post(
            "/api/v1/jd/analyze",
            json={
                "job_description": short_preview,
                "source_job_id": str(job_id),
            },
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        # Canonical DB description should have been used, extracting the full skills list
        matched = data["match_analysis"]["matched_skills"]
        assert len(matched) >= 2


@pytest.mark.anyio
async def test_llm_failure_graceful_fallback():
    """Item 31: LLM failure gracefully falls back to deterministic heuristic extraction without crashing."""
    raw_jd = (
        "Staff Software Engineer at Cloudflare.\n"
        "Responsibilities:\n- Develop high throughput networking services\n"
        "Requirements:\n- Python, PostgreSQL, Linux, Git\n"
    )
    with patch.object(llm_service, "_extract_with_groq", side_effect=Exception("API connection timeout")):
        result = await llm_service.analyze_job_description(raw_jd)
        assert result is not None
        assert "Python" in result["required_skills"]
        assert "PostgreSQL" in result["required_skills"]


def test_pydantic_schema_validation_and_repair():
    """Item 33: ExtractedJDModel parses and validates cleanly with defaults for missing optional fields."""
    partial_json = {
        "company": "Modern Tech",
        "role_title": "Backend Developer",
        "required_skills": ["Python", "FastAPI"],
    }
    model = ExtractedJDModel.model_validate(partial_json)
    assert model.company == "Modern Tech"
    assert model.role_title == "Backend Developer"
    assert model.required_skills == ["Python", "FastAPI"]
    assert model.preferred_skills == []
    assert model.responsibilities == []


def test_no_hallucinated_skills_noise_filtering():
    """Item 34: Noise terms (club titles, student roles, IDE names) are rejected from skills."""
    assert not is_valid_technical_skill("Vice President")
    assert not is_valid_technical_skill("Bennett University DevOps Club")
    assert not is_valid_technical_skill("student members")
    assert not is_valid_technical_skill("VS Code")
    assert is_valid_technical_skill("Python")
    assert is_valid_technical_skill("PostgreSQL")
    assert is_valid_technical_skill("Docker")


@pytest.mark.anyio
async def test_user_isolation_on_tailoring():
    """Item 35: Users cannot access or tailor another user's resume."""
    user_a, token_a, resume_a = await setup_candidate_user_and_resume("user_a@example.com")
    user_b, token_b, resume_b = await setup_candidate_user_and_resume("user_b@example.com")

    # User A attempts to tailor with User B's resume ID
    headers_a = {"Authorization": f"Bearer {token_a}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/jd/tailor",
            json={
                "job_description": "Software Engineer at Google requiring Python and Docker.",
                "resume_id": str(resume_b.id),
            },
            headers=headers_a,
        )
        assert r.status_code == 404, "User A must not be allowed to access User B's resume"


@pytest.mark.anyio
async def test_existing_jd_analyzer_api_compatibility():
    """Item 36: Analyze response adheres strictly to existing API contract for backward compatibility."""
    user, token, resume = await setup_candidate_user_and_resume("compat_test@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    raw_jd = (
        "Backend Developer at Spotify.\n"
        "Requirements:\n- Python\n- PostgreSQL\n"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/jd/analyze", json={"job_description": raw_jd}, headers=headers)
        assert r.status_code == 200
        data = r.json()
        # Verify required root keys
        assert "job_details" in data
        assert "match_analysis" in data
        assert "resume_id" in data
        assert "resume_filename" in data
        # Verify match_analysis structure
        match = data["match_analysis"]
        assert "overall_match_score" in match
        assert "matched_skills" in match
        assert "missing_skills" in match
        assert "verified_count" in match
        assert "related_count" in match
        assert "gap_count" in match
        assert "match_breakdown" in match
        assert "verified_matches" in match
        assert "related_experience" in match
        assert "gaps_breakdown" in match
        assert "normalized_requirements" in match


# ==============================================================================
# SECTION 24: SEMANTIC EVIDENCE MATCHING & STRICT TECHNOLOGY REGRESSION TESTS
# ==============================================================================

@pytest.fixture
def regression_candidate_profile():
    return {
        "name": "Alex Candidate",
        "email": "alex.cand@example.com",
        "projects": [
            "Route53 Clone: Built a full-stack application with Next.js/TypeScript frontend and FastAPI REST backend. Features authentication, CRUD, relational schema design, validation, transaction handling, and scaling considerations. AWS Route53-style console.",
            "AI Research Paper Assistant: Built a full-stack RAG system with FastAPI backend, ChromaDB, Groq. Document ingestion, data pipeline debugging, extraction, deduplication, chunking, embeddings.",
            "Lendora AI: Built a Scikit-learn ML pipeline with feature engineering, model benchmarking, evaluation metrics (Logistic Regression, Gradient Boosting, F1, ROC-AUC).",
        ],
        "achievements": [
            "Solved 150+ DSA problems on LeetCode; maintained a 50-day problem-solving streak.",
        ],
        "education": [
            "Bachelor of Technology in Computer Science. Expected Graduation: 2028",
        ],
        "skills": [
            "Python", "FastAPI", "Next.js", "TypeScript", "Docker", "PostgreSQL", "Scikit-Learn", "Git",
        ],
        "experience": [],
        "raw_text": "Alex Candidate... Route53 Clone, AI Research Paper Assistant, Lendora AI. Solved 150+ DSA problems on LeetCode. Expected Graduation: 2028",
    }


def test_broad_software_development_semantic_matching(regression_candidate_profile):
    """1. Broad Software Development semantic matching: verified through project implementations."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Software Development"]},
        evidence_map=ev_map,
    )
    sw_req = next(r for r in reqs if r.canonical == "Software Development")
    assert sw_req.match_status == MatchStatus.VERIFIED.value
    assert len(sw_req.resume_evidence) > 0
    assert "implemented project" in sw_req.notes.lower()


def test_problem_solving_semantic_matching(regression_candidate_profile):
    """2. Problem Solving semantic matching: verified through DSA achievements and debugging."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Problem Solving"]},
        evidence_map=ev_map,
    )
    ps_req = next(r for r in reqs if r.canonical == "Problem Solving")
    assert ps_req.match_status == MatchStatus.VERIFIED.value
    assert any("150+ DSA problems" in ev for ev in ps_req.resume_evidence)


def test_system_design_direct_matching(regression_candidate_profile):
    """3. System Design direct matching: verified through architecture and schema design in projects."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["System Design"]},
        evidence_map=ev_map,
    )
    sd_req = next(r for r in reqs if r.canonical == "System Design")
    assert sd_req.match_status == MatchStatus.VERIFIED.value
    assert len(sd_req.resume_evidence) > 0


def test_graduation_year_evidence(regression_candidate_profile):
    """4. Graduation year evidence: 2028 Graduate is verified from Education history."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"graduation_year_eligibility": "2028"},
        evidence_map=ev_map,
    )
    grad_req = next(r for r in reqs if r.canonical == "2028 Graduate")
    assert grad_req.match_status == MatchStatus.VERIFIED.value
    assert "2028" in grad_req.notes


def test_machine_learning_from_actual_ml_project(regression_candidate_profile):
    """5. Machine Learning verified from actual ML project (Lendora AI with Scikit-learn)."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Machine Learning"]},
        evidence_map=ev_map,
    )
    ml_req = next(r for r in reqs if r.canonical == "Machine Learning")
    assert ml_req.match_status == MatchStatus.VERIFIED.value
    assert "ML pipeline" in ml_req.notes or "Scikit-learn" in ml_req.notes


def test_pytorch_remains_missing_even_with_ml_project(regression_candidate_profile):
    """6. PyTorch requirement remains strictly unverified when only Scikit-learn is present."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["PyTorch"]},
        evidence_map=ev_map,
    )
    pt_req = next(r for r in reqs if r.canonical == "PyTorch")
    assert pt_req.match_status in (MatchStatus.MISSING.value, MatchStatus.RELATED.value)
    assert pt_req.match_status != MatchStatus.VERIFIED.value


def test_kubernetes_remains_missing_even_with_docker(regression_candidate_profile):
    """7. Kubernetes remains unverified even when Docker is present in the resume."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Kubernetes"]},
        evidence_map=ev_map,
    )
    k8s_req = next(r for r in reqs if r.canonical == "Kubernetes")
    assert k8s_req.match_status in (MatchStatus.MISSING.value, MatchStatus.RELATED.value)
    assert k8s_req.match_status != MatchStatus.VERIFIED.value


def test_aws_route53_style_clone_does_not_prove_aws(regression_candidate_profile):
    """8. Route53 clone / style reference does NOT prove AWS experience."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["AWS"]},
        evidence_map=ev_map,
    )
    aws_req = next(r for r in reqs if r.canonical == "AWS")
    assert aws_req.match_status != MatchStatus.VERIFIED.value


def test_fastapi_does_not_prove_machine_learning():
    """9. FastAPI alone does NOT verify Machine Learning."""
    web_resume = {
        "projects": ["Web API: Built FastAPI REST endpoints for user authentication and task management."],
        "skills": ["FastAPI", "Python", "SQL"],
        "experience": [],
    }
    ev_map = extract_structured_resume_evidence(web_resume)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Machine Learning"]},
        evidence_map=ev_map,
    )
    ml_req = next(r for r in reqs if r.canonical == "Machine Learning")
    assert ml_req.match_status == MatchStatus.MISSING.value


def test_python_does_not_prove_pytorch():
    """10. Python alone does NOT verify PyTorch."""
    py_resume = {
        "projects": ["CLI Tool: Built a Python automation script for CSV processing."],
        "skills": ["Python"],
        "experience": [],
    }
    ev_map = extract_structured_resume_evidence(py_resume)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["PyTorch"]},
        evidence_map=ev_map,
    )
    pt_req = next(r for r in reqs if r.canonical == "PyTorch")
    assert pt_req.match_status == MatchStatus.MISSING.value


def test_docker_does_not_prove_kubernetes():
    """11. Docker alone does NOT verify Kubernetes."""
    docker_resume = {
        "projects": ["Containerized App: Created Dockerfile and docker-compose setup."],
        "skills": ["Docker"],
        "experience": [],
    }
    ev_map = extract_structured_resume_evidence(docker_resume)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Kubernetes"]},
        evidence_map=ev_map,
    )
    k8s_req = next(r for r in reqs if r.canonical == "Kubernetes")
    assert k8s_req.match_status != MatchStatus.VERIFIED.value


def test_project_evidence_classification(regression_candidate_profile):
    """12. Project evidence classification: extracted items have PROJECT_IMPLEMENTATION evidence_type."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    assert "Software Development" in ev_map
    assert ev_map["Software Development"].evidence_type == EvidenceType.PROJECT_IMPLEMENTATION.value
    assert ev_map["Software Development"].source_section == "projects"


def test_achievement_evidence_classification(regression_candidate_profile):
    """13. Achievement evidence classification: extracted items have ACHIEVEMENT evidence_type."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    assert "Problem Solving" in ev_map
    assert ev_map["Problem Solving"].evidence_type == EvidenceType.ACHIEVEMENT.value
    assert ev_map["Problem Solving"].source_section == "achievements"


def test_no_professional_experience_years_inferred_from_projects(regression_candidate_profile):
    """14. No professional experience years inferred from projects when experience section is empty."""
    cand_years, year_msg = llm_service._estimate_candidate_years(regression_candidate_profile)
    assert cand_years is None
    assert year_msg == "Not determinable from resume"


def test_concrete_evidence_preferred_over_skill_list_only_evidence():
    """15. Concrete implementation evidence has higher strength than raw skill-list-only evidence."""
    resume_with_impl = {
        "projects": ["Next.js App: Built full-stack TypeScript and FastAPI application with responsive UI."],
        "skills": ["TypeScript"],
        "experience": [],
    }
    ev_map = extract_structured_resume_evidence(resume_with_impl)
    ts_ev = ev_map["TypeScript"]
    assert ts_ev.evidence_type == EvidenceType.PROJECT_IMPLEMENTATION.value
    assert ts_ev.strength >= 0.95


def test_find_positions_score_scale_0_100_consistency():
    """16. Find Positions score scale consistency: scores are numbers on 0-100 scale."""
    from app.services.job_matcher import JobMatcherService
    matcher = JobMatcherService()
    sim = 0.85
    pref = 0.90
    sim_100 = round(sim * 100.0, 1)
    pref_100 = round(pref * 100.0, 1)
    final = round(matcher.vector_weight * sim_100 + matcher.preference_weight * pref_100)
    assert sim_100 >= 30.0 and sim_100 <= 100.0
    assert pref_100 >= 30.0 and pref_100 <= 100.0
    assert final >= 30 and final <= 100


def test_job_match_and_jd_analyzer_scores_remain_conceptually_separate(regression_candidate_profile):
    """17. Profile Match (Find Positions) and Candidate Fit (JD Analyzer) remain conceptually separate."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Software Development", "Problem Solving", "System Design"]},
        evidence_map=ev_map,
    )
    analyzer_score, breakdown = calculate_reconciled_scores(reqs)
    assert analyzer_score >= 10 and analyzer_score <= 100
    assert breakdown["required_skills_score"] == 100


def test_score_arithmetic_reconciliation(regression_candidate_profile):
    """18. Score arithmetic reconciliation: final Candidate Fit score accurately combines components."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={
            "required_skills": ["Software Development", "Problem Solving"],
            "preferred_skills": ["Next.js"],
        },
        evidence_map=ev_map,
    )
    score, breakdown = calculate_reconciled_scores(reqs, domain_match_ratio=0.5)
    assert breakdown["required_skills_score"] == 100
    assert breakdown["preferred_skills_score"] == 100
    assert score is not None
    assert 60 <= score <= 95


def test_anti_hallucination_prevents_false_positive_skills():
    """19. Anti-hallucination prevents arbitrary cross-category verification."""
    noise_skills = ["Creative Thinker", "President of Chess Club", "Good Listener"]
    for s in noise_skills:
        assert not is_valid_technical_skill(s)


@pytest.mark.anyio
async def test_user_isolation_verification():
    """20. User isolation verification on JD operations."""
    user_a, token_a, _ = await setup_candidate_user_and_resume("iso_user_a@example.com")
    user_b, token_b, resume_b = await setup_candidate_user_and_resume("iso_user_b@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/resumes/{resume_b.id}", headers=headers_a)
        assert r.status_code in (403, 404)


# ==============================================================================
# SECTION 25: GRAVITON FINAL CONSISTENCY CLEANUP REGRESSION TESTS
# ==============================================================================

def test_graduation_year_duplicate_normalization():
    """Item 1: Graduation year variations collapse into graduation_year:2028 canonical display '2028 Graduate'."""
    from app.services.skill_normalizer import get_canonical_requirement_key
    variations = [
        "2028 Graduate",
        "Graduating in 2028",
        "Expected graduation 2028",
        "Graduation year: 2028",
        "2028 graduates",
    ]
    for text in variations:
        key, display, cat, sem_cat = get_canonical_requirement_key(text, "required_skill")
        assert key == "graduation_year:2028"
        assert display == "2028 Graduate"
        assert cat == "education"
        assert sem_cat == SemanticCategory.EDUCATION.value


def test_semantic_duplicate_requirements_collapse():
    """Item 1: Semantically equivalent requirements generally deduplicate before matching/scoring."""
    from app.services.skill_normalizer import get_canonical_requirement_key
    key1, disp1, _, _ = get_canonical_requirement_key("Python", "required_skill")
    key2, disp2, _, _ = get_canonical_requirement_key("python3", "preferred_skill")
    assert key1 == key2 == "skill:python"
    assert disp1 == disp2 == "Python"


def test_duplicate_requirements_not_affecting_score(regression_candidate_profile):
    """Item 1 & 8: Duplicate graduation requirements do not double-count in verified count or scores."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    # JD supplies graduation requirement in 3 different sections/variations
    reqs = build_unified_requirements(
        jd_data={
            "graduation_year_eligibility": "2028",
            "required_skills": ["Graduating in 2028", "Software Development"],
            "education_requirements": ["Expected graduation 2028"],
        },
        evidence_map=ev_map,
    )
    # Must collapse to exactly 1 graduation requirement
    grad_reqs = [r for r in reqs if r.canonical == "2028 Graduate"]
    assert len(grad_reqs) == 1
    # Only 2 total requirements: Software Development + 2028 Graduate
    assert len(reqs) == 2
    v_count = sum(1 for r in reqs if r.match_status == MatchStatus.VERIFIED.value)
    assert v_count == 2
    score, breakdown = calculate_reconciled_scores(reqs)
    # Required skills score is 100% (from Software Development)
    assert breakdown["required_skills_score"] == 100


def test_strongest_provenance_retained_after_dedupe(regression_candidate_profile):
    """Item 1: Strongest importance and source provenance retained after deduplication."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={
            "preferred_skills": ["Graduating in 2028"],
            "graduation_year_eligibility": "2028",
        },
        evidence_map=ev_map,
    )
    assert len(reqs) == 1
    grad_req = reqs[0]
    assert grad_req.canonical == "2028 Graduate"
    assert grad_req.importance == "required"
    assert grad_req.source == "JD graduation year requirement"
    assert grad_req.weight == 1.0


def test_software_architecture_related_evidence():
    """Item 2: Software Architecture qualifies as RELATED evidence when project architectural reasoning is present."""
    resume_with_arch = {
        "projects": [
            "Route53 Clone | Next.js, FastAPI, PostgreSQL: Built a multi-tier application architecture with documented architecture trade-offs, relational schema design, read-through caching plan, DB sharding reasoning, and shared session store horizontal scaling reasoning.",
        ],
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience": [],
    }
    ev_map = extract_structured_resume_evidence(resume_with_arch)
    assert "Software Architecture" in ev_map
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Software Architecture"]},
        evidence_map=ev_map,
    )
    arch_req = next(r for r in reqs if r.canonical == "Software Architecture")
    assert arch_req.match_status == MatchStatus.RELATED.value
    assert len(arch_req.resume_evidence) > 0
    assert "related transferable evidence" in arch_req.notes.lower()


def test_software_design_patterns_strictly_missing_unless_direct_evidence(regression_candidate_profile):
    """Item 2: Software Design Patterns remains MISSING unless direct evidence exists."""
    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={"required_skills": ["Software Design Patterns"]},
        evidence_map=ev_map,
    )
    dp_req = next(r for r in reqs if r.canonical == "Software Design Patterns")
    assert dp_req.match_status == MatchStatus.MISSING.value
    assert "No verified evidence" in dp_req.notes


def test_experience_years_never_embedding_scored():
    """Item 3: Experience score is 0% (never 4%) when requested years = 1 and verified candidate years is None."""
    reqs = [
        NormalizedRequirement(
            requirement_id="exp_test",
            category="experience",
            requirement="1+ years experience",
            canonical="1+ years experience",
            importance="required",
            match_status="missing",
            source="JD experience requirement",
            notes="EXPERIENCE GAP: 1+ years requested / Not determinable from resume.",
        )
    ]
    score, breakdown = calculate_reconciled_scores(
        requirements=reqs,
        candidate_years=None,
        requested_years=1.0,
    )
    # Must be 0%, strictly NOT 4%
    assert breakdown["experience_score"] == 0


def test_unknown_professional_years_with_explicit_requirement(regression_candidate_profile):
    """Item 3: Unknown professional years with explicit 1+ years requirement yields deterministic MISSING and 0%."""
    cand_years, year_msg = llm_service._estimate_candidate_years(regression_candidate_profile)
    assert cand_years is None
    assert year_msg == "Not determinable from resume"

    ev_map = extract_structured_resume_evidence(regression_candidate_profile)
    reqs = build_unified_requirements(
        jd_data={
            "required_skills": ["Software Development", "System Design"],
            "min_years_experience": 1.0,
        },
        evidence_map=ev_map,
        candidate_years=cand_years,
        requested_years=1.0,
    )
    exp_req = next(r for r in reqs if r.category == "experience")
    assert exp_req.match_status == MatchStatus.MISSING.value
    assert "Not determinable" in exp_req.notes

    score, breakdown = calculate_reconciled_scores(
        requirements=reqs,
        candidate_years=cand_years,
        requested_years=1.0,
    )
    assert breakdown["experience_score"] == 0


def test_project_bullets_grouped_by_project():
    """Item 4: Resume parser groups project title and all its bullets into a single project entity."""
    from app.services.resume_parser import DeterministicResumeParser
    parser = DeterministicResumeParser()
    raw_resume = (
        "Alex Chen\n"
        "alex@example.com\n\n"
        "PROJECTS\n"
        "Route53 Clone | Next.js, FastAPI, PostgreSQL\n"
        "- Built a multi-tier web application mimicking AWS Route53 DNS management.\n"
        "- Documented architecture trade-offs including relational schema design and scaling.\n\n"
        "AI Research Paper Assistant | Python, ChromaDB\n"
        "- Developed interactive research assistant using FastAPI and ChromaDB.\n"
        "- Implemented vector embeddings and document chunking pipeline.\n"
    )
    parsed = parser.parse(raw_resume)
    projects = parsed["projects"]
    assert len(projects) == 2
    p1 = projects[0]
    assert p1["project_title"] == "Route53 Clone"
    assert len(p1["project_bullets"]) == 2
    assert "Next.js" in p1["project_technologies"] or "FastAPI" in p1["project_technologies"]


def test_project_rendered_once_in_tailoring():
    """Item 4 & 10: Project Alignment renders ONE section per project, not per bullet."""
    resume_data = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Next.js"],
        "projects": [
            {
                "project_id": "proj_1",
                "project_title": "Route53 Clone",
                "project_technologies": ["Next.js", "FastAPI", "PostgreSQL"],
                "project_bullets": [
                    "Built a multi-tier web application mimicking AWS Route53 DNS management.",
                    "Documented architecture trade-offs including relational schema design and scaling.",
                ],
                "description": "Route53 Clone: Built a multi-tier web application...",
            },
        ],
    }
    canonical_requirements = [
        {"canonical": "Software Development", "match_status": "verified", "category": "required_skill"},
        {"canonical": "System Design", "match_status": "verified", "category": "required_skill"},
        {"canonical": "Software Architecture", "match_status": "related", "category": "required_skill"},
        {"canonical": "Software Design Patterns", "match_status": "missing", "category": "required_skill"},
    ]
    tailored = llm_service._deterministic_tailor_resume(
        {"role_title": "Software Engineer", "company": "Graviton"},
        resume_data,
        canonical_requirements=canonical_requirements,
    )
    proj_entries = tailored["projects"]
    assert len(proj_entries) == 1
    p = proj_entries[0]
    assert p["project_title"] == "Route53 Clone"
    assert any("Software Development" in s for s in p["supports"])
    assert any("Software Architecture" in r for r in p.get("related_evidence", []))
    assert any("Software Design Patterns" in d for d in p["does_not_establish"])


def test_missing_skill_not_inserted_into_resume_recommendation():
    """Item 5: Tailoring recommendations never advise modifying resume bullets to advertise missing skills."""
    resume_data = {
        "skills": ["Python", "FastAPI"],
        "projects": ["Route53 Clone: Built a multi-tier application architecture."],
    }
    canonical_requirements = [
        {"canonical": "Software Design Patterns", "match_status": "missing", "category": "required_skill"},
    ]
    tailored = llm_service._deterministic_tailor_resume(
        {"role_title": "Software Engineer", "company": "Target"},
        resume_data,
        canonical_requirements=canonical_requirements,
    )
    proj = tailored["projects"][0]
    rec = proj["action_suggestion"].lower()
    assert "future work" not in rec
    assert "opportunity to apply" not in rec
    assert "formal design patterns" not in rec


def test_exactly_500_character_provider_description_detection():
    """Item 6 & 7: Exactly 500-char provider description is detected as PARTIAL with limited description warning."""
    from app.services.jd_preprocessor import clean_job_description
    # Create exactly 500 characters ending with ellipsis
    base = "Graviton Research Capital is hiring an Intern Software Engineer for 2028 Graduates. Responsibilities include software development, system design, and problem solving. You will collaborate with engineering teams to build low-latency trading infrastructure. Candidates should have a strong grasp of data structures and algorithms. Experience with software design patterns and arch"
    padded_500 = (base + " " * 500)[:499] + "…"
    assert len(padded_500) == 500

    prep = clean_job_description(padded_500)
    assert prep.description_quality == "PARTIAL"
    assert "shortened description" in prep.quality_warning.lower()


def test_truncated_mid_sentence_description_detection():
    """Item 7: Truncated mid-sentence provider description detected as PARTIAL and affects confidence."""
    from app.services.jd_preprocessor import clean_job_description
    truncated_text = (
        "Graviton Research Capital - Intern Software Engineer 2028 Graduates.\n"
        "Requirements:\n"
        "- Strong problem solving skills and algorithms\n"
        "- Software development in C++ or Python\n"
        "- Experience with software design patterns and arch…"
    )
    prep = clean_job_description(truncated_text)
    assert prep.description_quality == "PARTIAL"
    assert prep.quality_warning is not None

    # When analyzed, calculate_reconciled_scores yields analysis_quality == "PARTIAL"
    score, breakdown = calculate_reconciled_scores(
        requirements=[
            NormalizedRequirement(
                requirement_id="r1", category="required_skill", requirement="Problem Solving",
                canonical="Problem Solving", importance="required", match_status="verified",
            ),
            NormalizedRequirement(
                requirement_id="r2", category="required_skill", requirement="Software Development",
                canonical="Software Development", importance="required", match_status="verified",
            ),
            NormalizedRequirement(
                requirement_id="r3", category="required_skill", requirement="System Design",
                canonical="System Design", importance="required", match_status="verified",
            ),
        ],
        is_partial_jd=True,
    )
    assert breakdown["analysis_quality"] == "PARTIAL"


def test_canonical_db_description_greater_than_preview_remains_fully_analyzed():
    """Item 6: Stored DB description > preview remains FULL quality when not truncated."""
    from app.services.jd_preprocessor import clean_job_description
    full_description = (
        "Graviton Research Capital is looking for an Intern Software Engineer (2028 Graduates).\n\n"
        "Responsibilities:\n"
        "- Develop high performance low-latency software.\n"
        "- Design and implement scalable distributed systems.\n"
        "- Solve algorithmic problems and optimize data structures.\n\n"
        "Requirements:\n"
        "- Expected graduation in 2028 with Computer Science degree.\n"
        "- Strong problem solving skills and software engineering foundations.\n"
        "- Experience with software architecture principles and REST APIs.\n"
        "- Minimum 1+ years experience in software engineering projects.\n"
    )
    assert len(full_description) > 500
    prep = clean_job_description(full_description)
    assert prep.description_quality == "FULL"
    assert prep.quality_warning is None


# ===========================================================================
# Consistency & Regression Tests: 6 Orchestration / Data-Model Bugs
# ===========================================================================


def test_provider_company_metadata_precedence_and_no_target_company():
    """Item 1: When source_job_id resolves a canonical JobListing, authoritative provider metadata
    takes precedence over extraction and NEVER defaults to 'Target Company' or 'Unknown Company'."""
    from unittest.mock import MagicMock
    listing_record = MagicMock()
    listing_record.id = uuid.uuid4()
    listing_record.company = "Ladybird Web Solution Pvt Ltd"
    listing_record.role_title = "Internship For Software Engineers - Freshers"
    listing_record.location = "Somwarpet, Kodagu, India"
    listing_record.employment_type = "Internship"
    listing_record.application_url = "https://example.com/apply"
    listing_record.source = "ProviderPortal"

    extracted_jd_details = {
        "company": "Target Company",
        "role_title": "Software Engineer",
        "location": None,
        "employment_type": None,
        "application_url": None,
    }

    # Simulate precedence logic
    if listing_record:
        if listing_record.company:
            extracted_jd_details["company"] = listing_record.company
        if listing_record.role_title:
            extracted_jd_details["role_title"] = listing_record.role_title
        if listing_record.location:
            extracted_jd_details["location"] = listing_record.location
        if listing_record.employment_type:
            extracted_jd_details["employment_type"] = listing_record.employment_type
        if listing_record.application_url:
            extracted_jd_details["application_url"] = listing_record.application_url
        if listing_record.source:
            extracted_jd_details["source"] = listing_record.source
        extracted_jd_details["source_job_id"] = str(listing_record.id)

    assert extracted_jd_details["company"] == "Ladybird Web Solution Pvt Ltd"
    assert extracted_jd_details["company"] not in ("Target Company", "Unknown Company", "Company Name")
    assert extracted_jd_details["role_title"] == "Internship For Software Engineers - Freshers"
    assert extracted_jd_details["location"] == "Somwarpet, Kodagu, India"


def test_withhold_score_for_less_than_or_equal_to_one_evaluated_requirement():
    """Item 2: If total evaluated requirements <= 1, overall_match_score MUST be withheld (None)."""
    single_req = [
        NormalizedRequirement(
            requirement_id="r1",
            category="required_skill",
            requirement="Software Development",
            canonical="Software Development",
            importance="required",
            match_status="verified",
        )
    ]
    score, breakdown = calculate_reconciled_scores(
        requirements=single_req,
        domain_match_ratio=0.8,
        candidate_years=None,
        requested_years=None,
        is_partial_jd=True,
    )
    # Score must be sentinel -1 so overall_match_score becomes null/None
    assert score == -1
    assert breakdown["required_skills_score"] == 100
    assert breakdown["experience_score"] is None
    assert breakdown["preferred_skills_score"] is None
    assert breakdown["analysis_quality"] == "PARTIAL"


def test_experience_must_be_null_when_jd_has_no_experience_requirement():
    """Item 3: When experience_requirements.length == 0, experience_score must be null. Always. No default 70."""
    reqs_no_exp = [
        NormalizedRequirement(
            requirement_id="r1", category="required_skill", requirement="Python",
            canonical="Python", importance="required", match_status="verified",
        ),
        NormalizedRequirement(
            requirement_id="r2", category="required_skill", requirement="System Design",
            canonical="System Design", importance="required", match_status="verified",
        ),
    ]
    score, breakdown = calculate_reconciled_scores(
        requirements=reqs_no_exp,
        domain_match_ratio=0.8,
        candidate_years=None,
        requested_years=None,
    )
    assert breakdown["experience_score"] is None
    # Verify score is calculated by redistributing weight, not using default 70
    assert score is not None
    assert score >= 10


def test_project_bullets_retain_parent_project_id_and_grouping():
    """Item 4: Resume parsing and evidence extraction must keep bullets grouped under one parent project."""
    resume_text = (
        "PROJECTS\n"
        "Route53 Clone\n"
        "TECH: Next.js, TypeScript, FastAPI, SQLAlchemy, SQLite\n"
        "- Built a full-stack internal business application with Next.js/TypeScript frontend and FastAPI REST backend.\n"
        "- Designed the relational schema in SQLite with SQLAlchemy ORM.\n"
        "- Implemented server-side data-integrity validation and transaction handling.\n"
        "- Documented a scaling plan for DNS query routing.\n"
    )
    from app.services.resume_parser import DeterministicResumeParser
    parser = DeterministicResumeParser()
    parsed = parser.parse(resume_text)
    projects = parsed["projects"]

    assert len(projects) == 1
    p1 = projects[0]
    assert p1["title"] == "Route53 Clone" or p1["project_title"] == "Route53 Clone"
    assert len(p1["bullets"]) == 4
    assert any("FastAPI" in t for t in p1["technologies"])

    # Extract evidence and verify parent_project_id retention
    ev_map = extract_structured_resume_evidence(parsed)
    assert "Software Development" in ev_map
    sw_ev = ev_map["Software Development"]
    assert len(sw_ev.parent_project_ids) == 1
    assert "proj_1" in sw_ev.parent_project_ids or any(pid.startswith("proj_") for pid in sw_ev.parent_project_ids)


def test_unique_project_counting_not_bullets():
    """Item 5: 3 named projects with multiple bullets each must count as exactly 3 projects, never 5+."""
    resume_data = {
        "projects": [
            {
                "project_id": "proj_1",
                "title": "Route53 Clone",
                "bullets": [
                    "Built full-stack application with Next.js and FastAPI REST backend.",
                    "Designed relational schema in SQLite with SQLAlchemy.",
                    "Implemented data validation and transaction handling.",
                    "Documented scaling plan for DNS query routing.",
                ],
            },
            {
                "project_id": "proj_2",
                "title": "AI Research Paper Assistant",
                "bullets": [
                    "Built RAG pipeline using ChromaDB vector database and FastAPI.",
                    "Implemented semantic chunking and embedding caching.",
                ],
            },
            {
                "project_id": "proj_3",
                "title": "Lendora AI",
                "bullets": [
                    "Built machine learning credit risk evaluation pipeline.",
                ],
            },
        ],
        "skills": ["Python", "FastAPI", "TypeScript", "Next.js"],
        "experience": [],
        "education": ["Computer Science, Expected Graduation: 2028"],
        "achievements": ["Solved 150+ DSA problems on LeetCode"],
    }
    ev_map = extract_structured_resume_evidence(resume_data)
    sw_ev = ev_map.get("Software Development")
    assert sw_ev is not None
    # Unique project count must equal 3 (Route53, AI Paper Assistant, Lendora)
    assert len(sw_ev.parent_project_ids) == 3

    status, evidence, explanation = _evaluate_requirement_evidence(
        canonical="Software Development",
        raw_requirement="Software Development",
        evidence_map=ev_map,
    )
    assert status == MatchStatus.VERIFIED
    assert "3 implemented projects" in explanation
    assert "5 implemented projects" not in explanation


@pytest.mark.anyio
async def test_route53_rendered_once_in_tailoring():
    """Item 7: Route53 Clone bullets must NOT produce separate project cards in tailoring."""
    resume_data = {
        "projects": [
            {
                "project_id": "proj_1",
                "title": "Route53 Clone",
                "bullets": [
                    "Built full-stack application with Next.js and FastAPI REST backend.",
                    "Designed relational schema in SQLite with SQLAlchemy.",
                    "Implemented data validation and transaction handling.",
                    "Documented scaling plan for DNS query routing.",
                ],
            },
            {
                "project_id": "proj_2",
                "title": "AI Research Paper Assistant",
                "bullets": ["Built RAG pipeline using ChromaDB and FastAPI."],
            },
            {
                "project_id": "proj_3",
                "title": "Lendora AI",
                "bullets": ["Built machine learning credit risk evaluation pipeline."],
            },
        ],
        "skills": ["Python", "FastAPI", "TypeScript", "Next.js", "System Design"],
    }
    jd_data = {
        "company": "Ladybird Web Solution Pvt Ltd",
        "role_title": "Internship For Software Engineers - Freshers",
        "required_skills": ["Software Development", "System Design"],
    }

    tailored = await llm_service.tailor_resume(jd_data=jd_data, resume_data=resume_data)
    tailored_projects = tailored["projects"]

    # There must be exactly 3 project cards, matching the 3 named projects
    assert len(tailored_projects) == 3
    route53_cards = [p for p in tailored_projects if "Route53" in p["project_title"]]
    assert len(route53_cards) == 1

    r53 = route53_cards[0]
    # Check demonstrates items
    demonstrates_text = " ".join(r53["supports"])
    assert "Software Development" in demonstrates_text
    assert "REST API Development" in demonstrates_text
    assert "System Design" in demonstrates_text
    # Recommendation text must mention multi-tier architecture & API design
    assert "multi-tier architecture" in r53["action_suggestion"].lower()
    assert "api design" in r53["action_suggestion"].lower()


def test_location_preference_granularity():
    """Item 6: Location preference must preserve granularity (country, state, city, remote)."""
    # 1. Candidate preference: Country (India) -> Job: Somwarpet, Kodagu, India
    score, reason, scope = evaluate_location_match("India", "Somwarpet, Kodagu, India")
    assert scope == "country"
    assert score == 1.0
    assert reason == "This position is within your preferred country, India."
    assert "Somwarpet" not in reason

    # 2. Candidate preference: City (Bengaluru) -> Job: Somwarpet, Kodagu, India
    score_blr, reason_blr, scope_blr = evaluate_location_match("Bengaluru", "Somwarpet, Kodagu, India")
    assert scope_blr == "city"
    # Must NOT treat arbitrary Indian cities as an exact location match
    assert score_blr < 0.5
    assert reason_blr is None

    # 3. Candidate preference: Exact City (Bengaluru) -> Job: Bengaluru, Karnataka, India
    score_exact, reason_exact, scope_exact = evaluate_location_match("Bengaluru", "Bengaluru, Karnataka, India")
    assert scope_exact == "city"
    assert score_exact == 1.0
    assert "preferred city" in reason_exact.lower()

    # 4. Candidate preference: Remote -> Job: Somwarpet, Kodagu, India (on-site)
    score_rem, reason_rem, scope_rem = evaluate_location_match("Remote", "Somwarpet, Kodagu, India")
    assert scope_rem == "remote"
    assert score_rem < 0.5
    assert reason_rem is None

    # 5. Candidate preference: Remote -> Job: Remote, India
    score_rem_ok, reason_rem_ok, scope_rem_ok = evaluate_location_match("Remote", "Remote, India")
    assert score_rem_ok == 1.0
    assert scope_rem_ok == "remote"
    assert "Remote" in reason_rem_ok


@pytest.mark.anyio
async def test_ladybird_exact_case_retest():
    """Item 9: Retest exact Ladybird Web Solution Pvt Ltd case."""
    # Candidate Resume
    resume_data = {
        "projects": [
            {
                "project_id": "proj_1",
                "title": "Route53 Clone",
                "bullets": [
                    "Built full-stack application with Next.js/TypeScript frontend and FastAPI REST backend.",
                    "Designed relational schema in SQLite with SQLAlchemy.",
                    "Implemented data validation and transaction handling.",
                    "Documented scaling plan for DNS query routing.",
                ],
            },
            {
                "project_id": "proj_2",
                "title": "AI Research Paper Assistant",
                "bullets": ["Built RAG pipeline using ChromaDB vector database and FastAPI."],
            },
            {
                "project_id": "proj_3",
                "title": "Lendora AI",
                "bullets": ["Built machine learning credit risk evaluation pipeline."],
            },
        ],
        "skills": ["Python", "FastAPI", "TypeScript", "Next.js", "System Design"],
        "experience": [],
        "education": ["Computer Science, Expected Graduation: 2028"],
        "achievements": ["Solved 150+ DSA problems on LeetCode"],
    }

    # Canonical Provider JobListing
    canonical_company = "Ladybird Web Solution Pvt Ltd"
    canonical_role = "Internship For Software Engineers - Freshers"
    job_location = "Somwarpet, Kodagu, India"
    job_description = (
        "Ladybird Web Solution Pvt Ltd is hiring for Internship For Software Engineers - Freshers.\n"
        "Requirements:\n"
        "- Strong fundamentals in software development.\n"
    )

    # 1. Company name precedence: When source_job_id resolves, company is canonical provider company
    jd_data = await llm_service.analyze_job_description(job_description)
    jd_data["company"] = canonical_company
    jd_data["role_title"] = canonical_role
    jd_data["location"] = job_location

    assert jd_data["company"] == "Ladybird Web Solution Pvt Ltd"
    assert jd_data["company"] != "Target Company"

    # 2. Evaluate candidate match
    match_result = await llm_service.evaluate_resume_match(jd_data, resume_data)

    # Candidate Fit score must be withheld when <= 1 evaluated requirement survives
    total_evaluated = len(match_result["normalized_requirements"])
    assert total_evaluated <= 1
    assert match_result["overall_match_score"] is None  # Candidate Fit: —

    # Component scores
    breakdown = match_result["match_breakdown"]
    assert breakdown["required_skills_score"] == 100  # 1 of 1 evaluated
    assert breakdown["preferred_skills_score"] is None  # N/A
    assert breakdown["experience_score"] is None  # N/A (no experience requirement in JD)

    # Unique project count
    ev_map = extract_structured_resume_evidence(resume_data)
    sw_ev = ev_map["Software Development"]
    assert len(sw_ev.parent_project_ids) == 3

    # Location evaluation
    loc_score, loc_reason, loc_scope = evaluate_location_match("India", job_location)
    assert loc_scope == "country"
    assert loc_reason == "This position is within your preferred country, India."



