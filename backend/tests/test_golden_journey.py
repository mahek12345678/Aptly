"""Aptly Golden Journey End-to-End QA Integration Tests.

Validates the complete core journey for a real user:
Google Auth -> Onboarding Steps 1-4 -> Real Resume Upload & Parsing
-> Initial Dashboard State (Factual) -> Find Positions (Grounded Hybrid Ranking)
-> Job Selection & Entity Consistency -> Full/Partial JD Analyzer & Non-Hallucinatory Tailoring
-> Apply Intent & Duplicate Protection -> "Not Yet" vs "Confirm Applied"
-> Track Jobs (Applied -> OA -> Interview -> Offer)
-> Dashboard Live Reconciliation (Jobs Applied, Replies Received, Offers Received)
-> Ask Aptly Contextual Queries -> Strict User Isolation.
"""
from datetime import datetime, timezone
import io
from pathlib import Path
import shutil
import tempfile
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.models.application import JobApplication, TrackingState
from app.models.job_match import DailyMatch, JobListing
from app.models.preference import UserPreference
from app.models.resume import Resume
from app.models.user import User
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
async def setup_test_uploads():
    temp_dir = tempfile.mkdtemp()
    orig_upload_dir = settings.RESUME_UPLOAD_DIR
    settings.RESUME_UPLOAD_DIR = Path(temp_dir)
    yield
    settings.RESUME_UPLOAD_DIR = orig_upload_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


