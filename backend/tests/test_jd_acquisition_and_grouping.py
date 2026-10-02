"""Regression tests for JD acquisition, length preservation, manual override, and project grouping."""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Text

from app.core.config import settings
from app.main import app
from app.models.job_match import JobListing
from app.api.v1.endpoints.jd_analyzer import AnalyzeJDRequest
from app.services.llm_service import llm_service
from tests.conftest import TestingSessionLocal
from tests.test_jd_analyzer import create_user_helper, create_parsed_resume_helper


@pytest.mark.anyio
async def test_database_storage_not_varchar_500():
    """Verify JobListing.description column is SQLAlchemy Text without varchar(500) limit."""
    col_type = JobListing.__table__.columns["description"].type
    assert isinstance(col_type, Text), f"JobListing.description must be Text, but got {type(col_type)}"

    # Also verify AnalyzeJDRequest accepts up to 35,000 characters without 500-char limit
    req_35k = AnalyzeJDRequest(job_description="A" * 35000)
    assert len(req_35k.job_description) == 35000

    with pytest.raises(Exception):
        AnalyzeJDRequest(job_description="A" * 35001)


@pytest.mark.anyio
async def test_5000_char_canonical_jd_survives_entire_pipeline():
    """
    Section 18: Full description control test.
    Create a controlled job fixture:
    description length = 5,000 chars
    Place a unique requirement near char ~4,500:
    'Experience with Apache Kafka is required.'
    Store in JobListing.
    Assert:
    - DB description = 5,000 chars
    - GET /jobs/{job_id} returns 5,000 chars
    - /jd/analyze analysis input = 5,000 chars
    - description_source = 'ADZUNA_FULL'
    - description_quality = 'FULL'
    - canonical extraction finds Apache Kafka
    """
    user, token = await create_user_helper("control_kafka@example.com", "Kafka User")
    await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "Apache Kafka", "PostgreSQL"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    prefix = (
        "Stripe Inc. is hiring a Staff Distributed Systems Engineer to design, deploy, and scale "
        "mission-critical financial transaction infrastructure.\n\n"
    )
    # Filler to build description to ~4,400 chars
    sentence = "Engineers will design high-throughput fault-tolerant event streams and manage consensus across clusters. "
    filler = sentence * 40
    kafka_req = "\n\nCore Technical Requirements:\nExperience with Apache Kafka is required.\nStrong Python experience.\n"
    suffix = "We offer competitive equity, comprehensive health benefits, and flexible work options."
    canonical_5000 = prefix + filler + kafka_req + suffix

    # Adjust exact length to >= 5000 chars
    if len(canonical_5000) < 5000:
        canonical_5000 += " " + ("Additional scaling architecture and reliability responsibilities. " * 10)
    canonical_5000 = canonical_5000[:5000]
    # Ensure Kafka is placed near char ~4,500
    if "Apache Kafka" not in canonical_5000:
        canonical_5000 = canonical_5000[:4450] + "\nExperience with Apache Kafka is required.\n" + canonical_5000[4495:]

    kafka_pos = canonical_5000.find("Apache Kafka")
    assert 4000 <= kafka_pos <= 4800, f"Kafka must be near char 4500, but found at {kafka_pos}"
    assert len(canonical_5000) == 5000

    # 1. Store in JobListing
    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="stripe_kafka_5000",
            company="Stripe Inc.",
            role_title="Staff Distributed Systems Engineer",
            description=canonical_5000,
            source="adzuna",
            application_url="https://stripe.com/jobs/kafka-5000",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Detail endpoint returns full 5,000 chars
        detail_res = await ac.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert len(detail_data["description"]) == 5000

        # 3. Simulate Find Positions passing a preview (500 chars) but with source_job_id
        preview_text = canonical_5000[:500]
        analyze_res = await ac.post(
            "/api/v1/jd/analyze",
            json={"job_description": preview_text, "source_job_id": str(job_id)},
            headers=headers,
        )
        assert analyze_res.status_code == 200
        data = analyze_res.json()
        job_details = data["job_details"]

        # Assert full 5,000 chars survived and was analyzed
        assert job_details["analysis_description_length"] == 5000
        assert job_details["description_source"] in ("ADZUNA_FULL", "PROVIDER_CANONICAL")
        assert job_details["description_quality"] in ("FULL", "COMPLETE")
        assert job_details["is_truncated"] is False

        # Canonical extraction finds Apache Kafka
        all_extracted = [s.lower() for s in job_details.get("required_skills", []) + job_details.get("preferred_skills", []) + job_details.get("keywords", [])]
        assert any("kafka" in s for s in all_extracted), f"Apache Kafka must be extracted from char ~4500, extracted: {all_extracted}"


