"""Aptly Voice Assistant endpoints: query, speech synthesis, and daily briefing.

Integrates Groq LLM for grounded reasoning and ElevenLabs for text-to-speech,
with per-user rate limiting, selective context retrieval, and strict user isolation.
"""
from __future__ import annotations

import logging
from math import ceil
import re
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.api.v1.endpoints.auth import UserProfile, _get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.services.assistant_context import (
    get_application_progress_context,
    get_briefing_context,
    get_matches_context,
    get_resume_skill_context,
    get_upcoming_deadlines_context,
)
from app.services.llm_service import llm_service
from app.services.tts_service import generate_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Assistant"])


# ---------------------------------------------------------------------------
# Rate Limiting Helper & Dependency
# ---------------------------------------------------------------------------

async def assistant_speech_identifier(request: Request) -> str:
    """Extract authenticated user identifier for per-user speech rate limiting."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from app.core.security import decode_access_token
            payload = decode_access_token(token)
            if payload and "sub" in payload:
                return f"user:{payload['sub']}"
        except Exception:
            return f"token:{token}"
    client_ip = request.client.host if request.client else "127.0.0.1"
    return f"ip:{client_ip}"


async def speech_rate_limit_callback(request: Request, response: Response, pexpire: int):
    """Return clean HTTP 429 when speech rate limit is exceeded."""
    expire = ceil(pexpire / 1000)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Speech generation limit reached (5 requests per minute). Please try again shortly.",
        headers={"Retry-After": str(expire)},
    )


class SafeSpeechRateLimiter(RateLimiter):
    """Rate limiter that safely permits requests if Redis is unavailable in development."""

    def __init__(self):
        super().__init__(
            times=settings.ASSISTANT_SPEECH_LIMIT,
            seconds=settings.ASSISTANT_SPEECH_WINDOW_SECONDS,
            identifier=assistant_speech_identifier,
            callback=speech_rate_limit_callback,
        )

    async def __call__(self, request: Request, response: Response):
        if not FastAPILimiter.redis:
            # Redis is not configured or unavailable; permit request safely in development/testing
            return
        try:
            return await super().__call__(request, response)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("FastAPI-Limiter check failed: %s. Permitting request.", exc)
            return


speech_rate_limiter = SafeSpeechRateLimiter()


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class AssistantQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    page_context: Optional[str] = Field(default=None, max_length=200)


class SuggestedAction(BaseModel):
    label: str
    route: str


class AssistantQueryResponse(BaseModel):
    answer: str
    intent: str
    voice_available: bool
    suggested_actions: List[SuggestedAction] = []


class BriefingSummaryBlock(BaseModel):
    active_matches_count: int
    upcoming_oa_count: int
    upcoming_interviews_count: int
    deadlines_7d_count: int
    pending_confirmations_count: int
    top_matches: List[Dict[str, Any]] = []
    upcoming_deadlines: List[Dict[str, Any]] = []


class AssistantBriefingResponse(BaseModel):
    answer: str
    intent: str = "briefing"
    summary: BriefingSummaryBlock
    voice_available: bool
    suggested_actions: List[SuggestedAction] = []


class AssistantSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


# ---------------------------------------------------------------------------
# Intent Detection & Action Recommendation
# ---------------------------------------------------------------------------

def detect_intent(message: str) -> str:
    """Classify user query into a targeted intent for selective context retrieval."""
    msg = message.lower()

    if any(k in msg for k in ["brief", "daily briefing", "summary", "morning update", "overview", "what's today"]):
        return "briefing"
    if any(k in msg for k in ["deadline", "due", "upcoming", "assessment", "oa", "interview", "schedule"]):
        return "deadlines"
    if any(k in msg for k in ["match", "recommend", "position", "finding", "strongest", "best fit", "roles"]):
        return "matches"
    if any(k in msg for k in ["application", "applied", "status", "progress", "replies", "offer", "rejected", "pipeline", "track"]):
        return "applications"
    if any(k in msg for k in ["resume", "skill", "mention", "experience", "cv", "qualif"]):
        return "resume"

    return "general"


def extract_skill_query(message: str) -> str:
    """Extract candidate skill name from resume questions like 'Does my resume mention Python?'"""
    msg = message.strip()
    match = re.search(r"(?:mention|have|list|include|contain)\s+([a-zA-Z0-9\+\#\.\s]+?)(?:\?|$|\.|\,)", msg, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return msg


def get_suggested_actions(intent: str, context: Dict[str, Any]) -> List[SuggestedAction]:
    """Generate contextual actions linking only to valid Aptly routes."""
    actions: List[SuggestedAction] = []

    if intent == "briefing":
        actions.append(SuggestedAction(label="View Track Jobs", route="/track-jobs"))
        if context.get("active_matches_count", 0) > 0:
            actions.append(SuggestedAction(label="View Matches", route="/find-positions"))
        else:
            actions.append(SuggestedAction(label="Analyze a Job Description", route="/jd-analyzer"))
    elif intent == "deadlines":
        actions.append(SuggestedAction(label="View Track Jobs", route="/track-jobs"))
    elif intent == "matches":
        actions.append(SuggestedAction(label="View Matches", route="/find-positions"))
        actions.append(SuggestedAction(label="Tailor Resume in JD Analyzer", route="/jd-analyzer"))
    elif intent == "applications":
        actions.append(SuggestedAction(label="Open Track Jobs", route="/track-jobs"))
    elif intent == "resume":
        actions.append(SuggestedAction(label="Open JD Analyzer", route="/jd-analyzer"))
        actions.append(SuggestedAction(label="Update Resume Settings", route="/onboarding/resume"))
    else:
        actions.append(SuggestedAction(label="View Track Jobs", route="/track-jobs"))
        actions.append(SuggestedAction(label="Explore Matches", route="/find-positions"))

    return actions


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/query", response_model=AssistantQueryResponse)
async def query_assistant(
    payload: AssistantQueryRequest,
    current_user: UserProfile = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Handle grounded text queries using Groq LLM with selective user context."""
    user_id = current_user.id
    message = payload.message.strip()
    intent = detect_intent(message)

    # Selective context retrieval
    if intent == "briefing":
        context_data = await get_briefing_context(db, user_id)
    elif intent == "deadlines":
        context_data = await get_upcoming_deadlines_context(db, user_id)
    elif intent == "matches":
        context_data = await get_matches_context(db, user_id, top_n=5)
    elif intent == "applications":
        context_data = await get_application_progress_context(db, user_id)
    elif intent == "resume":
        skill_term = extract_skill_query(message)
        context_data = await get_resume_skill_context(db, user_id, skill_term)
    else:
        # General query: provide concise briefing context
        context_data = await get_briefing_context(db, user_id)

    system_prompt = (
        "You are Aptly's career workspace assistant. "
        "Your task is to provide clear, helpful, factual guidance based SOLELY on the user's authentic Aptly data provided below.\n\n"
        "STRICT ANTI-HALLUCINATION RULES:\n"
        "1. Never invent job applications, companies, matches, deadlines, interviews, OA rounds, offers, skills, or metrics.\n"
        "2. Ground every single claim, company name, number, and status directly in the user context.\n"
        "3. If the user asks about something not present in their data (e.g. no deadlines, no matches, or a skill not on their resume), "
        "state that clearly and concisely without making up assumptions.\n"
        "4. Aptly canonical application statuses are strictly: 'applied', 'oa' (online assessment), 'interview', 'offer', 'rejected'.\n"
        "5. Keep responses concise, direct, professional, and natural to be spoken aloud. Avoid bullet walls or robotic phrasing."
    )

    page_ctx_info = f"\n(User currently viewing: {payload.page_context})" if payload.page_context else ""
    prompt = f"User Question: {message}{page_ctx_info}\n\nUser Context:\n{context_data}"

    try:
        raw_answer = await llm_service.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=350,
        )
        answer = raw_answer.strip()
    except Exception as exc:
        logger.error("Groq LLM call failed in assistant query: %s", exc)
        answer = (
            "I'm unable to process your request right now due to a service connection issue. "
            "Please try asking again in a moment."
        )

    # Check voice availability: available if ElevenLabs API key and voice ID are set
    voice_available = bool(settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_VOICE_ID)

    actions = get_suggested_actions(intent, context_data)

    return AssistantQueryResponse(
        answer=answer,
        intent=intent,
        voice_available=voice_available,
        suggested_actions=actions,
    )


