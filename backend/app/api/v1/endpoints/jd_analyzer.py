"""JD Analyzer and Resume Tailoring Endpoints."""
from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, List, Optional, Union
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import UserProfile, _get_current_user
from app.db.session import get_db
from app.models.job_match import JobListing
from app.models.resume import Resume
from app.services.llm_service import llm_service
from app.services.resume_parser import extract_raw_text, resume_parser
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jd", tags=["JD Analyzer"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AnalyzeJDRequest(BaseModel):
    job_description: Optional[str] = Field(
        default=None,
        max_length=35000,
        description="Full raw job description text (up to 35,000 characters)",
    )
    source_job_id: Optional[Union[uuid.UUID, str]] = Field(
        default=None,
        description="Optional canonical JobListing ID in PostgreSQL",
    )
    company: Optional[str] = Field(
        default=None,
        description="Optional authoritative company name passed from job provider",
    )
    role_title: Optional[str] = Field(
        default=None,
        description="Optional authoritative role title passed from job provider",
    )


class JobDetailsResponse(BaseModel):
    company: str
    role_title: str
    role_summary: Optional[str] = ""
    seniority: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    deadline: Optional[str] = None
    compensation: Optional[str] = None
    graduation_year_eligibility: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    required_experience: List[str] = []
    min_years_experience: Optional[float] = None
    experience_requirements: Optional[str] = None
    education_requirements: List[str] = []
    domain_requirements: List[str] = []
    tools_and_technologies: List[str] = []
    soft_skills: List[str] = []
    location_requirements: List[str] = []
    other_requirements: List[str] = []
    responsibilities: List[str] = []
    qualifications: List[str] = []
    keywords: List[str] = []
    analysis_quality: str = "sufficient"
    description_quality: str = "FULL"  # "FULL" | "COMPLETE" | "PARTIAL" | "INSUFFICIENT"
    description_source: str = "USER_PASTED"  # "ADZUNA_FULL" | "ADZUNA_PREVIEW" | "USER_PASTED" | "OTHER_SUPPORTED_SOURCE"
    description_length: int = 0
    provider_description_length: Optional[int] = None
    analysis_description_length: int = 0
    is_truncated: bool = False
    quality_warning: Optional[str] = None
    internal_grade: Optional[str] = None
    source: Optional[str] = None
    application_url: Optional[str] = None
    source_job_id: Optional[str] = None


class MatchAnalysisResponse(BaseModel):
    overall_match_score: Optional[int] = None
    analysis_quality: str = "COMPLETE"  # "COMPLETE" | "PARTIAL" | "INSUFFICIENT_REQUIREMENTS"
    description_quality: str = "FULL"  # "FULL" | "COMPLETE" | "PARTIAL" | "INSUFFICIENT"
    description_source: str = "USER_PASTED"
    description_length: int = 0
    provider_description_length: Optional[int] = None
    analysis_description_length: int = 0
    is_truncated: bool = False
    insufficient_requirements: bool = False
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    relevant_projects: List[str] = []
    relevant_experience: List[str] = []
    strengths: List[str] = []
    gaps: List[str] = []
    technical_gaps: List[Dict[str, Any]] = []
    unverified_traits: List[Dict[str, Any]] = []
    eligibility_review: List[Dict[str, Any]] = []
    match_breakdown: Optional[Dict[str, Any]] = None
    seniority_alignment: Optional[Dict[str, Any]] = None
    verified_matches: List[Dict[str, Any]] = []
    related_experience: List[Dict[str, Any]] = []
    gaps_breakdown: List[Dict[str, Any]] = []
    verified_count: int = 0
    related_count: int = 0
    gap_count: int = 0
    gaps_summary_message: Optional[str] = None
    normalized_requirements: List[Dict[str, Any]] = []