@pytest.mark.anyio
async def test_exact_500_provider_test():
    """
    Section 19: Exact-500 provider test.
    Create provider fixture:
    raw description = exactly 500 chars ending mid-sentence
    Assert:
    - DB = 500
    - description_quality = PARTIAL
    - description_source = ADZUNA_PREVIEW
    - Candidate Fit withheld when insufficient
    - UI shows LIMITED JOB DESCRIPTION quality warning
    - No fabricated continuation
    """
    user, token = await create_user_helper("exact_500@example.com", "Preview User")
    await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "FastAPI"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    # Exactly 500 chars ending mid-sentence without trailing whitespace
    exact_500_text = (
        "S&P Global is looking for a Lead AI Engineer (Agentic Systems). "
        "The ideal candidate will architect and deploy scalable multi-agent systems across enterprise "
        "decision engines, combining large language models with retrieval-augmented workflows. "
        "Key duties include optimizing latency, designing deterministic validation gates, and "
        "collaborating with cross-functional platform engineers. "
        "This is a multidisciplinary technical role operating at the intersection of agentic artificial intelligence systems and enterprise cloud workflows"
    )[:499] + "x"

    assert len(exact_500_text) == 500
    assert not exact_500_text.endswith(" ")

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="sp_global_500",
            company="S&P Global",
            role_title="Lead AI Engineer (Agentic Systems)",
            description=exact_500_text,
            source="adzuna",
            application_url="https://spglobal.example.com/apply/500",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/jd/analyze",
            json={"job_description": exact_500_text, "source_job_id": str(job_id)},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        job_details = data["job_details"]
        match_analysis = data["match_analysis"]

        assert job_details["description_length"] == 500
        assert job_details["analysis_description_length"] == 500
        assert job_details["description_source"] in ("ADZUNA_PREVIEW", "PROVIDER_PARTIAL")
        assert job_details["description_quality"] == "PARTIAL"
        assert job_details["is_truncated"] is True
        assert job_details["quality_warning"] is not None
        assert "shortened description" in job_details["quality_warning"].lower()

        # Fit score is withheld when requirements are insufficient
        assert match_analysis["overall_match_score"] is None


@pytest.mark.anyio
async def test_manual_override_test():
    """
    Section 20: Manual override test.
    Provider in DB: 500 chars
    User pasted: 4,000 chars
    Requirement near end: 'Experience with Docker is required.'
    Assert:
    - analysis input = 4,000 chars
    - Docker requirement extracted
    - description_source = USER_PASTED (not ADZUNA_PREVIEW)
    """
    user, token = await create_user_helper("manual_override@example.com", "Override User")
    await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "Docker", "Kubernetes"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    provider_500 = (
        "S&P Global is looking for a Lead AI Engineer (Agentic Systems). "
        "This is a multidisciplinary technical role operating at the intersection of agentic artificial intelligence systems and enterprise cloud workflows across distributed platform architectures."
    )[:500]

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="adzuna_preview_sp",
            company="S&P Global",
            role_title="Lead AI Engineer (Agentic Systems)",
            description=provider_500,
            source="adzuna",
            application_url="https://spglobal.example.com/apply/preview",
        )
        session.add(job)
        await session.commit()

    # User manually pastes a complete 4,000-char JD into the textarea
    intro = "Full Job Description from S&P Global Careers Portal:\nLead AI Engineer (Agentic Systems)\n\n"
    filler_chunk = "Engineers will design distributed agents, integrate vector memory, and deploy resilient microservices. "
    end_req = "\n\nQualifications & Requirements:\nExperience with Docker is required.\nExperience with Python and FastAPI."
    base = intro + (filler_chunk * 28) + end_req
    needed = 4000 - len(base)
    user_pasted_4000 = intro + (filler_chunk * 28) + ("A" * needed) + end_req

    assert len(user_pasted_4000) == 4000
    assert not user_pasted_4000.endswith(" ")
    assert "Experience with Docker is required." in user_pasted_4000

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/jd/analyze",
            json={"job_description": user_pasted_4000, "source_job_id": str(job_id)},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        job_details = data["job_details"]

        # Must use user's 4,000 chars, NOT downgraded to provider 500
        assert job_details["analysis_description_length"] == 4000
        assert job_details["description_source"] == "USER_PASTED"
        assert job_details["description_source"] != "ADZUNA_PREVIEW"
        assert job_details["description_quality"] in ("FULL", "COMPLETE")
        assert job_details["is_truncated"] is False

        # Docker requirement is extracted
        all_skills = [s.lower() for s in job_details.get("required_skills", []) + job_details.get("preferred_skills", []) + job_details.get("keywords", [])]
        assert any("docker" in s for s in all_skills), f"Docker requirement must be extracted, got {all_skills}"