async def create_golden_user(email: str = "golden_user@example.com", name: str = "Alex Morgan") -> tuple[User, str]:
    user_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        user = User(
            id=user_id,
            google_id=f"google_{user_id}",
            email=email,
            name=name,
            profile_picture_url="https://lh3.googleusercontent.com/a/test_pic",
            onboarding_completed=False,
            onboarding_step=1,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(data={"sub": str(user_id), "email": email, "name": name})
    return user, token


@pytest.mark.anyio
async def test_golden_journey_complete_flow():
    """Execute the full end-to-end Golden Journey on a fresh user."""
    # =========================================================================
    # 1. FRESH USER AUTH & INITIAL STATE
    # =========================================================================
    user, token = await create_golden_user("alex_golden@example.com", "Alex Morgan")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Check /auth/me
        me_res = await ac.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["email"] == "alex_golden@example.com"
        assert me_data["name"] == "Alex Morgan"
        assert me_data["onboarding_completed"] is False
        assert me_data["onboarding_step"] == 1

        # =====================================================================
        # 2. ONBOARDING STEP 1 — About You / Preferences
        # =====================================================================
        pref_payload = {
            "user_type": "professional",
            "opportunity_type": "full_time",
            "graduation_year": None,
            "preferred_location": "San Francisco, CA",
            "preferred_roles": ["AI Engineer", "Backend Engineer"],
            "interests": ["Distributed Systems", "Machine Learning", "FastAPI"],
        }
        step1_res = await ac.put("/api/v1/onboarding/preferences", headers=headers, json=pref_payload)
        assert step1_res.status_code == 200
        step1_data = step1_res.json()
        assert step1_data["preferred_location"] == "San Francisco, CA"
        assert "AI Engineer" in step1_data["preferred_roles"]

        # Verify onboarding_step advanced to 2
        me_step2 = await ac.get("/api/v1/auth/me", headers=headers)
        assert me_step2.json()["onboarding_step"] == 2

        # =====================================================================
        # 3. ONBOARDING STEP 2 — Real Resume Upload & Deterministic Parsing
        # =====================================================================
        # Realistic resume text covering skills, projects, and experience
        resume_text = (
            "Alex Morgan\n"
            "Email: alex.morgan@example.com | Phone: 555-0199 | San Francisco, CA\n\n"
            "EDUCATION\n"
            "University of California, Berkeley - B.S. in Computer Science, 2024\n\n"
            "TECHNICAL SKILLS\n"
            "Languages: Python, Go, TypeScript, SQL\n"
            "Frameworks: FastAPI, PyTorch, Docker, Kubernetes, PostgreSQL, Redis, Apache Kafka\n\n"
            "EXPERIENCE\n"
            "Software Engineer - Cloud Systems Inc (2024 - Present)\n"
            "- Designed scalable REST and gRPC microservices in Python and FastAPI handling 10M requests daily.\n"
            "- Optimized PostgreSQL database queries, reducing P99 latency by 45%.\n\n"
            "PROJECTS\n"
            "Route53 Clone | Python, DNS, SQLite\n"
            "- Built an authoritative DNS server in Python implementing RFC 1035 wire protocol parsing.\n"
            "- Implemented in-memory zone caching with TTL expiry and sub-millisecond query response.\n"
            "AI Research Paper Assistant | PyTorch, Transformers, FastAPI\n"
            "- Developed an agentic retrieval-augmented pipeline for semantic document search.\n"
            "- Integrated vector embeddings and chunk-level reranking for accurate citations.\n"
        )
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), resume_text)
        pdf_bytes = doc.tobytes()
        doc.close()
        files = {"file": ("Alex_Morgan_Resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

        upload_res = await ac.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert upload_res.status_code == 200
        resume_id = upload_res.json()["id"]

        # Parse resume explicitly (as done by frontend on upload)
        parse_res = await ac.post(f"/api/v1/resumes/{resume_id}/parse", headers=headers)
        assert parse_res.status_code == 200
        parsed_data = parse_res.json()
        assert parsed_data["parsed_status"] == "parsed"
        assert parsed_data["parsed_data"] is not None
        assert any("Python" in s for s in parsed_data["parsed_data"].get("skills", []))

        # Advance step to 3
        await ac.put("/api/v1/onboarding/step", headers=headers, json={"step": 3})

        # =====================================================================
        # 4. ONBOARDING STEP 3 — Personalize AI Copilot
        # =====================================================================
        personalize_payload = {
            "focus_opportunity_matching": True,
            "focus_resume_tailoring": True,
            "focus_deadline_tracking": True,
            "update_frequency": "daily",
            "additional_notes": "Interested in agentic systems and distributed backend architectures.",
        }
        step3_res = await ac.put("/api/v1/onboarding/personalization", headers=headers, json=personalize_payload)
        assert step3_res.status_code == 200
        assert step3_res.json()["onboarding_step"] == 4

        # =====================================================================
        # 5. ONBOARDING STEP 4 — Complete Setup
        # =====================================================================
        complete_res = await ac.post("/api/v1/onboarding/complete", headers=headers)
        assert complete_res.status_code == 200
        assert complete_res.json()["onboarding_completed"] is True
        assert complete_res.json()["onboarding_step"] == 4

        # =====================================================================
        # 6. DASHBOARD INITIAL STATE (Zero Fake Data)
        # =====================================================================
        dash_initial = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert dash_initial.status_code == 200
        initial_summary = dash_initial.json()
        assert initial_summary["metrics"]["jobs_applied"] == 0
        assert initial_summary["metrics"]["replies_received"] == 0
        assert initial_summary["metrics"]["offers_received"] == 0
        assert len(initial_summary["recent_activity"]) == 0
        assert len(initial_summary["upcoming_reminders"]) == 0

        # =====================================================================
        # 7. FIND NEW POSITIONS — Grounded Hybrid Matching & Mathematical Integrity
        # =====================================================================
        refresh_res = await ac.post("/api/v1/jobs/matches/refresh", headers=headers)
        assert refresh_res.status_code == 200
        matches_res = await ac.get("/api/v1/jobs/matches?limit=20", headers=headers)
        assert matches_res.status_code == 200
        matches_data = matches_res.json()
        assert matches_data["total"] > 0
        items = matches_data["items"]

        # Verify mathematical scoring integrity: Final Match = round(0.70 * sim + 0.30 * pref)
        for item in items[:5]:
            sim = item["similarity_score"]
            pref = item["preference_score"]
            final = item["final_score"]
            assert 0.0 <= sim <= 100.0
            assert 0.0 <= pref <= 100.0
            assert 0.0 <= final <= 100.0
            expected = float(round(0.70 * sim + 0.30 * pref))
            assert abs(final - expected) <= 1.0, f"Math mismatch: {sim}*0.7 + {pref}*0.3 != {final}"

        # Select top match
        selected_match = items[0]
        selected_job = selected_match["job"]
        assert selected_job["id"] is not None
        assert selected_job["company"] is not None
        assert selected_job["role_title"] is not None
        source_job_id = selected_job["id"]

        # Verify single job detail endpoint returns canonical data
        job_detail_res = await ac.get(f"/api/v1/jobs/{source_job_id}", headers=headers)
        assert job_detail_res.status_code == 200
        job_detail = job_detail_res.json()
        assert job_detail["company"] == selected_job["company"]
        assert job_detail["role_title"] == selected_job["role_title"]

        # =====================================================================
        # 8. JD ANALYZER — Full Canonical Handoff & Requirement Grounding
        # =====================================================================
        analyze_payload = {
            "job_description": selected_job["description"],
            "source_job_id": source_job_id,
        }
        analyze_res = await ac.post("/api/v1/jd/analyze", headers=headers, json=analyze_payload)
        assert analyze_res.status_code == 200
        analysis_data = analyze_res.json()
        assert "match_analysis" in analysis_data
        match_analysis = analysis_data["match_analysis"]
        assert "description_quality" in match_analysis
        assert "description_source" in match_analysis
        assert "analysis_quality" in match_analysis
        if "tailoring" in analysis_data and analysis_data["tailoring"]:
            tailoring = analysis_data["tailoring"]
            assert "targeted_summary" in tailoring

        # =====================================================================
        # 9. APPLY FLOW — Application Intent & Duplicate Protection
        # =====================================================================
        apply_payload = {
            "company": selected_job["company"],
            "role": selected_job["role_title"],
            "location": selected_job["location"] or "Remote",
            "application_url": selected_job["application_url"] or "https://careers.example.com/apply",
            "source": selected_job["source"] or "Job Matching",
            "source_job_id": str(source_job_id),
            "job_description": selected_job["description"],
        }

        # First Apply click -> creates application_started
        start_res1 = await ac.post("/api/v1/applications/start", headers=headers, json=apply_payload)
        assert start_res1.status_code == 200
        app_record = start_res1.json()
        app_id = app_record["id"]
        assert app_record["tracking_state"] == TrackingState.APPLICATION_STARTED.value
        assert app_record["applied_at"] is None

        # Duplicate click -> must NOT create a new record, returns existing
        start_res2 = await ac.post("/api/v1/applications/start", headers=headers, json=apply_payload)
        assert start_res2.status_code == 200
        assert start_res2.json()["id"] == app_id

        # Verify Dashboard is NOT inflated by pending intent
        dash_mid = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert dash_mid.json()["metrics"]["jobs_applied"] == 0

        # "Not yet" simulation -> remains application_started
        not_yet_res = await ac.post(f"/api/v1/applications/{app_id}/not-yet", headers=headers)
        assert not_yet_res.status_code == 200
        assert not_yet_res.json()["tracking_state"] == TrackingState.APPLICATION_STARTED.value

        # Confirm Applied -> transitions to applied with applied_at
        confirm_res = await ac.post(f"/api/v1/applications/{app_id}/confirm-applied", headers=headers)
        assert confirm_res.status_code == 200
        confirmed_data = confirm_res.json()
        assert confirmed_data["tracking_state"] == TrackingState.APPLIED.value
        assert confirmed_data["status"] == "applied"
        assert confirmed_data["applied_at"] is not None

        # =====================================================================
        # 10. TRACK JOBS & STATUS TRANSITIONS
        # =====================================================================
        apps_list = await ac.get("/api/v1/applications", headers=headers)
        assert apps_list.status_code == 200
        apps_items = apps_list.json()
        assert len(apps_items) == 1
        assert apps_items[0]["id"] == app_id
        assert apps_items[0]["status"] == "applied"

        # Drag: Applied -> OA
        patch_oa = await ac.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "oa"})
        assert patch_oa.status_code == 200
        assert patch_oa.json()["status"] == "oa"

        # Check Dashboard: OA counts as a reply received
        dash_oa = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert dash_oa.json()["metrics"]["jobs_applied"] == 1
        assert dash_oa.json()["metrics"]["replies_received"] == 1
        assert dash_oa.json()["metrics"]["offers_received"] == 0

        # Drag: OA -> Interview
        patch_int = await ac.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "interview"})
        assert patch_int.status_code == 200
        assert patch_int.json()["status"] == "interview"

        # Drag: Interview -> Offer
        patch_off = await ac.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "offer"})
        assert patch_off.status_code == 200
        assert patch_off.json()["status"] == "offer"

        # Check Dashboard: Offer counts as an offer received and reply received
        dash_offer = await ac.get("/api/v1/dashboard/summary", headers=headers)
        assert dash_offer.json()["metrics"]["jobs_applied"] == 1
        assert dash_offer.json()["metrics"]["replies_received"] == 1
        assert dash_offer.json()["metrics"]["offers_received"] == 1

        # Reject invalid status (e.g. "replied")
        patch_invalid = await ac.patch(f"/api/v1/applications/{app_id}", headers=headers, json={"status": "replied"})
        assert patch_invalid.status_code == 422

        # =====================================================================
        # 11. ASK APTLY — Grounded Assistant Queries
        # =====================================================================
        # Query 1: Applications
        q1_res = await ac.post(
            "/api/v1/assistant/query",
            headers=headers,
            json={"message": "What jobs have I applied to?"},
        )
        assert q1_res.status_code == 200
        q1_data = q1_res.json()
        assert q1_data["intent"] == "applications"
        assert len(q1_data["answer"]) > 10

        # Query 2: Skills
        q2_res = await ac.post(
            "/api/v1/assistant/query",
            headers=headers,
            json={"message": "Does my resume mention Python?"},
        )
        assert q2_res.status_code == 200
        q2_data = q2_res.json()
        assert q2_data["intent"] == "resume"
        assert len(q2_data["answer"]) > 10

        # =====================================================================
        # 12. STRICT USER ISOLATION
        # =====================================================================
        user_b, token_b = await create_golden_user("user_b_isolation@example.com", "User B")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B cannot see User A's applications
        apps_b = await ac.get("/api/v1/applications", headers=headers_b)
        assert apps_b.status_code == 200
        assert len(apps_b.json()) == 0

        # User B cannot access User A's application by ID (404)
        get_other_app = await ac.get(f"/api/v1/applications/{app_id}", headers=headers_b)
        assert get_other_app.status_code == 404

        # User B's dashboard shows 0
        dash_b = await ac.get("/api/v1/dashboard/summary", headers=headers_b)
        assert dash_b.json()["metrics"]["jobs_applied"] == 0
