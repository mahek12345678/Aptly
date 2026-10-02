"""Groq LLM Service for Job Description Analysis and Resume Tailoring.

SINGLE SOURCE OF TRUTH PIPELINE:
1. Preprocesses and cleans raw JD via jd_preprocessor.py, extracting clean role title without internal grades.
2. Extracts structured JD attributes with strict Pydantic schemas.
3. Builds a unified NormalizedRequirement list for every requirement (required skill, preferred skill,
   experience, education, domain).
4. Reconciles component scores deterministically (Required Skills 40%, Preferred Skills 15%,
   Experience 25%, Role Alignment 20%). Score guardrails cap score if critical experience is missing.
5. All downstream counts, verified matches, gaps, copy, and target/learn items derive strictly
   from this single unified requirement list.
6. Anti-hallucination tailoring: summary uses conservative transferable language without claiming
   unverified seniority or leadership.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from groq import AsyncGroq
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import settings
from app.services.jd_preprocessor import PreprocessedJD, clean_job_description, clean_role_title
from app.services.skill_normalizer import (
    MatchStatus,
    NormalizedRequirement,
    build_unified_requirements,
    calculate_reconciled_scores,
    extract_structured_resume_evidence,
    is_valid_technical_skill,
    normalize_skill,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strict Validation Schemas
# ---------------------------------------------------------------------------


class ExtractedJDModel(BaseModel):
    company: Optional[str] = Field(default=None, description="Company name")
    role_title: Optional[str] = Field(default="Software Engineer", description="Role or job title")
    internal_grade: Optional[str] = Field(default=None, description="Internal job grade level if specified")
    role_summary: str = Field(default="", description="Factual 1-2 sentence summary of role")
    seniority: Optional[str] = Field(default=None, description="Seniority level (e.g. Senior, Lead, Mid, Entry, Intern)")
    employment_type: Optional[str] = "Full-time"
    location: Optional[str] = None
    deadline: Optional[str] = None
    compensation: Optional[str] = None
    graduation_year_eligibility: Optional[str] = None
    responsibilities: List[str] = []
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    required_experience: List[str] = []
    min_years_experience: Optional[float] = None
    education_requirements: List[str] = []
    domain_requirements: List[str] = []
    tools_and_technologies: List[str] = []
    soft_skills: List[str] = []
    location_requirements: List[str] = []
    other_requirements: List[str] = []
    qualifications: List[str] = []
    keywords: List[str] = []
    analysis_quality: str = "sufficient"
    quality_warning: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class MatchAnalysisModel(BaseModel):
    overall_match_score: Optional[int] = Field(default=None, ge=0, le=100)
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    verified_count: int = 0
    related_count: int = 0
    gap_count: int = 0
    gaps_summary_message: Optional[str] = None
    relevant_projects: List[str] = []
    relevant_experience: List[str] = []
    strengths: List[str] = []
    gaps: List[str] = []
    match_breakdown: Optional[Dict[str, Any]] = None
    seniority_alignment: Optional[Dict[str, Any]] = None
    verified_matches: List[Dict[str, Any]] = []
    related_experience: List[Dict[str, Any]] = []
    gaps_breakdown: List[Dict[str, Any]] = []
    normalized_requirements: List[Dict[str, Any]] = []

    model_config = ConfigDict(extra="ignore")


class TailoredSectionSummary(BaseModel):
    suggestion: str
    strategy: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TailoredSectionSkills(BaseModel):
    prioritized: List[str] = []
    secondary: List[str] = []
    target_gaps: List[str] = []
    strategy: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TailoredExperienceEntry(BaseModel):
    original_entry: str
    action_suggestion: str
    keywords_to_bold: List[str] = []

    model_config = ConfigDict(extra="ignore")


class TailoredProjectEntry(BaseModel):
    original_entry: str
    action_suggestion: str
    supports: List[str] = []
    related_evidence: List[str] = []
    does_not_establish: List[str] = []
    keywords_to_bold: List[str] = []
    project_id: Optional[str] = None
    project_title: Optional[str] = None
    project_bullets: List[str] = []

    model_config = ConfigDict(extra="ignore")


class TailoredResumeModel(BaseModel):
    summary: TailoredSectionSummary
    skills: TailoredSectionSkills
    experience: List[TailoredExperienceEntry] = []
    projects: List[TailoredProjectEntry] = []

    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# LLM Service Implementation
# ---------------------------------------------------------------------------


class LLMService:
    """Service wrapping Groq SDK for grounded JD analysis, deterministic matching, and resume tailoring."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY or settings.LLM_API_KEY
        self.model = model or settings.GROQ_MODEL or "openai/gpt-oss-120b"
        self._groq_client: Optional[AsyncGroq] = None

    @property
    def client(self) -> AsyncGroq:
        if self._groq_client is None:
            self._groq_client = AsyncGroq(api_key=self.api_key, timeout=25.0)
        return self._groq_client

    # ---------------------------------------------------------------------------
    # Public Methods
    # ---------------------------------------------------------------------------

    async def analyze_job_description(self, job_description: str) -> Dict[str, Any]:
        """Preprocess and extract structured details from a job description."""
        # 1. Clean and preprocess the JD
        prep = clean_job_description(job_description)

        # 2. Check quality confidence
        if prep.analysis_quality == "insufficient_job_description":
            return {
                "company": prep.detected_company or "Unknown Company",
                "role_title": prep.detected_role or "Role",
                "internal_grade": prep.internal_grade,
                "role_summary": "",
                "seniority": None,
                "employment_type": "Full-time",
                "location": None,
                "deadline": None,
                "compensation": None,
                "graduation_year_eligibility": None,
                "responsibilities": [],
                "required_skills": [],
                "preferred_skills": [],
                "required_experience": [],
                "min_years_experience": None,
                "education_requirements": [],
                "domain_requirements": [],
                "tools_and_technologies": [],
                "soft_skills": [],
                "location_requirements": [],
                "other_requirements": [],
                "qualifications": [],
                "keywords": [],
                "analysis_quality": "insufficient_job_description",
                "quality_warning": prep.quality_warning,
            }

        # 3. Extract structured details with Groq or deterministic fallback
        extracted: Optional[Dict[str, Any]] = None
        if self.api_key:
            try:
                extracted = await self._extract_with_groq(prep.cleaned_text)
            except Exception as exc:
                logger.warning("Groq JD extraction failed, utilizing grounded fallback: %s", exc)

        if not extracted:
            extracted = self._heuristic_extract_jd(prep)

        # 4. Clean role title and extract internal grade
        raw_role = extracted.get("role_title") or prep.detected_role or "Software Engineer"
        clean_title, detected_grade = clean_role_title(raw_role)
        if not detected_grade:
            _, detected_grade = clean_role_title(prep.cleaned_text[:600])
        if not detected_grade and prep.raw_text:
            _, detected_grade = clean_role_title(prep.raw_text[:600])

        extracted["role_title"] = clean_title or raw_role
        extracted["internal_grade"] = detected_grade or prep.internal_grade

        if prep.detected_company and (not extracted.get("company") or extracted.get("company") == "Target Company"):
            extracted["company"] = prep.detected_company

        extracted["required_skills"] = [normalize_skill(s) for s in extracted.get("required_skills", []) if s]
        extracted["preferred_skills"] = [normalize_skill(s) for s in extracted.get("preferred_skills", []) if s]
        extracted["analysis_quality"] = "sufficient"
        extracted["description_quality"] = getattr(prep, "description_quality", "FULL")
        extracted["quality_warning"] = prep.quality_warning
        if extracted.get("min_years_experience") is not None and extracted["min_years_experience"] <= 0:
            extracted["min_years_experience"] = None

        # Dev-mode diagnostic log (no secrets, no resume content)
        logger.debug(
            "JD extraction diagnostics | role=%r | company=%r | cleaned_chars=%d | "
            "required_skills=%d | preferred_skills=%d | required_experience=%d | "
            "min_years=%s | responsibilities=%d | education=%d",
            extracted.get("role_title"),
            extracted.get("company"),
            len(prep.cleaned_text),
            len(extracted.get("required_skills") or []),
            len(extracted.get("preferred_skills") or []),
            len(extracted.get("required_experience") or []),
            extracted.get("min_years_experience"),
            len(extracted.get("responsibilities") or []),
            len(extracted.get("education_requirements") or []),
        )

        return extracted

    async def extract_jd_details(self, job_description: str) -> Dict[str, Any]:
        """Alias for backward-compatibility."""
        return await self.analyze_job_description(job_description)

    async def evaluate_resume_match(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        relevant_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Compare JD against user's parsed resume deterministically with SINGLE SOURCE OF TRUTH."""
        # 1. Extract structured resume evidence mapped to canonical skills
        evidence_map = extract_structured_resume_evidence(resume_data)

        # 2. Candidate experience years and education verification
        cand_years, year_msg = self._estimate_candidate_years(resume_data)
        has_degree = bool(resume_data.get("education"))

        # Clean title if needed
        clean_title, detected_grade = clean_role_title(jd_data.get("role_title", "Software Engineer"))
        if clean_title:
            jd_data["role_title"] = clean_title
        if detected_grade and not jd_data.get("internal_grade"):
            jd_data["internal_grade"] = detected_grade

        # 3. SINGLE SOURCE OF TRUTH: Build unified requirements list (Requirement 1)
        requirements = build_unified_requirements(
            jd_data=jd_data,
            evidence_map=evidence_map,
            candidate_years=cand_years,
            candidate_degree_verified=has_degree,
        )

        # 4. Domain alignment
        domain_ratio = self._calculate_domain_alignment(jd_data, resume_data)

        # 5. Calculate Reconciled Scores (Requirements 2, 11, 12)
        is_partial = (jd_data.get("description_quality") == "PARTIAL")
        score, breakdown = calculate_reconciled_scores(
            requirements=requirements,
            domain_match_ratio=domain_ratio,
            candidate_years=cand_years,
            requested_years=jd_data.get("min_years_experience"),
            is_partial_jd=is_partial,
        )

        # 6. Partition strictly by match_status (Requirements 3, 4, 6)
        verified_items = [r for r in requirements if r.match_status == MatchStatus.VERIFIED.value]
        related_items = [r for r in requirements if r.match_status == MatchStatus.RELATED.value]
        missing_items = [r for r in requirements if r.match_status == MatchStatus.MISSING.value]

        verified_count = len(verified_items)
        related_count = len(related_items)
        gap_count = len(missing_items)

        # 7. Non-contradictory dynamic copy
        total_requirements = len(requirements)
        if total_requirements == 0:
            gaps_summary_message = (
                "We couldn't identify enough explicit requirements in this job description "
                "to evaluate skill fit reliably."
            )
        elif gap_count == 0:
            gaps_summary_message = "All evaluated requirements have verified or related evidence."
        else:
            gaps_summary_message = f"{gap_count} requirement{'s' if gap_count > 1 else ''} could not be verified from your resume."

        # 8. Grounded Seniority Alignment
        # ONLY use explicit min_years from the JD — never infer from role title
        min_years = jd_data.get("min_years_experience")
        if min_years:
            req_years_display = f"{int(min_years)}+ years"
        else:
            req_years_display = "Not specified"

        if cand_years is not None:
            is_senior_role = bool(min_years and min_years >= 4.0)
            has_seniority_gap = is_senior_role and (cand_years < min_years)
            gap_years = max(0, int((min_years or 5.0) - cand_years)) if has_seniority_gap else 0
            gap_display = f"~{gap_years}+ years" if has_seniority_gap else "None"
            status_display = f"EXPERIENCE GAP: {req_years_display} requested / Not verified in resume" if has_seniority_gap else "Seniority requirements aligned with verified background."
        else:
            has_seniority_gap = bool(min_years and min_years >= 4.0)
            gap_display = "N/A" if not min_years else f"{int(min_years)}+ years requested"
            status_display = f"EXPERIENCE GAP: {req_years_display} requested / Not determinable from resume" if min_years else "Experience requirements: Not specified in JD"

        seniority_alignment = {
            "seniority_requested": req_years_display,
            "candidate_seniority": year_msg,
            "gap": gap_display,
            "status": status_display,
            "is_gap": has_seniority_gap,
            "verified_professional_experience_years": cand_years,
        }

        # 9. Structured lists for UI display
        verified_matches = [
            {
                "requirement_id": r.requirement_id,
                "requirement": r.requirement,
                "canonical_requirement": r.canonical,
                "status": "VERIFIED_MATCH",
                "evidence": r.resume_evidence,
                "notes": r.notes,
                "source": r.source,
                "is_required": r.importance == "required",
            }
            for r in verified_items
        ]

        related_experience = [
            {
                "requirement_id": r.requirement_id,
                "requirement": r.requirement,
                "canonical_requirement": r.canonical,
                "status": "RELATED_EVIDENCE",
                "evidence": r.resume_evidence,
                "notes": r.notes,
                "source": r.source,
                "is_required": r.importance == "required",
            }
            for r in related_items
        ]

        gaps_breakdown = [
            {
                "requirement_id": r.requirement_id,
                "requirement": r.requirement,
                "canonical_requirement": r.canonical,
                "status": "NOT_FOUND",
                "source": r.source,
                "advice": r.notes,
                "is_required": r.importance == "required",
            }
            for r in missing_items
        ]

        matched_skills = [r.canonical for r in verified_items if r.category in ("required_skill", "preferred_skill")]
        missing_skills = [r.canonical for r in missing_items if r.category in ("required_skill", "preferred_skill")]

        # Grounded strengths and gaps
        strengths: List[str] = []
        gaps: List[str] = []

        for vm in verified_matches[:4]:
            notes = vm.get("notes") or ""
            if " — verified " in notes:
                strengths.append(f"✓ {notes}")
            elif vm.get("evidence"):
                strengths.append(f"✓ {vm['canonical_requirement']} — verified in resume: {vm['evidence'][0]}")
            else:
                strengths.append(f"✓ {vm['canonical_requirement']} — verified in resume.")

        for re_exp in related_experience[:2]:
            notes = re_exp.get("notes") or ""
            if notes.startswith("Related capability:"):
                strengths.append(f"~ {re_exp['canonical_requirement']} — {notes}")
            elif re_exp.get("evidence"):
                strengths.append(f"~ {re_exp['canonical_requirement']} — related transferable evidence: {re_exp['evidence'][0]}")
            else:
                strengths.append(f"~ {re_exp['canonical_requirement']} — related transferable evidence.")

        if has_seniority_gap:
            gaps.append(f"△ {seniority_alignment['status']}")

        for miss_item in gaps_breakdown[:4]:
            gaps.append(f"△ {miss_item['canonical_requirement']}: {miss_item['advice']}")

        relevant_projects: List[str] = []
        for p in resume_data.get("projects", [])[:3]:
            p_str = str(p).strip()
            relevant_projects.append(p_str[:120] + "..." if len(p_str) > 120 else p_str)

        relevant_exp_list: List[str] = []
        for e in resume_data.get("experience", [])[:3]:
            e_str = str(e).strip()
            relevant_exp_list.append(e_str[:120] + "..." if len(e_str) > 120 else e_str)

        # Handle INSUFFICIENT_REQUIREMENTS sentinel score (Phase 14: null score when insufficient requirements or partial JD)
        display_score = score if (score is not None and score >= 0) else None
        insufficient = (score is None or score == -1)

        match_result = {
            "overall_match_score": display_score,
            "analysis_quality": breakdown.get("analysis_quality", "COMPLETE"),
            "description_quality": jd_data.get("description_quality", "COMPLETE"),
            "description_source": jd_data.get("description_source", "USER_PASTED"),
            "description_length": jd_data.get("description_length", 0),
            "provider_description_length": jd_data.get("provider_description_length"),
            "analysis_description_length": jd_data.get("analysis_description_length", 0),
            "is_truncated": jd_data.get("is_truncated", False),
            "insufficient_requirements": insufficient,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "verified_count": verified_count,
            "related_count": related_count,
            "gap_count": gap_count,
            "gaps_summary_message": gaps_summary_message,
            "relevant_projects": relevant_projects,
            "relevant_experience": relevant_exp_list,
            "strengths": strengths,
            "gaps": gaps,
            "technical_gaps": [
                g for g in gaps_breakdown
                if g.get("score_component") in ("required_skills", "preferred_skills", "experience", "domain")
                or g.get("category") in ("required_skill", "preferred_skill", "experience", "domain")
            ],
            "unverified_traits": [
                g for g in gaps_breakdown
                if g.get("score_component") == "soft_traits"
                or g.get("category") in ("soft_skill", "trait")
            ],
            "eligibility_review": [
                g for g in gaps_breakdown
                if g.get("score_component") == "eligibility"
                or g.get("category") in ("education", "eligibility")
            ],
            "match_breakdown": breakdown,
            "seniority_alignment": seniority_alignment,
            "verified_professional_experience_years": cand_years,
            "verified_matches": verified_matches,
            "related_experience": related_experience,
            "gaps_breakdown": gaps_breakdown,
            "normalized_requirements": [r.model_dump() for r in requirements],
        }

        # Optional Groq phrasing refinement (never alters numerical scores or items)
        if self.api_key:
            try:
                explained = await self._explain_match_with_groq(jd_data, resume_data, match_result)
                if explained:
                    match_result["strengths"] = explained.get("strengths", match_result["strengths"])
            except Exception as exc:
                logger.debug("Groq explanation failed, continuing with deterministic match result: %s", exc)

        return match_result

    async def match_resume_to_jd(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        relevant_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Alias for backward-compatibility."""
        return await self.evaluate_resume_match(jd_data, resume_data, relevant_chunks)

    async def tailor_resume(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        canonical_requirements: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate structured section-by-section tailoring suggestions without fabricating facts.

        canonical_requirements: the normalized_requirements list from evaluate_resume_match.
        When provided, tailoring is strictly downstream of the canonical requirement graph.
        """
        desc_quality = jd_data.get("description_quality", "").upper()
        analysis_quality = jd_data.get("analysis_quality", "")
        has_zero_requirements = not canonical_requirements and not jd_data.get("required_skills")
        is_limited = (desc_quality in ("PARTIAL", "INSUFFICIENT") or analysis_quality == "insufficient_job_description") and has_zero_requirements

        deterministic_tailored = self._deterministic_tailor_resume(
            jd_data, resume_data, canonical_requirements=canonical_requirements
        )

        if not is_limited and self.api_key:
            try:
                groq_tailored = await self._tailor_with_groq(jd_data, resume_data, deterministic_tailored)
                if groq_tailored:
                    return groq_tailored
            except Exception as exc:
                logger.warning("Groq tailoring failed, utilizing grounded fallback: %s", exc)

        return deterministic_tailored

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> str:
        """General-purpose text completion via Groq chat completions."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    # ---------------------------------------------------------------------------
    # Groq API Calls with Repair Retries
    # ---------------------------------------------------------------------------

    async def _extract_with_groq(self, clean_jd: str) -> Dict[str, Any]:
        """Call Groq to extract structured JD fields according to strict schema."""
        system_prompt = (
            "You are an expert technical recruiter and resume analyzer.\n"
            "Analyze the job description and extract key attributes in STRICT JSON format.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- ONLY extract requirements explicitly supported by the supplied JD.\n"
            "- Do not infer technologies merely because they are common for the role.\n"
            "- Extract clean role_title without internal grade or headings (e.g. 'Lead AI Engineer' not 'About the Role: Grade Level: 11 Lead AI Engineer').\n"
            "- If an internal grade is mentioned, extract it into internal_grade (e.g. '11').\n"
            "- Categorize skills into required_skills (must-have) and preferred_skills (nice-to-have).\n\n"
            "Return ONLY a JSON object with EXACT keys:\n"
            "- company (string, required)\n"
            "- role_title (string, required)\n"
            "- internal_grade (string or null)\n"
            "- role_summary (string, 1-2 sentence concise factual summary)\n"
            "- seniority (string or null, e.g. 'Senior', 'Lead', 'Entry')\n"
            "- employment_type (string, e.g. 'Full-time', 'Internship', 'Contract')\n"
            "- location (string or null)\n"
            "- deadline (string or null)\n"
            "- compensation (string or null)\n"
            "- graduation_year_eligibility (string or null)\n"
            "- responsibilities (list of strings)\n"
            "- required_skills (list of strings)\n"
            "- preferred_skills (list of strings)\n"
            "- required_experience (list of strings)\n"
            "- min_years_experience (number or null, e.g. 5.0)\n"
            "- education_requirements (list of strings)\n"
            "- domain_requirements (list of strings)\n"
            "- tools_and_technologies (list of strings)\n"
            "- soft_skills (list of strings)\n"
            "- qualifications (list of strings)\n"
            "- keywords (list of strings)\n"
            "DO NOT include markdown fences. Return raw JSON only."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract structured requirements from this job description:\n\n{clean_jd[:30000]}"},
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw_text = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_text)
            validated = ExtractedJDModel.model_validate(parsed)
            return validated.model_dump()
        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning("First Groq JD extraction failed: %s. Retrying with repair...", err)

        repair_messages = list(messages)
        repair_messages.append({
            "role": "user",
            "content": "Return valid JSON matching keys: company, role_title, internal_grade, role_summary, seniority, employment_type, location, deadline, compensation, graduation_year_eligibility, responsibilities, required_skills, preferred_skills, required_experience, min_years_experience, education_requirements, domain_requirements, tools_and_technologies, soft_skills, qualifications, keywords.",
        })

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=repair_messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw_text = response.choices[0].message.content or "{}"
        parsed = json.loads(raw_text)
        validated = ExtractedJDModel.model_validate(parsed)
        return validated.model_dump()

    async def _explain_match_with_groq(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        match_result: Dict[str, Any],
    ) -> Optional[Dict[str, List[str]]]:
        """Call Groq to generate grounded natural language explanations for verified strengths."""
        system_prompt = (
            "You are a strict career assessment engine.\n"
            "ANTI-HALLUCINATION RULES:\n"
            "- Formulate 3-4 grounded bullet points for 'strengths'.\n"
            "- Every strength MUST trace directly to a verified JD requirement and a real project or experience in the resume.\n"
            "- Do not invent technologies, metrics, or years of experience.\n"
            "- Return JSON with keys: strengths (list of strings).\n"
            "Return raw JSON only."
        )

        user_content = (
            f"JD Role: {jd_data.get('role_title')} at {jd_data.get('company')}\n"
            f"Verified Matches: {json.dumps(match_result.get('verified_matches'))}\n"
            f"Candidate Projects: {json.dumps(resume_data.get('projects', [])[:3])}"
        )

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        if isinstance(data.get("strengths"), list):
            return {
                "strengths": [s for s in data["strengths"] if isinstance(s, str)],
            }
        return None

    async def _tailor_with_groq(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        fallback_tailored: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Call Groq to refine tailored resume suggestions while enforcing strict anti-hallucination contracts."""
        system_prompt = (
            "You are an executive resume strategist.\n"
            "CRITICAL ANTI-HALLUCINATION CONTRACT:\n"
            "- Targeted summary MUST be based on verified candidate skills, actual role domain, and transferable experience.\n"
            "- Do NOT imply seniority or leadership expertise that is not verified in the resume (e.g. do not say 'ready to lead AI services' if candidate has 1 year experience).\n"
            "- In Skills Section Ordering: PRIORITIZE verified resume skills matching JD; SECONDARY other verified technical skills; TARGET/LEARN genuine JD gaps (include source).\n"
            "- NEVER add skills to TARGET/LEARN that were not mentioned in the JD (do not add Prometheus/Grafana or Kafka unless in JD).\n"
            "- NEVER copy job board boilerplate, platform descriptions (e.g. LGBTQ community, myGwork), or recruiter contact rules.\n\n"
            "Return JSON matching keys: summary, skills, experience, projects.\n"
            "summary: {suggestion: str, strategy: str}\n"
            "skills: {prioritized: list[str], secondary: list[str], target_gaps: list[str], strategy: str}\n"
            "experience: list of {original_entry: str, action_suggestion: str, keywords_to_bold: list[str]}\n"
            "projects: list of {original_entry: str, action_suggestion: str, supports: list[str], does_not_establish: list[str], keywords_to_bold: list[str]}\n"
            "Raw JSON only."
        )

        user_content = (
            f"Target Role: {jd_data.get('role_title')} at {jd_data.get('company')}\n"
            f"JD Required Skills: {json.dumps(jd_data.get('required_skills', []))}\n"
            f"JD Preferred Skills: {json.dumps(jd_data.get('preferred_skills', []))}\n"
            f"Candidate Verified Skills: {json.dumps(resume_data.get('skills', []))}\n"
            f"Baseline Grounded Tailoring: {json.dumps(fallback_tailored)}"
        )

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.15,
            max_tokens=1200,
        )
        raw = resp.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        validated = TailoredResumeModel.model_validate(parsed)
        out = validated.model_dump()

        # Sanitize skills to ensure no noise words entered
        out["skills"]["prioritized"] = [
            s for s in out["skills"].get("prioritized", []) if is_valid_technical_skill(s)
        ]
        out["skills"]["secondary"] = [
            s for s in out["skills"].get("secondary", []) if is_valid_technical_skill(s)
        ]
        # Target gaps must strictly come from fallback target_gaps (derived from actual JD requirements)
        out["skills"]["target_gaps"] = fallback_tailored["skills"]["target_gaps"]

        # Enforce summary anti-hallucination and replace placeholders
        target_company = jd_data.get("company") or ""
        if target_company in ("Target Company", "Unknown Company", "Company Name", "Unknown"):
            target_company = ""
        summary_text = out["summary"].get("suggestion", "")
        if any(w in summary_text.lower() for w in ["lgbtq", "mygwork", "recruiter directly", "job board", "ready to lead", "senior leadership"]):
            out["summary"]["suggestion"] = fallback_tailored["summary"]["suggestion"]
        elif "Target Company" in summary_text or "Unknown Company" in summary_text:
            if target_company:
                out["summary"]["suggestion"] = summary_text.replace("Target Company", target_company).replace("Unknown Company", target_company)
            else:
                out["summary"]["suggestion"] = summary_text.replace(" at Target Company", "").replace(" Target Company", " the role")

        # Always preserve grounded 1-to-1 project cards from fallback_tailored
        merged_projects = []
        groq_projects = out.get("projects", [])
        for i, fb_p in enumerate(fallback_tailored.get("projects", [])):
            gp = groq_projects[i] if i < len(groq_projects) else {}
            rec = gp.get("action_suggestion") or fb_p.get("action_suggestion", "")
            if any(bad in rec.lower() for bad in ["future work", "opportunity to apply", "lack of", "missing", "does not have", "formal design pattern", "in future work"]):
                rec = fb_p.get("action_suggestion", "")
            # Preserve multi-tier architecture & API design recommendation when established
            if fb_p.get("related_evidence") and "multi-tier architecture" in fb_p.get("action_suggestion", "").lower():
                rec = fb_p.get("action_suggestion", "")

            p_entry = dict(fb_p)
            p_entry["action_suggestion"] = rec
            p_entry["project_id"] = fb_p.get("project_id")
            p_entry["project_title"] = fb_p.get("project_title")
            p_entry["project_bullets"] = fb_p.get("project_bullets", [])
            p_entry["supports"] = fb_p.get("supports", [])
            p_entry["related_evidence"] = fb_p.get("related_evidence", [])
            p_entry["does_not_establish"] = fb_p.get("does_not_establish", [])
            p_entry["keywords_to_bold"] = fb_p.get("keywords_to_bold", [])
            p_entry["original_entry"] = fb_p.get("original_entry", "")
            merged_projects.append(p_entry)

        out["projects"] = merged_projects
        return out

    # ---------------------------------------------------------------------------
    # Grounded Deterministic Engine
    # ---------------------------------------------------------------------------

    def _estimate_candidate_years(self, resume_data: Dict[str, Any]) -> Tuple[Optional[float], str]:
        """
        Estimate candidate verifiable years of professional work experience.
        Only inspects dated professional employment entries in the experience section.
        Does NOT convert education dates, project durations, or achievements into professional experience.
        If there is no dated professional experience, returns (None, "Not determinable from resume").
        """
        experiences = resume_data.get("experience", [])
        if not experiences:
            return None, "Not determinable from resume"

        # Check for date ranges specifically within the experience section items
        exp_text = " ".join(str(e) for e in experiences)
        year_matches = [int(y) for y in re.findall(r"\b(20[12]\d)\b", exp_text)]
        if not year_matches or len(year_matches) < 2:
            # Check for pattern like "2022 - Present" or "2023 to Current"
            pres_m = re.search(r"\b(20[12]\d)\s*(?:-|to)\s*(?:present|current)\b", exp_text, re.IGNORECASE)
            if pres_m:
                start_yr = int(pres_m.group(1))
                current_yr = 2026
                span = float(max(0.5, current_yr - start_yr))
                return span, f"Approximately {round(span, 1)} year{'s' if span != 1 else ''} of directly verifiable experience found in the resume."
            return None, "Not determinable from resume"

        span = float(max(year_matches) - min(year_matches))
        if span <= 0:
            span = 1.0
        elif span > 30:
            span = 30.0

        summary_msg = f"Approximately {round(span, 1)} year{'s' if span != 1 else ''} of directly verifiable experience found in the resume."
        return span, summary_msg

    def _calculate_domain_alignment(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
    ) -> float:
        """Calculate role and domain keyword alignment between JD and resume."""
        target_role = (jd_data.get("role_title") or "").lower()
        role_words = {w for w in re.findall(r"\b[a-zA-Z]{3,}\b", target_role) if w not in {"the", "and", "for", "with"}}

        resume_text = " ".join([
            str(resume_data.get("summary") or ""),
            " ".join(str(e) for e in resume_data.get("experience", [])),
            " ".join(str(p) for p in resume_data.get("projects", [])),
        ]).lower()

        if not role_words:
            return 0.6

        matched_words = sum(1 for w in role_words if w in resume_text)
        return matched_words / len(role_words)

    def _heuristic_extract_jd(self, prep: PreprocessedJD) -> Dict[str, Any]:
        """Extract structured job details deterministically from preprocessed text."""
        text = prep.cleaned_text
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        company = prep.detected_company or ""
        role_title = prep.detected_role or "Software Engineer"
        location = None
        employment_type = "Full-time"
        deadline = None
        compensation = None
        graduation_year = None
        seniority = None
        min_years = None
        required_skills: List[str] = []
        preferred_skills: List[str] = []
        responsibilities: List[str] = []
        qualifications: List[str] = []

        # Graduation year extraction (e.g. 2028 Graduates)
        grad_m = re.search(r"\b(202[4-9])\s*(?:graduates?|passouts?|batch)\b", text, re.IGNORECASE)
        if not grad_m:
            grad_m = re.search(r"\b(?:graduates?|batch of|class of|graduating in)\s*(202[4-9])\b", text, re.IGNORECASE)
        if grad_m:
            graduation_year = grad_m.group(1)

        # Find role title from early lines if not detected
        if role_title == "Software Engineer" and lines:
            for l in lines[:5]:
                if any(w in l.lower() for w in ["engineer", "developer", "architect", "scientist", "analyst", "lead", "manager"]):
                    role_title = l.split(" - ")[0].split(" | ")[0].strip()[:60]
                    break

        # Clean title & grade (Requirement 7)
        clean_title, detected_grade = clean_role_title(role_title)
        role_title = clean_title or role_title
        internal_grade = detected_grade or prep.internal_grade

        if not graduation_year:
            grad_title_m = re.search(r"\b(202[4-9])\s*(?:graduates?|batch)?\b", role_title, re.IGNORECASE)
            if grad_title_m:
                graduation_year = grad_title_m.group(1)

        # Seniority extraction
        if re.search(r"\b(?:senior|sr\.?|lead|principal|staff)\b", role_title, re.IGNORECASE):
            seniority = "Senior"
        elif re.search(r"\b(?:intern|internship|trainee)\b", role_title, re.IGNORECASE):
            seniority = "Intern"
            employment_type = "Internship"

        # Years of experience pattern
        exp_m = re.search(r"(\d+)\+?\s*(?:-\s*\d+\+?\s*)?years?(?:\s+of)?(?:\s+[a-zA-Z\s]{0,40})?\s+experience", text, re.IGNORECASE)
        if exp_m:
            try:
                min_years = float(exp_m.group(1))
            except ValueError:
                pass

        # Compensation pattern
        comp_m = re.search(r"(\$[\d,]+(?:\s*-\s*\$[\d,]+)?|\₹[\d,]+(?:\s*-\s*\₹[\d,]+)?)", text)
        if comp_m:
            compensation = comp_m.group(1)

        # Location extraction
        loc_m = re.search(r"(?i)location:\s*([^\n\r]+)", text)
        if loc_m:
            location = loc_m.group(1).strip()

        # Deadline extraction
        dl_m = re.search(r"(?i)deadline:\s*([^\n\r]+)", text)
        if dl_m:
            deadline = dl_m.group(1).strip()

        # Company extraction from header if not detected
        if (not company or company in ("Target Company", "Unknown Company", "Company Name")) and lines:
            first_line = lines[0]
            if " at " in first_line:
                parts = first_line.split(" at ", 1)
                role_title = clean_role_title(parts[0].strip())[0]
                company = parts[1].strip().rstrip(".,;: ")
            elif " with " in first_line:
                parts = first_line.split(" with ", 1)
                role_title = clean_role_title(parts[0].strip())[0]
                company = parts[1].strip().rstrip(".,;: ")

        # Technical skills catalog
        common_skills = [
            "Software Development", "Software Engineering", "System Design", "Problem Solving",
            "Algorithms", "Data Structures",
            "Python", "JavaScript", "TypeScript", "React", "Node.js", "Next.js",
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
            "AWS", "GCP", "Azure", "Git", "CI/CD", "REST APIs", "GraphQL", "FastAPI",
            "Django", "Flask", "Go", "Golang", "Java", "C++", "C#", "Rust", "Linux",
            "PyTorch", "TensorFlow", "Scikit-Learn", "Machine Learning", "Deep Learning",
            "NLP", "Computer Vision", "LLM", "Vector DB", "ChromaDB", "Tailwind CSS",
            "Kafka", "Kinesis", "SQLAlchemy",
        ]

        found_skills = []
        for s in common_skills:
            if re.search(r"(?<!\w)" + re.escape(s) + r"(?!\w)", text, re.IGNORECASE):
                canonical_s = normalize_skill(s)
                if canonical_s not in found_skills:
                    found_skills.append(canonical_s)

        # Split required vs preferred by actual section
        pref_block_m = re.search(r"(?is)(?:preferred|nice to have|plus|bonus)[:\s]+(.*?)(?:responsibilities|qualifications|$)", text)
        if pref_block_m:
            pref_text = pref_block_m.group(1)
            for s in found_skills:
                if re.search(r"(?<!\w)" + re.escape(s) + r"(?!\w)", pref_text, re.IGNORECASE):
                    preferred_skills.append(s)
                else:
                    required_skills.append(s)
        else:
            required_skills = list(found_skills)
            preferred_skills = []

        # Bullet point extraction
        for line in lines:
            if line.startswith(("-", "•", "*")):
                b = line.lstrip("-•* ").strip()
                if len(b) > 15:
                    if len(responsibilities) < 5:
                        responsibilities.append(b)
                    elif len(qualifications) < 5:
                        qualifications.append(b)

        keywords = list(dict.fromkeys(required_skills + preferred_skills + [role_title, company]))

        return {
            "company": company,
            "role_title": role_title,
            "internal_grade": internal_grade,
            "role_summary": f"Role: {role_title} at {company} focused on engineering and technology.",
            "seniority": seniority,
            "employment_type": employment_type,
            "location": location,
            "deadline": deadline,
            "compensation": compensation,
            "graduation_year_eligibility": graduation_year,
            "responsibilities": responsibilities or ["Develop core features", "Collaborate with cross-functional teams"],
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            # required_experience: only from explicit JD text — never fabricated from role title
            "required_experience": [f"{int(min_years)}+ years experience"] if min_years else [],
            "min_years_experience": min_years,
            # education_requirements: only add when JD heuristically mentions degree
            "education_requirements": [],
            "domain_requirements": [],
            "tools_and_technologies": required_skills[:5],
            "soft_skills": [],
            "qualifications": qualifications or [],
            "keywords": keywords[:15],
            "analysis_quality": "sufficient",
            "quality_warning": None,
        }

    def _deterministic_tailor_resume(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        canonical_requirements: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate structured section-by-section suggestions without hallucinating credentials.

        When canonical_requirements is supplied (the normalized_requirements from evaluate_resume_match),
        all skill lists and target_gaps are derived strictly from that graph — never from generic
        knowledge of what the role type normally requires.
        """
        user_skills_raw = resume_data.get("skills", [])
        user_skills_clean = [
            normalize_skill(s) for s in user_skills_raw if isinstance(s, str) and is_valid_technical_skill(s)
        ]

        target_role = jd_data.get("role_title", "Software Engineer")
        clean_title, _ = clean_role_title(target_role)
        target_role = clean_title or target_role
        target_company = (jd_data.get("company") or "").strip()
        if target_company in ("Target Company", "Unknown Company", "Company Name", "Unknown"):
            target_company = ""
        company_phrase = f" at {target_company}" if target_company else ""

        # ---------------------------------------------------------------
        # ONE SOURCE OF TRUTH: use canonical requirements graph when available
        # ---------------------------------------------------------------
        if canonical_requirements:
            # Build sets directly from normalized requirements (single source of truth)
            verified_req_canonicals: List[str] = [
                r["canonical"] for r in canonical_requirements
                if r.get("match_status") == "verified"
                and (
                    r.get("score_component") in ("required_skills", "preferred_skills")
                    or r.get("category") in ("required_skill", "preferred_skill")
                )
            ]
            verified_related_canonicals: List[str] = [
                r["canonical"] for r in canonical_requirements
                if r.get("match_status") == "related"
                and (
                    r.get("score_component") in ("required_skills", "preferred_skills")
                    or r.get("category") in ("required_skill", "preferred_skill")
                )
            ]
            # target_gaps: only actual missing JD requirements (must appear in canonical graph)
            target_gaps: List[str] = [
                f"{r['canonical']} (Source: {r.get('source', 'JD requirement')})"
                for r in canonical_requirements
                if r.get("match_status") == "missing"
                and (
                    r.get("score_component") in ("required_skills", "preferred_skills")
                    or r.get("category") in ("required_skill", "preferred_skill")
                )
            ]
            all_jd_canonicals: set = {
                r["canonical"] for r in canonical_requirements
                if (
                    r.get("score_component") in ("required_skills", "preferred_skills")
                    or r.get("category") in ("required_skill", "preferred_skill")
                )
            }
            # PRIORITIZE: resume skills that are verified JD requirements
            prioritized = list(dict.fromkeys(verified_req_canonicals))
            # RELATED: resume skills related to JD requirements
            related_skills = list(dict.fromkeys(verified_related_canonicals))
            # SECONDARY: resume skills not in JD scope (keep to show breadth)
            secondary = [
                s for s in user_skills_clean
                if s not in all_jd_canonicals and s not in related_skills
            ]
            secondary = list(dict.fromkeys(secondary))
        else:
            # Fallback: derive from jd_data when no canonical graph is passed
            jd_required = [normalize_skill(s) for s in jd_data.get("required_skills", []) if s]
            jd_preferred = [normalize_skill(s) for s in jd_data.get("preferred_skills", []) if s]
            all_jd_canonicals = set(jd_required + jd_preferred)

            prioritized = [s for s in user_skills_clean if s in all_jd_canonicals]
            secondary = [s for s in user_skills_clean if s not in all_jd_canonicals]
            prioritized = list(dict.fromkeys(prioritized))
            secondary = list(dict.fromkeys(secondary))
            related_skills = []

            # Target gaps: only from actual JD requirements
            target_gaps = []
            for s in jd_required:
                if s not in user_skills_clean and s not in target_gaps:
                    target_gaps.append(f"{s} (Source: JD required technology)")
            for s in jd_preferred:
                if s not in user_skills_clean and s not in target_gaps:
                    target_gaps.append(f"{s} (Source: JD preferred requirement)")

        # 2. Targeted Summary (grounded — only verified primary skills)
        verified_primary = ", ".join(prioritized[:4]) if prioritized else (
            ", ".join(related_skills[:2]) if related_skills else ", ".join(secondary[:3])
        )
        target_domain = re.sub(
            r"(?i)\b(?:lead|senior|principal|staff|director|head of|vp|junior|intern)\b", "", target_role
        )
        target_domain = re.sub(r"\s+", " ", target_domain).strip()

        if verified_primary:
            tailored_summary = (
                f"Software engineering candidate with verified experience in {verified_primary}. "
                f"Brings hands-on foundations transferable to the {target_domain} responsibilities{company_phrase}."
            )
        else:
            tailored_summary = (
                f"Software engineering candidate applying to {target_role}{company_phrase}. "
                f"Skills and projects demonstrate relevant technical foundations."
            )

        # Check for limited / partial JD with zero reliable requirements (Section 16)
        desc_quality = jd_data.get("description_quality", "").upper()
        analysis_quality = jd_data.get("analysis_quality", "")
        has_zero_requirements = (len(all_jd_canonicals) == 0 and not canonical_requirements)
        is_limited_tailoring = (
            (desc_quality in ("PARTIAL", "INSUFFICIENT") or analysis_quality == "insufficient_job_description")
            and has_zero_requirements
        )

        if is_limited_tailoring:
            tailored_summary = (
                f"Tailoring is limited because the complete job requirements are unavailable. "
                f"Verified resume strengths demonstrate software engineering foundations."
            )
            summary_strategy = (
                "Tailoring is limited because the complete job requirements are unavailable. "
                "Paste full JD to unlock precise tailoring."
            )
            prioritized = []
            secondary = list(dict.fromkeys(user_skills_clean[:6]))
            target_gaps = []
            skills_strategy = (
                "Tailoring is limited because the complete job requirements are unavailable. "
                "Paste full JD to unlock precise tailoring."
            )
        else:
            summary_strategy = (
                f"Positions verified candidate strengths ({verified_primary or 'general engineering foundations'}) "
                f"directly against {target_role} expectations without claiming unverified credentials."
            )
            skills_strategy = (
                "Order verified skills critical to the role first (from canonical JD requirements). "
                "Keep general skills secondary. Target gaps are real JD requirements only."
            )

        # 3. Project Alignment — aggregated: ONE section per project
        raw_projects = resume_data.get("projects", [])
        
        # Flatten glued project lines (where a new project Title | Tech follows sentence end)
        flattened_raw = []
        for p in raw_projects:
            if isinstance(p, str):
                splits = re.split(r'(?<=[.!?])\s+(?=[A-Z][A-Za-z0-9\s]{2,35}\s*\|)', p)
                for s in splits:
                    if s.strip():
                        flattened_raw.append(s.strip())
            else:
                flattened_raw.append(p)

        action_verbs = {
            'built', 'designed', 'implemented', 'documented', 'developed', 'created',
            'engineered', 'led', 'architected', 'spearheaded', 'integrated', 'optimized'
        }

        grouped_projects: List[Dict[str, Any]] = []
        for item in flattened_raw:
            if isinstance(item, dict):
                parent_pid = item.get("parent_project_id")
                if parent_pid:
                    parent = next((proj for proj in grouped_projects if proj.get("project_id") == parent_pid), None)
                    if parent:
                        b_list = item.get("bullets") or item.get("project_bullets") or []
                        for b in (b_list if isinstance(b_list, list) else [b_list]):
                            if b and b not in parent["bullets"]:
                                parent["bullets"].append(b)
                                parent["project_bullets"].append(b)
                        continue

                pid = item.get("project_id") or f"proj_{len(grouped_projects) + 1}"
                title = item.get("title") or item.get("project_title") or "Project"
                norm_title = re.sub(r"[^a-zA-Z0-9]+", "", title).lower()
                existing = next((proj for proj in grouped_projects if proj.get("norm_title") == norm_title), None)
                b_list = item.get("bullets") or item.get("project_bullets") or []
                clean_b_list = list(b_list if isinstance(b_list, list) else [b_list])
                techs = item.get("technologies") or item.get("project_technologies") or []
                
                if existing:
                    for b in clean_b_list:
                        if b and b not in existing["bullets"]:
                            existing["bullets"].append(b)
                            existing["project_bullets"].append(b)
                else:
                    grouped_projects.append({
                        "project_id": pid,
                        "title": title,
                        "project_title": title,
                        "norm_title": norm_title,
                        "technologies": techs,
                        "project_technologies": techs,
                        "bullets": clean_b_list,
                        "project_bullets": clean_b_list,
                        "description": " ".join(clean_b_list) if clean_b_list else title,
                        "entry": " ".join(clean_b_list) if clean_b_list else title,
                    })
            elif isinstance(item, str):
                clean = item.strip()
                is_bullet_char = clean.startswith(("-", "*", "•", "▪", "–", "—", ">", "\ufffd"))
                b_clean = re.sub(r"^[-*•▪–—>\ufffd\s]+", "", clean)

                is_header = False
                title = ""
                techs = []
                if not is_bullet_char and "|" in clean:
                    parts = [p.strip() for p in clean.split("|")]
                    cand = parts[0]
                    first_w = cand.split()[0].lower() if cand.split() else ""
                    if first_w not in action_verbs and len(cand) <= 50:
                        is_header = True
                        title = cand
                        techs = [t.strip() for t in parts[1].split(",") if t.strip()] if len(parts) > 1 else []
                elif not is_bullet_char and len(clean) <= 40 and not clean.endswith("."):
                    first_w = clean.split()[0].lower() if clean.split() else ""
                    if first_w not in action_verbs:
                        is_header = True
                        title = clean

                if is_header:
                    norm_title = re.sub(r"[^a-zA-Z0-9]+", "", title).lower()
                    existing = next((proj for proj in grouped_projects if proj.get("norm_title") == norm_title), None)
                    if not existing:
                        grouped_projects.append({
                            "project_id": f"proj_{len(grouped_projects) + 1}",
                            "title": title,
                            "project_title": title,
                            "norm_title": norm_title,
                            "technologies": techs,
                            "project_technologies": techs,
                            "bullets": [],
                            "project_bullets": [],
                            "description": "",
                            "entry": "",
                        })
                else:
                    # Supporting bullet
                    if grouped_projects:
                        grouped_projects[-1]["bullets"].append(b_clean)
                        grouped_projects[-1]["project_bullets"].append(b_clean)
                        if grouped_projects[-1]["description"]:
                            grouped_projects[-1]["description"] += " " + b_clean
                        else:
                            grouped_projects[-1]["description"] = b_clean
                    else:
                        grouped_projects.append({
                            "project_id": "proj_1",
                            "title": "Project",
                            "project_title": "Project",
                            "norm_title": "project",
                            "technologies": [],
                            "project_technologies": [],
                            "bullets": [b_clean],
                            "project_bullets": [b_clean],
                            "description": b_clean,
                            "entry": b_clean,
                        })

        tailored_proj: List[Dict[str, Any]] = []
        for p_obj in grouped_projects[:4]:
            p_title = p_obj.get("project_title") or p_obj.get("title") or "Project"
            p_bullets = p_obj.get("project_bullets") or p_obj.get("bullets") or []
            p_desc = p_obj.get("description") or p_obj.get("entry") or ""
            full_proj_text = f"{p_title} {' '.join(p_bullets)} {p_desc}"
            full_proj_lower = full_proj_text.lower()

            # Demonstrates (verified capabilities established in this project)
            demonstrates = []
            if "software development" in full_proj_lower or any(k in full_proj_lower for k in ["fastapi", "next.js", "full-stack", "built a", "rest api"]):
                demonstrates.append("✓ Software Development")
            if any(k in full_proj_lower for k in ["rest api", "restful", "fastapi"]):
                demonstrates.append("✓ REST API Development")
            if "system design" in full_proj_lower or any(k in full_proj_lower for k in ["relational schema", "scaling", "architecture", "trade-offs"]):
                demonstrates.append("✓ System Design")
            if any(k in full_proj_lower for k in ["relational schema", "postgresql", "mysql", "sqlite", "schema design"]):
                demonstrates.append("✓ Relational Database Design")
            for sk in user_skills_clean:
                if len(demonstrates) >= 6:
                    break
                if re.search(r"\b" + re.escape(sk) + r"\b", full_proj_text, re.IGNORECASE):
                    tag = f"✓ {sk}"
                    if tag not in demonstrates:
                        demonstrates.append(tag)

            # Related Evidence
            related_ev = []
            if any(k in full_proj_lower for k in ["multi-tier", "architecture", "caching", "sharding", "horizontal scaling", "trade-offs", "scaling", "route53"]):
                related_ev.append("△ Software Architecture")

            # Does Not Establish
            not_supported = []
            if "Software Design Patterns" in all_jd_canonicals or any("design patterns" in g.lower() for g in target_gaps):
                if not re.search(r"\b(?:design pattern|factory pattern|singleton|observer|adapter)\b", full_proj_lower):
                    not_supported.append("✗ Software Design Patterns")
            for gap in target_gaps[:2]:
                gap_name = gap.split(" (")[0]
                tag = f"✗ {gap_name}"
                if gap_name.lower() not in full_proj_lower and tag not in not_supported and len(not_supported) < 2:
                    not_supported.append(tag)

            # Constructive recommendation: Never negative advice or artificial disclaimers
            if related_ev:
                action_rec = (
                    "Emphasize the multi-tier architecture, API design, schema decisions and scalability "
                    "trade-offs already demonstrated in this project."
                )
            elif demonstrates:
                action_rec = (
                    f"Emphasize the engineering metrics, feature delivery, and architectural "
                    f"decisions already demonstrated in {p_title}."
                )
            else:
                action_rec = (
                    f"Highlight technical decisions and concrete implementation details relevant to the role."
                )

            tailored_proj.append({
                "project_id": p_obj.get("project_id"),
                "project_title": p_title,
                "project_bullets": p_bullets[:5],
                "original_entry": p_title if len(p_title) <= 60 else p_title[:57] + "...",
                "action_suggestion": action_rec,
                "supports": demonstrates[:6] or ["✓ Core software engineering implementation"],
                "related_evidence": related_ev,
                "does_not_establish": not_supported[:2],
                "keywords_to_bold": [
                    kw for kw in all_jd_canonicals if kw.lower() in full_proj_lower
                ][:3],
            })

        # 4. Experience Bullet Points
        experiences = resume_data.get("experience", [])
        tailored_exp = [
            {
                "original_entry": str(e)[:140] + ("..." if len(str(e)) > 140 else ""),
                "action_suggestion": "Elevate technical metrics and feature delivery impact to the primary bullet point.",
                "keywords_to_bold": [
                    kw for kw in all_jd_canonicals if kw.lower() in str(e).lower()
                ][:3],
            }
            for e in experiences[:3]
        ]

        return {
            "summary": {
                "suggestion": tailored_summary,
                "strategy": summary_strategy,
            },
            "skills": {
                "prioritized": prioritized,
                "secondary": secondary,
                "target_gaps": target_gaps,
                "strategy": skills_strategy,
            },
            "experience": tailored_exp,
            "projects": tailored_proj,
        }

    async def generate_grounded_match_explanation(
        self,
        role_title: str,
        company: str,
        description: str,
        user_skills: List[str],
        user_preferences: Dict[str, Any],
        job_location: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a concise, 1-2 sentence grounded match explanation using Groq."""
        if not self.api_key:
            return None

        prep = clean_job_description(description)
        clean_desc = prep.cleaned_text

        matched_skills_overlap = [s for s in user_skills if s.lower() in clean_desc.lower()]
        pref_roles = user_preferences.get("preferred_roles", [])
        pref_location = user_preferences.get("preferred_location", "")

        loc_score, loc_reason, loc_scope = evaluate_location_match(pref_location, job_location)

        system_prompt = (
            "You are Aptly's grounded matching explainer. Output 1-2 concise, factual sentences "
            "explaining why this candidate matches the role based strictly on the verified skills and preferences provided.\n"
            "STRICT RULES:\n"
            "- Mention only skills from the VERIFIED SKILLS list.\n"
            "- Mention only role attributes from the JOB INFO.\n"
            "- LOCATION GRANULARITY RULE: Never claim the candidate has a preference for a city or region unless that exact city/region was explicitly given in CANDIDATE LOCATION PREFERENCE. If candidate preference is a country (e.g. India), state 'This position is within your preferred country, India.' and never claim they prefer the specific job city.\n"
            "- If candidate preference is 'Remote', evaluate remote independently.\n"
            "- If candidate preference is a specific city (e.g. Bengaluru), do not treat other cities as location matches.\n"
            "- NEVER invent or assume skills, years of experience, or unstated facts.\n"
            "- Output plain text without markdown or quotes."
        )

        user_content = (
            f"COMPANY: {company}\n"
            f"ROLE: {role_title}\n"
            f"JOB LOCATION: {job_location or 'Not specified'}\n"
            f"VERIFIED SKILLS: {', '.join(user_skills[:6])}\n"
            f"MATCHED SKILLS: {', '.join(matched_skills_overlap[:4])}\n"
            f"TARGET ROLES: {', '.join(pref_roles)}\n"
            f"CANDIDATE LOCATION PREFERENCE: {pref_location} (Scope: {loc_scope})\n"
            f"DETERMINED LOCATION ALIGNMENT: {loc_reason or 'No exact location match'}\n"
            f"JOB SUMMARY: {clean_desc[:3000]}\n\n"
            "Provide a 1-sentence grounded match explanation."
        )

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                max_tokens=80,
            )
            content = resp.choices[0].message.content
            if content:
                return content.strip().strip('"').strip("'")
        except Exception as exc:
            logger.debug("Groq explanation generation failed gracefully: %s", exc)
            return None
        return None


def evaluate_location_match(
    pref_location: Optional[str],
    job_location: Optional[str],
) -> Tuple[float, Optional[str], str]:
    """
    Evaluates candidate location preference against job location, strictly preserving granularity.
    Returns: (score: float, reason_text: Optional[str], granularity: str)
    Granularity is one of: 'remote', 'country', 'state', 'city', 'unspecified'.
    """
    if not pref_location:
        if job_location and "remote" in job_location.lower():
            return 0.8, "Offers Remote work flexibility", "remote"
        return 0.6, None, "unspecified"

    pref_raw = pref_location.strip()
    pref_clean = pref_raw.lower()
    job_loc_raw = (job_location or "").strip()
    job_loc_clean = job_loc_raw.lower()

    # 1. Remote evaluation
    if "remote" in pref_clean:
        if "remote" in job_loc_clean:
            return 1.0, "Offers Remote work flexibility", "remote"
        else:
            return 0.3, None, "remote"

    # Known Countries (lowercase)
    KNOWN_COUNTRIES = {
        "india", "united states", "usa", "us", "united kingdom", "uk",
        "canada", "germany", "australia", "singapore", "netherlands",
        "france", "ireland", "japan", "switzerland", "uae", "united arab emirates",
    }

    # Known States/Provinces (lowercase)
    KNOWN_STATES = {
        "karnataka", "maharashtra", "tamil nadu", "delhi", "telangana", "uttar pradesh",
        "california", "new york", "texas", "washington", "ontario", "british columbia",
    }

    # 2. Country Scope
    if pref_clean in KNOWN_COUNTRIES:
        granularity = "country"
        if pref_clean in job_loc_clean or (pref_clean in ("usa", "us") and re.search(r"\b(?:usa|us|united states)\b", job_loc_clean)):
            return 1.0, f"This position is within your preferred country, {pref_raw}.", "country"
        else:
            return 0.4, None, "country"

    # 3. State Scope
    if pref_clean in KNOWN_STATES:
        granularity = "state"
        if pref_clean in job_loc_clean:
            return 1.0, f"This position is within your preferred region, {pref_raw}.", "state"
        else:
            return 0.3, None, "state"

    # 4. City Scope (Specific city preference, e.g. 'Bengaluru', 'San Francisco', etc.)
    granularity = "city"
    escaped_city = re.escape(pref_clean)
    if re.search(r"\b" + escaped_city + r"\b", job_loc_clean):
        return 1.0, f"Matches your preferred city, {pref_raw}.", "city"

    if "remote" in job_loc_clean:
        return 0.7, "Offers Remote work flexibility", "city"

    return 0.3, None, "city"


# Global singleton
llm_service = LLMService()