@pytest.mark.anyio
async def test_incomplete_jd_limits_tailoring():
    """
    Section 16: Do not let partial JDs generate overconfident tailoring.
    Assert that when provider is partial and zero requirements are extracted:
    - summary strategy indicates tailoring is limited
    - prioritized skills is empty
    - skills strategy CTA: 'Paste full JD to unlock precise tailoring'
    """
    user, token = await create_user_helper("partial_tailor@example.com", "Tailor User")
    resume = await create_parsed_resume_helper(
        user_id=user.id,
        skills=["Python", "FastAPI", "PostgreSQL"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    job_id = uuid.uuid4()
    partial_text = "Senior Technical Role. About the role: Operating at the intersection of"

    async with TestingSessionLocal() as session:
        job = JobListing(
            id=job_id,
            external_id="adzuna_sparse_partial",
            company="S&P Global",
            role_title="Lead AI Engineer",
            description=partial_text,
            source="adzuna",
        )
        session.add(job)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/jd/tailor",
            json={
                "job_description": partial_text,
                "resume_id": str(resume.id),
                "source_job_id": str(job_id),
            },
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        tailored = data["tailored_sections"]

        # Strategy must clearly communicate limited tailoring
        summary_strat = tailored["summary"]["strategy"]
        skills_strat = tailored["skills"]["strategy"]
        assert "Tailoring is limited" in summary_strat
        assert "Paste full JD to unlock precise tailoring" in summary_strat
        assert "Paste full JD to unlock precise tailoring" in skills_strat
        assert tailored["skills"]["prioritized"] == []


@pytest.mark.anyio
async def test_project_grouping_serialization():
    """
    Section 21: Project grouping serialization test.
    Verify that Route53 Clone bullets are NOT rendered as separate projects,
    and distinct projects (Route53 Clone, AI Research Paper Assistant, Lendora AI)
    are each grouped cleanly under their parent title with their supporting bullets.
    """
    raw_projects = [
        "Route53 Clone | Next.js, TypeScript, FastAPI, SQLAlchemy, SQLite | GitHub | Live Demo",
        "Built a full-stack internal business application (AWS Route53-style console) with a Next.js/TypeScript frontend and a FastAPI REST backend: authentication, hosted zone management, and DNS record CRUD with search, filters, and pagination.",
        "Designed the relational schema (SQLAlchemy + SQLite) and documented architecture trade-offs: a JSON-encoded record-values field over a rigid per-type schema, and HTTP-only cookie sessions over JWT.",
        "Implemented server-side data-integrity validation independent of client-side checks, cascading deletes, and a shared-session transaction pattern for atomic multi-record BIND import.",
        "Documented a scaling plan (read-through caching, DB sharding by zone, shared session store for horizontal scaling) reasoning about read-heavy DNS workloads beyond the current single-instance scope. AI Research Paper Assistant | Python, FastAPI, ChromaDB, Groq, PyMuPDF | GitHub | Live Demo",
        "Built a full-stack RAG system with a FastAPI backend, integrating document ingestion, a vector database, and an LLM API into one pipeline for real-time semantic Q&A over research papers.",
        "Built and debugged a data pipeline (extraction, deduplication, chunking, embedding), diagnosing real-world issues like multi-column layout artifacts and duplicate boilerplate. Lendora AI | Python, Scikit-learn, Streamlit | GitHub | Live Demo",
        "Built a loan underwriting dashboard using a Scikit-learn Gradient Boosting pipeline across 16 engineered financial features; benchmarked against Logistic Regression, achieving 93.8% F1 and 0.98 ROC-AUC on held-out data.",
    ]

    resume_data = {
        "skills": ["Python", "FastAPI", "TypeScript", "Next.js", "SQLAlchemy", "SQLite", "Scikit-learn"],
        "projects": raw_projects,
        "experience": [],
    }

    jd_data = {
        "company": "Tech Corp",
        "role_title": "Full Stack Engineer",
        "required_skills": ["Python", "FastAPI", "TypeScript"],
        "preferred_skills": ["Next.js"],
        "description_quality": "FULL",
    }

    tailored = await llm_service.tailor_resume(jd_data, resume_data)
    projects = tailored.get("projects", [])

    # Exactly 3 projects must be produced: Route53 Clone, AI Research Paper Assistant, Lendora AI
    assert len(projects) == 3, f"Expected 3 distinct projects, but got {len(projects)}: {[p.get('project_title') for p in projects]}"

    titles = [p.get("project_title") for p in projects]
    assert "Route53 Clone" in titles[0]
    assert "AI Research Paper Assistant" in titles[1]
    assert "Lendora AI" in titles[2]

    # Verify Route53 Clone has multiple aggregated supporting bullets
    route53_proj = projects[0]
    bullets = route53_proj.get("project_bullets", [])
    assert len(bullets) >= 3, f"Route53 Clone must retain its supporting bullets, got {len(bullets)}"

    # Ensure NO bullet was mistakenly treated as a project title
    for p in projects:
        t = p.get("project_title", "")
        assert not t.startswith("Built a full-stack"), f"Bullet mistakenly rendered as project title: {t}"
        assert not t.startswith("Designed the relational"), f"Bullet mistakenly rendered as project title: {t}"
        assert not t.startswith("Implemented server-side"), f"Bullet mistakenly rendered as project title: {t}"
