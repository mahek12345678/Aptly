import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.models.job_match import JobListing
from app.models.resume import Resume
from app.models.user import User
from app.services.skill_normalizer import NormalizedRequirement, recompute_component_score
from tests.conftest import TestingSessionLocal


async def create_user_helper(email: str = "jd_user@example.com", name: str = "JD Tester") -> tuple[User, str]:
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name=name,
            onboarding_completed=True,
            onboarding_step=4,
        )
        session.add(user)
        await session.commit()
    token = create_access_token(data={"sub": str(user_id)})
    return user, token


async def create_parsed_resume_helper(
    user_id: uuid.UUID,
    skills: list[str] = None,
    experience: list[str] = None,
    projects: list[str] = None,
) -> Resume:
    if skills is None:
        skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "React"]
    if experience is None:
        experience = [
            "Software Engineer at Acme Corp (2022-2024): Built RESTful APIs using Python and FastAPI, optimizing database queries on PostgreSQL.",
        ]
    if projects is None:
        projects = [
            "Cloud Tracker: Full-stack portfolio application with Docker containerization and CI/CD pipelines.",
        ]

    parsed_data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "skills": skills,
        "experience": experience,
        "projects": projects,
        "education": ["B.S. in Computer Science, Tech University, 2022"],
        "certifications": ["AWS Certified Cloud Practitioner"],
        "achievements": ["Hackathon Winner 2023"],
        "raw_text": f"Jane Doe. Skills: {', '.join(skills)}",
    }

    now = datetime.now(timezone.utc)
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user_id,
        file_name="jane_doe_resume.pdf",
        file_path="/uploads/resumes/jane_doe_resume.pdf",
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

    return resume


@pytest.mark.anyio
async def test_unauthenticated_jd_endpoints_fail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/api/v1/jd/analyze", json={"job_description": "We are hiring a Software Engineer at Stripe."})
        assert r1.status_code == 401

        r2 = await ac.post(
            "/api/v1/jd/tailor",
            json={"job_description": "We are hiring a Software Engineer at Stripe.", "resume_id": str(uuid.uuid4())},
        )
        assert r2.status_code == 401