def resolve_authoritative_jd(
    listing_record: Optional[JobListing],
    frontend_jd: Optional[str],
) -> Tuple[str, str, Optional[int]]:
    """
    Deterministic source selection (Sections 8, 9, 13):
    Returns (raw_jd, description_source, provider_len).
    - If user explicitly edited/pasted a longer JD than provider: USER_PASTED
    - Else if listing_record.description exists:
      - If preview (<= 650 chars and ending mid-sentence/ellipsis/500-char):
        ADZUNA_PREVIEW (if adzuna) or OTHER_SUPPORTED_SOURCE
      - Else:
        ADZUNA_FULL (if adzuna) or OTHER_SUPPORTED_SOURCE
    - Else: USER_PASTED
    Never downgrade a longer manually supplied JD to a provider preview.
    """
    user_text = (frontend_jd or "").strip()
    provider_text = (listing_record.description or "").strip() if listing_record else ""
    provider_len = len(provider_text) if listing_record else None
    provider_name = (listing_record.source or "adzuna").strip().lower() if listing_record else ""
    is_adzuna = (provider_name == "adzuna")

    if listing_record:
        # User manual override:
        # If user explicitly supplied text longer than provider_text
        if user_text and len(user_text) > len(provider_text) and user_text != provider_text:
            return user_text, "USER_PASTED", provider_len
        elif provider_text:
            is_preview = (
                len(provider_text) <= 650
                and (
                    provider_text.endswith(("...", "…", "\ufffd"))
                    or len(provider_text) == 500
                    or provider_text[-1] not in (".", "!", "?", '"', "'", "\n")
                )
            )
            if is_preview:
                source_tag = "ADZUNA_PREVIEW" if is_adzuna else "OTHER_SUPPORTED_SOURCE"
            else:
                source_tag = "ADZUNA_FULL" if is_adzuna else "OTHER_SUPPORTED_SOURCE"
            return provider_text, source_tag, provider_len
        elif user_text:
            return user_text, "USER_PASTED", provider_len
        else:
            source_tag = "ADZUNA_FULL" if is_adzuna else "OTHER_SUPPORTED_SOURCE"
            return provider_text, source_tag, provider_len
    else:
        return user_text, "USER_PASTED", provider_len


class AnalyzeJDResponse(BaseModel):
    job_details: JobDetailsResponse
    match_analysis: MatchAnalysisResponse
    resume_id: uuid.UUID
    resume_filename: str


class TailorResumeRequest(BaseModel):
    job_description: Optional[str] = Field(default=None, max_length=35000)
    source_job_id: Optional[Union[uuid.UUID, str]] = Field(default=None)
    resume_id: uuid.UUID
    company: Optional[str] = Field(default=None)
    role_title: Optional[str] = Field(default=None)


