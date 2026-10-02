"""Personalized Job Retrieval and Hybrid Ranking Service.

Combines ChromaDB vector semantic similarity (70%) with user onboarding preferences (30%)
into a deterministic, grounded match score with factual explanations.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job_match import DailyMatch, JobListing
from app.models.preference import UserPreference
from app.models.resume import Resume
from app.services.job_sources import BaseJobSource, get_job_source
from app.services.llm_service import evaluate_location_match, llm_service
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


def normalize_url(url: Optional[str]) -> str:
    """Normalize application URL for deduplication."""
    if not url:
        return ""
    clean = re.sub(r"^https?://(?:www\.)?", "", url.strip(), flags=re.IGNORECASE)
    clean = clean.split("?")[0].split("#")[0].rstrip("/").lower()
    return clean


def normalize_text(text: Optional[str]) -> str:
    """Normalize text (lowercase, collapse whitespace) for deduplication."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


class JobMatcherService:
    """Service for job ingestion, embedding management, and hybrid candidate matching."""

    def __init__(self, vector_weight: float = 0.70, preference_weight: float = 0.30):
        self.vector_weight = vector_weight
        self.preference_weight = preference_weight

    async def ingest_and_embed_listings(
        self,
        db: AsyncSession,
        source: Optional[BaseJobSource] = None,
    ) -> int:
        """Fetch listings from provider, deduplicate/update in PostgreSQL, and cache embeddings in ChromaDB."""
        provider = source or get_job_source()
        raw_jobs = await provider.fetch_jobs()

        added_or_updated = 0
        now = datetime.now(timezone.utc)

        for item in raw_jobs:
            # Multi-tier deduplication
            job: Optional[JobListing] = None

            # Priority 1: source + external_id (when external_id is present)
            if item.external_id:
                stmt_ext = select(JobListing).where(
                    JobListing.source == item.source,
                    JobListing.external_id == item.external_id,
                )
                res_ext = await db.execute(stmt_ext)
                job = res_ext.scalar_one_or_none()

            # Fallback 2: normalized application_url (when url is present)
            if not job and item.application_url:
                norm_app_url = normalize_url(item.application_url)
                if norm_app_url:
                    stmt_all = select(JobListing).where(JobListing.application_url.isnot(None))
                    res_all = await db.execute(stmt_all)
                    for existing in res_all.scalars().all():
                        if normalize_url(existing.application_url) == norm_app_url:
                            job = existing
                            break

            # Fallback 3: company + normalized role + location
            if not job:
                norm_company = normalize_text(item.company)
                norm_role = normalize_text(item.role_title)
                norm_loc = normalize_text(item.location)

                stmt_cand = select(JobListing).where(func.lower(JobListing.company) == norm_company)
                res_cand = await db.execute(stmt_cand)
                for cand in res_cand.scalars().all():
                    if (
                        normalize_text(cand.role_title) == norm_role
                        and normalize_text(cand.location) == norm_loc
                    ):
                        job = cand
                        break

            if not job:
                # Insert new job listing
                job = JobListing(
                    external_id=item.external_id,
                    source=item.source,
                    company=item.company,
                    role_title=item.role_title,
                    location=item.location,
                    employment_type=item.employment_type,
                    description=item.description,
                    application_url=item.application_url,
                    deadline=item.deadline,
                    compensation=item.compensation,
                    posted_at=item.posted_at or now,
                    embedding_status="pending",
                    is_active=True,
                    fetched_at=now,
                    last_seen_at=now,
                    created_at=now,
                    updated_at=now,
                )
                db.add(job)
                await db.flush()
                await db.refresh(job)

                # Store embedding for new job
                vector_store.store_job_embedding(
                    job_id=job.id,
                    company=job.company,
                    role_title=job.role_title,
                    description=job.description,
                    source=job.source,
                )
                job.embedding_status = "embedded"
                job.updated_at = now
            else:
                # Check if description or role changed before updating
                content_changed = (
                    job.description.strip() != item.description.strip()
                    or job.role_title.strip() != item.role_title.strip()
                )

                job.company = item.company
                job.role_title = item.role_title
                job.location = item.location
                job.employment_type = item.employment_type
                job.description = item.description
                if item.application_url:
                    job.application_url = item.application_url
                if item.deadline:
                    job.deadline = item.deadline
                if item.compensation:
                    job.compensation = item.compensation
                if item.posted_at:
                    job.posted_at = item.posted_at
                job.is_active = True
                job.last_seen_at = now
                job.updated_at = now

                # Re-embed ONLY when description or relevant text changed
                if content_changed or job.embedding_status != "embedded":
                    vector_store.store_job_embedding(
                        job_id=job.id,
                        company=job.company,
                        role_title=job.role_title,
                        description=job.description,
                        source=job.source,
                    )
                    job.embedding_status = "embedded"

            added_or_updated += 1

        # Stale threshold: mark inactive if not seen in 14 days (graceful lifecycle)
        stale_cutoff = now - timedelta(days=14)
        stmt_stale = (
            select(JobListing)
            .where(JobListing.is_active == True, JobListing.last_seen_at < stale_cutoff)
        )
        res_stale = await db.execute(stmt_stale)
        for stale_job in res_stale.scalars().all():
            stale_job.is_active = False
            stale_job.updated_at = now

        await db.commit()
        logger.info("Ingested and verified embeddings for %d job listings", added_or_updated)
        return added_or_updated

    def calculate_vector_score(self, candidate_text: str, job: JobListing) -> float:
        """Compute cosine similarity between candidate resume profile and job listing text."""
        if not candidate_text:
            return 0.50

        job_text = f"{job.role_title} at {job.company}. {job.description}"
        return vector_store.compute_cosine_similarity(candidate_text, job_text)

    def calculate_preference_score(
        self,
        user_pref: Optional[UserPreference],
        user_skills: List[str],
        job: JobListing,
    ) -> Tuple[float, List[str]]:
        """Calculate deterministic preference fit based on onboarding preferences and verified skills."""
        reasons: list[str] = []
        scores: list[float] = []

        # 1. Target Role Alignment (Weight ~40%)
        role_score = 0.5
        if user_pref and user_pref.preferred_roles:
            job_title_lower = job.role_title.lower()
            matched_role = None
            for r in user_pref.preferred_roles:
                if r.lower() in job_title_lower or any(word in job_title_lower for word in r.lower().split()):
                    matched_role = r
                    break

            if matched_role:
                role_score = 1.0
                reasons.append(f"Matches your target role: {matched_role}")
            else:
                role_score = 0.4
        scores.append(role_score * 0.40)

        # 2. Opportunity Type Fit (Weight ~25%)
        opp_score = 0.6
        if user_pref and user_pref.opportunity_type:
            pref_opp = user_pref.opportunity_type.lower().replace("-", "_")
            job_opp = (job.employment_type or "").lower().replace("-", "_")
            if pref_opp == job_opp or (pref_opp == "full_time" and "full" in job_opp):
                opp_score = 1.0
                reasons.append(f"Aligned with your {job.employment_type.replace('_', ' ').title()} preference")
            elif "intern" in pref_opp and "intern" in job_opp:
                opp_score = 1.0
                reasons.append("Aligned with your Internship preference")
            else:
                opp_score = 0.3
        scores.append(opp_score * 0.25)

        # 3. Location / Work Mode Fit (Weight ~15%) - strictly preserving granularity
        pref_loc = user_pref.preferred_location if user_pref else None
        loc_score, loc_reason, loc_scope = evaluate_location_match(pref_loc, job.location)
        if loc_reason:
            reasons.append(loc_reason)
        scores.append(loc_score * 0.15)

        # 4. Verified Skills Overlap (Weight ~20%)
        skill_score = 0.5
        if user_skills:
            matched_skills = []
            job_desc_lower = job.description.lower()
            for s in user_skills:
                clean_s = s.strip().lower()
                if clean_s and re.search(r"\b" + re.escape(clean_s) + r"\b", job_desc_lower):
                    matched_skills.append(s)

            if matched_skills:
                skill_score = min(1.0, 0.4 + (len(matched_skills) * 0.2))
                reasons.append(f"Skills matched: {', '.join(matched_skills[:3])}")
            else:
                skill_score = 0.3
        scores.append(skill_score * 0.20)

        total_pref_score = sum(scores)
        return total_pref_score, reasons

    async def rank_jobs_for_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[DailyMatch]:
        """Rank all active job listings for the candidate using the hybrid model and persist DailyMatch."""
        # 1. Fetch user's latest parsed resume
        stmt_resume = (
            select(Resume)
            .where(Resume.user_id == user_id, Resume.parsed_status == "parsed")
            .order_by(Resume.created_at.desc())
        )
        res_resume = await db.execute(stmt_resume)
        resume = res_resume.scalars().first()

        if not resume:
            # Auto-parse fallback if resume was uploaded but /parse was not called
            stmt_uploaded = (
                select(Resume)
                .where(Resume.user_id == user_id)
                .order_by(Resume.created_at.desc())
            )
            res_uploaded = await db.execute(stmt_uploaded)
            uploaded_res = res_uploaded.scalars().first()
            if uploaded_res and uploaded_res.file_path:
                from pathlib import Path
                if Path(uploaded_res.file_path).exists():
                    try:
                        from app.services.resume_parser import extract_raw_text, resume_parser
                        raw_text = extract_raw_text(uploaded_res.file_path)
                        if raw_text.strip():
                            parsed_dict = resume_parser.parse(raw_text)
                            vector_store.store_resume_chunks(
                                resume_id=uploaded_res.id,
                                user_id=user_id,
                                parsed_data=parsed_dict,
                                raw_text=raw_text,
                            )
                            uploaded_res.extracted_text = raw_text
                            uploaded_res.parsed_data = parsed_dict
                            uploaded_res.parsed_status = "parsed"
                            uploaded_res.parsed_at = datetime.now(timezone.utc)
                            await db.flush()
                            resume = uploaded_res
                    except Exception as parse_err:
                        logger.warning("Auto-parsing resume on job matching failed: %s", parse_err)

        candidate_text = ""
        user_skills: list[str] = []
        if resume and resume.parsed_data:
            parsed = resume.parsed_data
            user_skills = parsed.get("skills", [])
            skills_str = ", ".join(user_skills)
            exp_str = " ".join(str(e) for e in parsed.get("experience", []))
            candidate_text = f"Candidate Profile: Skills: {skills_str}. Experience: {exp_str}"
        elif resume and resume.extracted_text:
            candidate_text = resume.extracted_text[:2000]

        # 2. Fetch user's onboarding preferences
        stmt_pref = select(UserPreference).where(UserPreference.user_id == user_id)
        res_pref = await db.execute(stmt_pref)
        user_pref = res_pref.scalar_one_or_none()

        # 3. Fetch active listings
        stmt_jobs = select(JobListing).where(JobListing.is_active == True).order_by(JobListing.created_at.desc())
        res_jobs = await db.execute(stmt_jobs)
        jobs = res_jobs.scalars().all()

        if not jobs:
            # If no listings exist, ingest default listings
            await self.ingest_and_embed_listings(db)
            res_jobs = await db.execute(stmt_jobs)
            jobs = res_jobs.scalars().all()

        # 4. Score each job listing
        now = datetime.now(timezone.utc)
        matches: list[DailyMatch] = []

        for job in jobs:
            # Vector cosine similarity (0–100 scale)
            sim_score = self.calculate_vector_score(candidate_text, job)
            sim_score_100 = float(round(sim_score * 100.0, 1))

            # Preference fit & factual explanation reasons (0–100 scale)
            pref_score, reasons = self.calculate_preference_score(user_pref, user_skills, job)
            pref_score_100 = float(round(pref_score * 100.0, 1))

            # Combined weighted score (0–100 scale strictly reflecting configured weights)
            raw_final = (self.vector_weight * sim_score_100 + self.preference_weight * pref_score_100)
            final_score = float(round(max(0.0, min(100.0, raw_final))))

            # Check if match already exists for this user and job
            stmt_match = select(DailyMatch).where(
                DailyMatch.user_id == user_id,
                DailyMatch.job_listing_id == job.id,
            )
            res_m = await db.execute(stmt_match)
            match_record = res_m.scalar_one_or_none()

            if match_record:
                # Update scores while preserving saved/dismissed flags
                match_record.similarity_score = sim_score_100
                match_record.preference_score = pref_score_100
                match_record.final_score = final_score
                match_record.match_reasons = reasons
                match_record.matched_at = now
            else:
                match_record = DailyMatch(
                    user_id=user_id,
                    job_listing_id=job.id,
                    similarity_score=sim_score_100,
                    preference_score=pref_score_100,
                    final_score=final_score,
                    match_reasons=reasons,
                    matched_at=now,
                    dismissed=False,
                    saved=False,
                )
                db.add(match_record)

            matches.append(match_record)

        await db.commit()

        # Return sorted by final_score DESC
        matches.sort(key=lambda m: m.final_score, reverse=True)

        # Optional grounded Groq explanation for top shortlist (anti-hallucination)
        if settings.GROQ_API_KEY and matches:
            pref_dict = {
                "preferred_roles": user_pref.preferred_roles if user_pref else [],
                "preferred_location": user_pref.preferred_location if user_pref else "",
            }
            for m in matches[:3]:
                job_obj = next((j for j in jobs if j.id == m.job_listing_id), None)
                if job_obj:
                    try:
                        groq_exp = await llm_service.generate_grounded_match_explanation(
                            role_title=job_obj.role_title,
                            company=job_obj.company,
                            description=job_obj.description,
                            user_skills=user_skills,
                            user_preferences=pref_dict,
                            job_location=job_obj.location,
                        )
                        if groq_exp:
                            # Prepend grounded explanation to reasons list
                            m.match_reasons = [groq_exp] + [r for r in m.match_reasons if r != groq_exp][:3]
                    except Exception as e:
                        logger.debug("Optional Groq match explanation skipped: %s", e)

        return matches


# Singleton instance
job_matcher = JobMatcherService()