@router.get("/briefing", response_model=AssistantBriefingResponse)
async def get_daily_briefing(
    current_user: UserProfile = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate structured Daily Briefing data with a grounded natural-language briefing."""
    user_id = current_user.id
    context_data = await get_briefing_context(db, user_id)

    summary_block = BriefingSummaryBlock(
        active_matches_count=context_data["active_matches_count"],
        upcoming_oa_count=context_data["oa_count"],
        upcoming_interviews_count=context_data["interview_count"],
        deadlines_7d_count=context_data["upcoming_deadlines_7d_count"],
        pending_confirmations_count=context_data["pending_confirmations_count"],
        top_matches=context_data["top_matches"],
        upcoming_deadlines=context_data["upcoming_deadlines"],
    )

    # Zero-data check
    if not context_data["has_data"]:
        answer = (
            f"Good day, {current_user.first_name}. You don't have any active job applications or matches yet. "
            "Upload your resume in Settings or explore 'Find New Positions' to discover personalized roles."
        )
    else:
        system_prompt = (
            "You are Aptly's career workspace assistant delivering a morning briefing. "
            "Synthesize the provided user data into 2 to 3 concise, spoken sentences. "
            "STRICT RULES:\n"
            "1. Ground all numbers, company names, and deadlines strictly in the context.\n"
            "2. Never hallucinate extra companies, offers, or interviews.\n"
            "3. Mention key items: new matches, upcoming assessments or deadlines within 7 days, and any pending confirmations.\n"
            "4. Tone: calm, professional, motivating, concise."
        )

        user_prompt = (
            f"User: {current_user.first_name}\n"
            f"Data Summary: {context_data}"
        )

        try:
            raw_answer = await llm_service.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=250,
            )
            answer = raw_answer.strip()
        except Exception as exc:
            logger.error("Groq LLM call failed in assistant briefing: %s", exc)
            # Safe deterministic fallback
            parts = []
            if summary_block.active_matches_count > 0:
                parts.append(f"{summary_block.active_matches_count} active position matches")
            if summary_block.deadlines_7d_count > 0:
                parts.append(f"{summary_block.deadlines_7d_count} deadlines this week")
            if summary_block.upcoming_oa_count > 0:
                parts.append(f"{summary_block.upcoming_oa_count} upcoming assessment")
            if summary_block.pending_confirmations_count > 0:
                parts.append(f"{summary_block.pending_confirmations_count} application awaiting confirmation")

            detail_str = ", ".join(parts) if parts else "no pending deadlines"
            answer = f"Good day, {current_user.first_name}. Here is your Aptly briefing: you have {detail_str}."

    voice_available = bool(settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_VOICE_ID)
    actions = get_suggested_actions("briefing", context_data)

    return AssistantBriefingResponse(
        answer=answer,
        intent="briefing",
        summary=summary_block,
        voice_available=voice_available,
        suggested_actions=actions,
    )


@router.post(
    "/speech",
    response_class=StreamingResponse,
    dependencies=[Depends(speech_rate_limiter)],
)
async def synthesize_speech(
    payload: AssistantSpeechRequest,
    current_user: UserProfile = Depends(_get_current_user),
):
    """Generate audio/mpeg stream via ElevenLabs with per-user rate limiting (5 req/min)."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text required for speech generation",
        )

    # generate_speech handles credentials check and errors, raising HTTPException(503) if unavailable
    return generate_speech(text)