class TailorResumeResponse(BaseModel):
    tailored_sections: Dict[str, Any]
    resume_id: uuid.UUID


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeJDResponse)
async def analyze_job_description(
    payload: AnalyzeJDRequest,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalyzeJDResponse:
    """Analyze a job description and compare it against the user's parsed resume."""
    # 1. Fetch user's parsed resume
    stmt = (
        select(Resume)
        .where(
            Resume.user_id == current_user.id,
            Resume.parsed_status == "parsed",
        )
        .order_by(Resume.created_at.desc())
    )
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if not resume:
        # Check if user has an uploaded resume not yet marked as parsed
        stmt_uploaded = (
            select(Resume)
            .where(Resume.user_id == current_user.id)
            .order_by(Resume.created_at.desc())
        )
        res_uploaded = await db.execute(stmt_uploaded)
        any_resume = res_uploaded.scalars().first()
        if any_resume and any_resume.file_path:
            from pathlib import Path
            if Path(any_resume.file_path).exists():
                try:
                    raw_text = extract_raw_text(any_resume.file_path)
                    if raw_text.strip():
                        parsed_dict = resume_parser.parse(raw_text)
                        vector_store.store_resume_chunks(
                            resume_id=any_resume.id,
                            user_id=current_user.id,
                            parsed_data=parsed_dict,
                            raw_text=raw_text,
                        )
                        any_resume.extracted_text = raw_text
                        any_resume.parsed_data = parsed_dict
                        any_resume.parsed_status = "parsed"
                        any_resume.parsed_at = datetime.now(timezone.utc)
                        await db.flush()
                        resume = any_resume
                except Exception as parse_err:
                    logger.warning("Auto-parsing resume on analyze failed: %s", parse_err)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parsed resume found. Please upload and parse your resume in Step 2 before analyzing job descriptions.",
        )

    # 2. Canonical DB JobListing handoff (Phase 22 & Phase 2)
    listing_record: Optional[JobListing] = None
    if payload.source_job_id:
        job_id_str = str(payload.source_job_id).strip()
        try:
            job_uuid = uuid.UUID(job_id_str)
            stmt_job = select(JobListing).where(JobListing.id == job_uuid)
            res_job = await db.execute(stmt_job)
            listing_record = res_job.scalar_one_or_none()
        except ValueError:
            try:
                stmt_job = select(JobListing).where(JobListing.external_id == job_id_str)
                res_job = await db.execute(stmt_job)
                listing_record = res_job.scalar_one_or_none()
            except Exception as e_ext:
                logger.warning("Could not query JobListing by external_id %s: %s", job_id_str, e_ext)
        except Exception as exc:
            logger.warning("Could not resolve source_job_id %s: %s", payload.source_job_id, exc)

    raw_jd, description_source, provider_len = resolve_authoritative_jd(
        listing_record, payload.job_description
    )

    if len(raw_jd) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description must contain at least 20 characters",
        )

    try:
        # 3. Extract structured details from the JD (with preprocessing & cleaning)
        jd_details = await llm_service.analyze_job_description(raw_jd)

        # Description quality assessment & metadata (Section 10)
        is_partial_source = (description_source in ("PROVIDER_PARTIAL", "ADZUNA_PREVIEW"))
        if jd_details.get("analysis_quality") == "insufficient_job_description":
            desc_quality = "INSUFFICIENT"
            is_trunc = False
        elif is_partial_source or jd_details.get("description_quality") == "PARTIAL":
            desc_quality = "PARTIAL"
            is_trunc = True
            jd_details["quality_warning"] = (
                "Your job provider supplied a shortened description. Paste the full job description for the most reliable analysis."
            )
        else:
            desc_quality = "FULL"
            is_trunc = False

        jd_details["description_source"] = description_source
        jd_details["description_quality"] = desc_quality
        jd_details["description_length"] = len(raw_jd)
        jd_details["provider_description_length"] = provider_len
        jd_details["analysis_description_length"] = len(raw_jd)
        jd_details["is_truncated"] = is_trunc

        # Preserve canonical provider attributes: Authoritative provider metadata takes precedence over failed/missing extraction
        if listing_record:
            if listing_record.company:
                jd_details["company"] = listing_record.company
            if listing_record.role_title:
                jd_details["role_title"] = listing_record.role_title
            if listing_record.location:
                jd_details["location"] = listing_record.location
            if listing_record.employment_type:
                jd_details["employment_type"] = listing_record.employment_type
            if listing_record.application_url:
                jd_details["application_url"] = listing_record.application_url
            if listing_record.source:
                jd_details["source"] = listing_record.source
            jd_details["source_job_id"] = str(listing_record.id)
        elif payload.company and (not jd_details.get("company") or jd_details.get("company") in ("Target Company", "Unknown Company", "Company Name", "Unknown")):
            jd_details["company"] = payload.company

        if payload.role_title and (not jd_details.get("role_title") or jd_details.get("role_title") in ("Software Engineer", "Unknown Role", "Role Title")):
            jd_details["role_title"] = payload.role_title

        # 4. If JD is insufficient/malformed, return clean response with quality warning
        if jd_details.get("analysis_quality") == "insufficient_job_description":
            return AnalyzeJDResponse(
                job_details=JobDetailsResponse(**jd_details),
                match_analysis=MatchAnalysisResponse(
                    overall_match_score=None,
                    analysis_quality="INSUFFICIENT_REQUIREMENTS",
                    description_quality="INSUFFICIENT",
                    description_source=description_source,
                    description_length=len(raw_jd),
                    provider_description_length=provider_len,
                    analysis_description_length=len(raw_jd),
                    is_truncated=False,
                    insufficient_requirements=True,
                    matched_skills=[],
                    missing_skills=[],
                    relevant_projects=[],
                    relevant_experience=[],
                    strengths=[],
                    gaps=[jd_details.get("quality_warning") or "Insufficient job description."],
                    gaps_summary_message="We couldn't identify enough explicit requirements in this job description to evaluate skill fit reliably.",
                ),
                resume_id=resume.id,
                resume_filename=resume.file_name,
            )

        # 5. Retrieve relevant resume vector chunks from ChromaDB (with user isolation)
        relevant_chunks: list[dict[str, Any]] = []
        try:
            query_text = f"{jd_details.get('role_title', '')} {' '.join(jd_details.get('required_skills', []))}"
            chroma_res = vector_store.query_resume_vectors(
                user_id=current_user.id,
                query=query_text,
                n_results=5,
            )
            if chroma_res and "documents" in chroma_res and chroma_res["documents"]:
                docs = chroma_res["documents"][0]
                metas = chroma_res.get("metadatas", [[]])[0] if chroma_res.get("metadatas") else []
                for doc, meta in zip(docs, metas):
                    relevant_chunks.append({"text": doc, "metadata": meta})
        except Exception as exc:
            logger.warning("Vector retrieval error for JD matching: %s", exc)

        # 6. Deterministically compare JD against resume
        match_data = await llm_service.evaluate_resume_match(
            jd_data=jd_details,
            resume_data=resume.parsed_data or {},
            relevant_chunks=relevant_chunks,
        )

        return AnalyzeJDResponse(
            job_details=JobDetailsResponse(**jd_details),
            match_analysis=MatchAnalysisResponse(**match_data),
            resume_id=resume.id,
            resume_filename=resume.file_name,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("JD analysis error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Aptly couldn't analyze this job right now. Please try again.",
        )


@router.post("/tailor", response_model=TailorResumeResponse)
async def tailor_resume_for_job(
    payload: TailorResumeRequest,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TailorResumeResponse:
    """Generate structured section-by-section tailoring suggestions without overwriting the resume.

    Canonical requirement graph flows:
    JD -> structured extraction -> evaluate_resume_match -> canonical_requirements -> tailor_resume
    Tailoring is always downstream of the same requirement graph used for Candidate Fit.
    """
    # 1. Verify resume ownership
    stmt = select(Resume).where(
        Resume.id == payload.resume_id,
        Resume.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    if resume.parsed_status != "parsed" or not resume.parsed_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has not been successfully parsed yet",
        )

    # 2. Canonical DB JobListing handoff
    listing_record: Optional[JobListing] = None
    if payload.source_job_id:
        job_id_str = str(payload.source_job_id).strip()
        try:
            job_uuid = uuid.UUID(job_id_str)
            stmt_job = select(JobListing).where(JobListing.id == job_uuid)
            res_job = await db.execute(stmt_job)
            listing_record = res_job.scalar_one_or_none()
        except ValueError:
            try:
                stmt_job = select(JobListing).where(JobListing.external_id == job_id_str)
                res_job = await db.execute(stmt_job)
                listing_record = res_job.scalar_one_or_none()
            except Exception as e_ext:
                logger.warning("Could not query JobListing by external_id %s: %s", job_id_str, e_ext)
        except Exception as exc:
            logger.warning("Could not resolve source_job_id %s: %s", payload.source_job_id, exc)

    raw_jd, description_source, provider_len = resolve_authoritative_jd(
        listing_record, payload.job_description
    )

    if len(raw_jd) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description must contain at least 20 characters",
        )

    try:
        # 3. Extract JD structure
        jd_details = await llm_service.analyze_job_description(raw_jd)

        # Description quality assessment & metadata (Section 10)
        is_partial_source = (description_source in ("PROVIDER_PARTIAL", "ADZUNA_PREVIEW"))
        if jd_details.get("analysis_quality") == "insufficient_job_description":
            desc_quality = "INSUFFICIENT"
            is_trunc = False
        elif is_partial_source or jd_details.get("description_quality") == "PARTIAL":
            desc_quality = "PARTIAL"
            is_trunc = True
            jd_details["quality_warning"] = (
                "Your job provider supplied a shortened description. Paste the full job description for the most reliable analysis."
            )
        else:
            desc_quality = "FULL"
            is_trunc = False

        jd_details["description_source"] = description_source
        jd_details["description_quality"] = desc_quality
        jd_details["description_length"] = len(raw_jd)
        jd_details["provider_description_length"] = provider_len
        jd_details["analysis_description_length"] = len(raw_jd)
        jd_details["is_truncated"] = is_trunc

        if listing_record:
            if listing_record.company:
                jd_details["company"] = listing_record.company
            if listing_record.role_title:
                jd_details["role_title"] = listing_record.role_title
            if listing_record.location:
                jd_details["location"] = listing_record.location
            if listing_record.employment_type:
                jd_details["employment_type"] = listing_record.employment_type
            if listing_record.application_url:
                jd_details["application_url"] = listing_record.application_url
            if listing_record.source:
                jd_details["source"] = listing_record.source
            jd_details["source_job_id"] = str(listing_record.id)
        elif payload.company and (not jd_details.get("company") or jd_details.get("company") in ("Target Company", "Unknown Company", "Company Name", "Unknown")):
            jd_details["company"] = payload.company

        if payload.role_title and (not jd_details.get("role_title") or jd_details.get("role_title") in ("Software Engineer", "Unknown Role", "Role Title")):
            jd_details["role_title"] = payload.role_title

        # 4. Build canonical requirement graph (same as /analyze endpoint)
        match_data = await llm_service.evaluate_resume_match(
            jd_data=jd_details,
            resume_data=resume.parsed_data,
        )
        canonical_requirements: list[dict] = match_data.get("normalized_requirements", [])

        # 5. Tailor strictly from canonical requirement graph
        tailored = await llm_service.tailor_resume(
            jd_data=jd_details,
            resume_data=resume.parsed_data,
            canonical_requirements=canonical_requirements or None,
        )

        return TailorResumeResponse(
            tailored_sections=tailored,
            resume_id=resume.id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Resume tailoring error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Aptly couldn't analyze this job right now. Please try again.",
        )