@pytest.mark.anyio
async def test_analyze_without_resume_returns_error():
    user, token = await create_user_helper("no_resume@example.com", "No Resume User")
    headers = {"Authorization": f"Bearer {token}"}

    sample_jd = (
        "Backend Engineer at Stripe. Location: San Francisco, CA. "
        "We are looking for an experienced Python and PostgreSQL engineer to build core payment APIs. "
        "Responsibilities: Design scalable services. Qualifications: 2+ years of experience with Python, SQL, REST APIs."
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/jd/analyze", json={"job_description": sample_jd}, headers=headers)
        assert response.status_code == 400
        assert "No parsed resume found" in response.json()["detail"]


@pytest.mark.anyio
async def test_analyze_jd_structured_extraction_and_matching():
    user, token = await create_user_helper("analyzer_user@example.com", "Analyzer User")
    resume = await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
        experience=["Engineered microservices using Python and PostgreSQL."],
    )
    headers = {"Authorization": f"Bearer {token}"}

    sample_jd = (
        "Backend Engineer at Stripe\n"
        "Location: San Francisco, CA (Hybrid)\n"
        "Compensation: $170,000 - $210,000 / yr\n"
        "Deadline: Applications close Oct 30, 2026\n\n"
        "About the Role:\n"
        "Stripe is hiring a Backend Engineer to scale our global financial infrastructure.\n\n"
        "Requirements:\n"
        "- Strong proficiency in Python, PostgreSQL, and Docker\n"
        "- Experience with AWS and Kubernetes is preferred\n"
        "- Design and implement scalable REST APIs and distributed systems"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/jd/analyze", json={"job_description": sample_jd}, headers=headers)
        assert response.status_code == 200

        data = response.json()
        job = data["job_details"]
        match = data["match_analysis"]

        # Validate extraction
        assert "Stripe" in job["company"] or job["company"] != "Unknown Company"
        assert "Backend Engineer" in job["role_title"]
        assert job["location"] is not None
        assert len(job["required_skills"]) > 0

        # Validate matching
        assert 0 <= match["overall_match_score"] <= 100
        # Python, PostgreSQL, Docker should be matched
        assert any("python" in s.lower() for s in match["matched_skills"])
        # AWS or Kubernetes should be missing
        assert any(k in [s.lower() for s in match["missing_skills"]] for k in ["aws", "kubernetes"])
        assert len(match["strengths"]) > 0
        assert len(match["gaps"]) > 0

        # Validate resume metadata returned
        assert data["resume_id"] == str(resume.id)
        assert data["resume_filename"] == "jane_doe_resume.pdf"


@pytest.mark.anyio
async def test_anti_hallucination_integrity():
    user, token = await create_user_helper("strict_user@example.com", "Strict User")
    # User ONLY has Python and SQL
    resume = await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "SQL"],
        experience=["Junior Developer working with Python and SQL scripts."],
        projects=["Data extraction pipeline using Python."],
    )
    headers = {"Authorization": f"Bearer {token}"}

    sample_jd = (
        "Senior Distributed Systems Engineer at CloudTech.\n"
        "Required technologies: Rust, Golang, Kubernetes, GraphQL, and Python.\n"
        "You must be an expert in Rust concurrency and Kubernetes orchestration."
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/jd/analyze", json={"job_description": sample_jd}, headers=headers)
        assert response.status_code == 200

        data = response.json()
        match = data["match_analysis"]

        matched_lower = [s.lower() for s in match["matched_skills"]]
        # Python should be matched
        assert "python" in matched_lower
        # Rust and Kubernetes MUST NOT be matched since candidate does NOT have them!
        assert "rust" not in matched_lower
        assert "kubernetes" not in matched_lower
        # Rust and Kubernetes must be identified as gaps / missing
        missing_lower = [s.lower() for s in match["missing_skills"]]
        assert "rust" in missing_lower or "kubernetes" in missing_lower


@pytest.mark.anyio
async def test_tailor_resume_endpoint_and_isolation():
    user_a, token_a = await create_user_helper("user_a_tailor@example.com", "Tailor User A")
    user_b, token_b = await create_user_helper("user_b_tailor@example.com", "Tailor User B")

    resume_a = await create_parsed_resume_helper(user_id=user_a.id)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    sample_jd = (
        "Full Stack Developer at Fintech Inc. "
        "Looking for React, Python, and Docker developers to build modern web dashboards."
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User B cannot tailor User A's resume (404)
        r_unauth = await ac.post(
            "/api/v1/jd/tailor",
            json={"job_description": sample_jd, "resume_id": str(resume_a.id)},
            headers=headers_b,
        )
        assert r_unauth.status_code == 404

        # User A can tailor own resume
        response = await ac.post(
            "/api/v1/jd/tailor",
            json={"job_description": sample_jd, "resume_id": str(resume_a.id)},
            headers=headers_a,
        )
        assert response.status_code == 200
        data = response.json()
        assert "tailored_sections" in data
        sections = data["tailored_sections"]
        assert "summary" in sections
        assert "skills" in sections
        assert "experience" in sections
        assert "projects" in sections

        # Verify User A's original resume in DB was NOT modified or overwritten
        async with TestingSessionLocal() as session:
            db_resume = await session.get(Resume, resume_a.id)
            assert db_resume.file_name == "jane_doe_resume.pdf"
            assert db_resume.parsed_status == "parsed"
            assert "Jane Doe" in db_resume.parsed_data["name"]


@pytest.mark.anyio
async def test_get_job_detail_endpoint_returns_full_description():
    """Verify GET /api/v1/jobs/{job_id} returns full canonical description without truncation."""
    user, token = await create_user_helper("job_detail_user@example.com", "Job Detail User")
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    # 4,200 characters detailed JD
    full_body = (
        "Principal Systems Architect at Stripe Inc.\n"
        "About the Role: We are seeking a Principal Systems Architect to design, scale, and maintain our global "
        "financial transaction processing systems across multiple hybrid cloud regions.\n"
        "Responsibilities:\n"
        "- Architect high-throughput distributed message queues handling over 500,000 transactions per second.\n"
        "- Build resilient data ingestion pipelines with zero downtime guarantees.\n"
        "- Lead database sharding and performance tuning initiatives across distributed PostgreSQL clusters.\n"
        "Requirements:\n"
        "- 8+ years experience in backend engineering and distributed systems architecture.\n"
        "- Deep expertise in Python, PostgreSQL, Docker, Kubernetes, and Redis.\n"
        "- Track record of designing fault-tolerant financial ledger architectures.\n"
    )
    long_padding = "Additional requirements and context regarding system safety, security compliance, SOC2, and ISO standards.\n" * 45
    canonical_text = (full_body + long_padding)[:4200]
    assert len(canonical_text) == 4200

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="stripe_full_arch_4200",
            company="Stripe Inc.",
            role_title="Principal Systems Architect",
            description=canonical_text,
            source="adzuna",
            application_url="https://stripe.com/jobs/arch-4200",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(job_id)
        assert data["company"] == "Stripe Inc."
        assert data["role_title"] == "Principal Systems Architect"
        assert len(data["description"]) == 4200
        assert data["description"] == canonical_text


@pytest.mark.anyio
async def test_handoff_full_canonical_jd_survives():
    """Verify that when Analyze & Tailor passes source_job_id, the 4,200 char canonical description is used."""
    user, token = await create_user_helper("handoff_full@example.com", "Handoff User")
    resume = await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "PostgreSQL", "Docker", "Kubernetes", "Redis"],
        experience=["Senior Systems Engineer: Built distributed pipelines in Python and PostgreSQL."],
    )
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    full_body = (
        "Principal Systems Architect at Stripe Inc.\n"
        "Requirements:\n"
        "- 5+ years experience in software engineering\n"
        "- Expert knowledge of Python and PostgreSQL\n"
        "- Hands-on proficiency with Docker and Kubernetes\n"
    )
    long_padding = "Detailed architectural overview and engineering principles for global high-availability payment systems.\n" * 45
    canonical_text = (full_body + long_padding)[:4200]
    assert len(canonical_text) == 4200

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="stripe_handoff_4200",
            company="Stripe Inc.",
            role_title="Principal Systems Architect",
            description=canonical_text,
            source="adzuna",
            application_url="https://stripe.com/jobs/arch-4200",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Simulate frontend passing a truncated 500-char preview alongside source_job_id
        short_preview = canonical_text[:500]
        res = await ac.post(
            "/api/v1/jd/analyze",
            json={"job_description": short_preview, "source_job_id": str(job_id)},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        job_details = data["job_details"]
        match_analysis = data["match_analysis"]

        # Full canonical description must be resolved
        assert job_details["description_source"] in ("ADZUNA_FULL", "PROVIDER_CANONICAL")
        assert job_details["description_quality"] in ("FULL", "COMPLETE")
        assert job_details["analysis_description_length"] == 4200
        assert job_details["is_truncated"] is False
        assert job_details["company"] == "Stripe Inc."
        assert job_details["role_title"] == "Principal Systems Architect"

        # Fit score is computed (NOT withheld) because full description was analyzed
        assert match_analysis["overall_match_score"] is not None
        assert match_analysis["overall_match_score"] > 0


@pytest.mark.anyio
async def test_handoff_provider_partial_withheld_fit():
    """Verify that when provider only returns a 500-char truncated snippet, Candidate Fit score is withheld."""
    user, token = await create_user_helper("handoff_partial@example.com", "Partial User")
    await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "PostgreSQL"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    # Snippet of 500 chars ending abruptly with a hanging connector
    partial_text = (
        "Ladybird Web Solution Pvt Ltd is hiring for Internship For Software Engineers - Freshers.\n"
        "Requirements:\n"
        "- Strong fundamentals in software development.\n"
        "About the team: You will be collaborating closely with product designers, qa engineers, and devops "
        "specialists across the organization to deliver high quality web products. In this role, you will be part of the"
    )
    # Ensure length is <= 500 and ends abruptly
    partial_text = partial_text[:500]

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="adzuna_partial_500",
            company="Ladybird Web Solution Pvt Ltd",
            role_title="Internship For Software Engineers - Freshers",
            description=partial_text,
            source="adzuna",
            application_url="https://ladybird.example.com/jobs/500",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/jd/analyze",
            json={"job_description": partial_text, "source_job_id": str(job_id)},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        job_details = data["job_details"]
        match_analysis = data["match_analysis"]

        assert job_details["description_source"] in ("ADZUNA_PREVIEW", "PROVIDER_PARTIAL")
        assert job_details["description_quality"] == "PARTIAL"
        assert job_details["is_truncated"] is True

        # Candidate Fit score MUST be withheld (null / None)
        assert match_analysis["overall_match_score"] is None
        # But component scores remain accessible
        breakdown = match_analysis["match_breakdown"]
        assert "required_skills_score" in breakdown


@pytest.mark.anyio
async def test_handoff_user_paste_overrides_preview():
    """Verify that when a user pastes a full 4,200 char JD over a 500-char provider snippet, it overrides."""
    user, token = await create_user_helper("handoff_override@example.com", "Override User")
    await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    db_snippet = "Short snippet with only 100 characters from provider..."
    user_pasted_full = (
        "Senior Backend Engineer at Acme Corp.\n"
        "Requirements:\n"
        "- 4+ years of professional backend engineering\n"
        "- Expertise in Python, FastAPI, and PostgreSQL\n"
        "- Containerization with Docker\n"
    ) + ("Detailed architecture and team culture statements.\n" * 85)
    user_pasted_full = user_pasted_full[:4200]
    assert len(user_pasted_full) == 4200

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="acme_snippet_db",
            company="Acme Corp",
            role_title="Senior Backend Engineer",
            description=db_snippet,
            source="adzuna",
            application_url="https://acme.example.com/apply",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/jd/analyze",
            json={"job_description": user_pasted_full, "source_job_id": str(job_id)},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        job_details = data["job_details"]
        match_analysis = data["match_analysis"]

        # Description source is USER_PASTED, quality is FULL/COMPLETE
        assert job_details["description_source"] == "USER_PASTED"
        assert job_details["description_quality"] in ("FULL", "COMPLETE")
        assert job_details["analysis_description_length"] == 4200
        assert job_details["is_truncated"] is False

        # Authoritative metadata preserved from database
        assert job_details["company"] == "Acme Corp"
        assert job_details["role_title"] == "Senior Backend Engineer"
        assert job_details["source"] == "adzuna"
        assert job_details["application_url"] == "https://acme.example.com/apply"

        # Candidate Fit is scored
        assert match_analysis["overall_match_score"] is not None


@pytest.mark.anyio
async def test_component_score_invariant():
    """Verify the invariant: displayed_component_score == recompute_component_score(component_requirements)."""
    user, token = await create_user_helper("invariant_user@example.com", "Invariant User")
    await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "PostgreSQL", "Docker", "Git"],
        experience=["3 years building Python microservices with PostgreSQL and Docker."],
    )
    headers = {"Authorization": f"Bearer {token}"}

    jd_text = (
        "Staff Software Engineer at CloudCorp\n"
        "Requirements:\n"
        "- 3+ years experience in Python and PostgreSQL\n"
        "- Proficiency in Docker\n"
        "Preferred:\n"
        "- Experience with Kubernetes and Redis\n"
        "Qualifications:\n"
        "- 3+ years of professional software development experience\n"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/jd/analyze",
            json={"job_description": jd_text},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        breakdown = data["match_analysis"]["match_breakdown"]
        norm_reqs_raw = data["match_analysis"]["normalized_requirements"]

        # Parse normalized requirements back into NormalizedRequirement models
        norm_reqs = [NormalizedRequirement.model_validate(r) for r in norm_reqs_raw]

        req_skills = [r for r in norm_reqs if r.score_component == "required_skills"]
        pref_skills = [r for r in norm_reqs if r.score_component == "preferred_skills"]
        exp_reqs = [r for r in norm_reqs if r.score_component == "experience"]

        # Invariant checks:
        if req_skills:
            expected_req = recompute_component_score(req_skills)
            assert breakdown["required_skills_score"] == expected_req

        if pref_skills:
            expected_pref = recompute_component_score(pref_skills)
            assert breakdown["preferred_skills_score"] == expected_pref

        if exp_reqs:
            expected_exp = recompute_component_score(exp_reqs)
            assert breakdown["experience_score"] == expected_exp

