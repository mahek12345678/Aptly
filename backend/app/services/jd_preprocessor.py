"""Job Description Preprocessor and Cleaning Engine.

Preprocesses raw job descriptions prior to structured extraction and matching:
- Strips third-party job board wrappers (e.g. myGwork, LinkedIn, Indeed, Adzuna).
- Cleans recruiter contact disclaimers and agency notices.
- Normalizes HTML entities, tracking links, and formatting noise.
- Preserves legitimate job content, employer equal-opportunity/diversity statements,
  and role requirements.
- Assesses extraction quality and detects insufficient or malformed descriptions.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class PreprocessedJD:
    raw_text: str
    cleaned_text: str
    analysis_quality: str  # "sufficient" | "insufficient_job_description"
    description_quality: str = "FULL"  # "FULL" | "PARTIAL"
    quality_warning: Optional[str] = None
    detected_company: Optional[str] = None
    detected_role: Optional[str] = None
    internal_grade: Optional[str] = None
    stripped_boilerplate_count: int = 0


def clean_role_title(raw_title: str) -> Tuple[str, Optional[str]]:
    """
    Clean role title by stripping metadata headings, internal grade indicators, and company suffixes.
    
    Example:
    'About the Role: Grade Level (for internal use): 11 Lead AI Engineer' -> ('Lead AI Engineer', '11')
    """
    if not raw_title:
        return "", None

    text = raw_title.strip()

    # Extract internal grade (e.g. Grade Level (for internal use): 11 or Grade: 12 or Band 4)
    internal_grade = None
    grade_match = re.search(
        r"(?i)(?:grade\s*level|grade|job\s*grade|band|level)(?:\s*\([^)]*\))?[:\s]+(\d+[a-zA-Z]?)",
        text,
    )
    if grade_match:
        internal_grade = grade_match.group(1).strip()

    # Remove grade and band patterns
    text = re.sub(
        r"(?i)\(?(?:grade\s*level|grade|job\s*grade|band|level)(?:\s*\([^)]*\))?[:\s]*\d+[a-zA-Z]?\)?",
        "",
        text,
    )
    text = re.sub(
        r"(?i)\(for\s+internal\s+use(?:\s+only)?\)[:\s]*",
        "",
        text,
    )

    # Remove common prefix headings repeatedly until fixed point
    prefixes_to_strip = [
        r"(?i)^about\s+the\s+(?:role|job|position|team)[:\s]*",
        r"(?i)^role\s+summary[:\s]*",
        r"(?i)^position\s+overview[:\s]*",
        r"(?i)^job\s+(?:title|description|summary|overview|details)[:\s]*",
        r"(?i)^role[:\s]+",
        r"(?i)^position[:\s]+",
        r"(?i)\(for\s+internal\s+use(?:\s+only)?\)[:\s]*",
    ]
    while True:
        prev = text
        for p in prefixes_to_strip:
            text = re.sub(p, "", text).strip()
        if text == prev:
            break

    # Strip company suffixes like " - S&P Global" or " at S&P Global"
    text = re.sub(r"(?i)\s+(?:-|\||at|with)\s+[A-Za-z0-9&.\s]{2,40}$", "", text).strip()

    # Clean multiple spaces and trailing punctuation
    text = re.sub(r"[ \t]+", " ", text).strip(" -:|,")
    return text, internal_grade


# Third-party platform / aggregator intro patterns that wrap the real role
_THIRD_PARTY_WRAPPER_PATTERNS = [
    # myGwork and LGBTQ platform wrappers
    re.compile(
        r"(?:This job is with|We are pleased to share this role on behalf of)\s+[^,\n]+,\s*(?:an inclusive employer and\s*)?(?:a\s+)?member of myGwork.*?(?:About the Role|About the Job|Job Description|The Role|Overview|Position Overview|Job Summary|Responsibilities|Requirements|Qualifications|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:Dedicated\s+)?(?:the\s+)?largest global (?:business\s+)?platform (?:and job board\s+)?for the LGBTQ\+?\s*(?:business\s*)?community[^\.\n]*[\.\n]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"myGwork is (?:the|a)\s+largest global platform[^\.\n]*[\.\n]?",
        re.IGNORECASE,
    ),
    # Recruiter disclaimers
    re.compile(
        r"(?:Please\s+)?do not contact the recruiter directly[^\.\n]*[\.\n]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:No\s+agencies|No\s+recruitment\s+agencies|No\s+agency\s+submissions?|Strictly\s+no\s+agencies|Direct\s+applicants\s+only|No\s+third\s*party\s*submissions)[^\.\n]*[\.\n]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"Unsolicited resumes (?:from search firms|from recruiters|submitted)[^\.\n]*[\.\n]?",
        re.IGNORECASE,
    ),
    # Job board attribution & navigation buttons
    re.compile(
        r"(?:Posted on|Originally posted on|Source:|Apply on|Easy Apply|Apply via)\s+(?:LinkedIn|Indeed|Glassdoor|myGwork|Monster|ZipRecruiter|Adzuna|Jooble|Dice)[^\.\n]*[\.\n]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:Apply Now|Easy Apply|Save Job|Share Job|Report this job|Back to search results|Page \d+ of \d+)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    # Tracking links / cookie / privacy UI
    re.compile(
        r"https?://(?:www\.)?(?:click\.|tracking\.|doubleclick\.|analytics\.)[^\s]+",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:This site uses cookies|Accept all cookies|Cookie preferences|Manage cookies|Privacy Settings)[^\.\n]*[\.\n]?",
        re.IGNORECASE,
    ),
]

# Noise lines to filter out line-by-line
_NOISE_LINE_PATTERNS = [
    re.compile(r"^(?:share|apply|save|print|email|favorite)\s*(?:job|this job|opportunity)?$", re.IGNORECASE),
    re.compile(r"^(?:sign in|log in|register|create account|search jobs|back to search)\b", re.IGNORECASE),
    re.compile(r"^copyright\s+©?\s*\d{4}.*all rights reserved\.?$", re.IGNORECASE),
    re.compile(r"^posted\s+\d+\s+(?:days?|hours?|weeks?|months?)\s+ago$", re.IGNORECASE),
    re.compile(r"^job\s+(?:id|req|reference|ref\s*#?)[:\s]+[a-zA-Z0-9_\-]+$", re.IGNORECASE),
]


def clean_html_and_entities(text: str) -> str:
    """Strip HTML markup and unescape HTML entities safely."""
    if not text:
        return ""
    # Unescape HTML entities first (e.g. &nbsp; &amp; &lt;)
    text = html.unescape(text)
    # Replace common HTML block elements with linebreaks to keep paragraphs
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</?(?:p|div|li|h[1-6]|tr)[^>]*>", "\n", text)
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def clean_job_description(raw_jd: str) -> PreprocessedJD:
    """
    Clean and preprocess a raw job description string.
    
    Removes third-party job board banners, recruiter contact disclaimers,
    and UI artifacts while preserving real job responsibilities, requirements,
    qualifications, and corporate EEO statements.
    """
    if not raw_jd or not raw_jd.strip():
        return PreprocessedJD(
            raw_text=raw_jd or "",
            cleaned_text="",
            analysis_quality="insufficient_job_description",
            quality_warning="Job description is empty. Please paste a complete job description.",
        )

    # 1. Clean HTML entities & tags
    text = clean_html_and_entities(raw_jd)

    # 2. Extract potential company/role from myGwork wrappers before removing wrapper
    detected_company = None
    detected_role = None

    company_match = re.search(
        r"This job is with\s+([^,\.\n]+),\s*(?:an inclusive employer|a member)",
        text,
        re.IGNORECASE,
    )
    if company_match:
        detected_company = company_match.group(1).strip()

    # 3. Apply third-party wrapper removals
    boilerplate_removed_count = 0
    for pattern in _THIRD_PARTY_WRAPPER_PATTERNS:
        while True:
            match = pattern.search(text)
            if not match:
                break
            boilerplate_removed_count += 1
            # If the wrapper ends with a genuine section header like "About the Role", keep the header
            matched_str = match.group(0)
            preserved_suffix = ""
            for header in ["About the Role", "About the Job", "Job Description", "The Role", "Responsibilities", "Overview", "Requirements"]:
                idx = matched_str.lower().rfind(header.lower())
                if idx != -1:
                    preserved_suffix = "\n" + matched_str[idx:]
                    break
            text = pattern.sub(preserved_suffix, text, count=1)

    # 4. Line by line noise filter
    lines = text.splitlines()
    cleaned_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        # Check against noise lines
        if any(np.match(stripped) for np in _NOISE_LINE_PATTERNS):
            boilerplate_removed_count += 1
            continue
        cleaned_lines.append(stripped)

    # 5. Normalize whitespace and paragraph spacing
    normalized_text = "\n".join(cleaned_lines)
    # Collapse 3+ newlines to 2
    normalized_text = re.sub(r"\n{3,}", "\n\n", normalized_text)
    # Collapse multiple spaces or tabs into a single space
    normalized_text = re.sub(r"[ \t]+", " ", normalized_text).strip()

    # 6. Quality assessment
    # Check length and presence of role-like content
    char_len = len(normalized_text)
    words = normalized_text.split()
    word_count = len(words)

    # Detect role signals
    has_role_indicators = bool(re.search(
        r"\b(?:responsibilities|qualifications|requirements|required|skills|experience|about the role|you will|what you'?ll do|minimum qualifications|preferred qualifications|key responsibilities|technologies|tools|duties|hiring|engineer|developer|role)\b",
        normalized_text,
        re.IGNORECASE,
    ))

    if char_len < 60 or word_count < 10:
        return PreprocessedJD(
            raw_text=raw_jd,
            cleaned_text=normalized_text,
            analysis_quality="insufficient_job_description",
            description_quality="PARTIAL",
            quality_warning="We couldn't find enough role requirements in this description. Paste the complete job description for a reliable analysis.",
            detected_company=detected_company,
            detected_role=detected_role,
            stripped_boilerplate_count=boilerplate_removed_count,
        )

    if not has_role_indicators and char_len < 150:
        return PreprocessedJD(
            raw_text=raw_jd,
            cleaned_text=normalized_text,
            analysis_quality="insufficient_job_description",
            description_quality="PARTIAL",
            quality_warning="This text appears to be an excerpt or navigation text rather than a full job description. Paste the complete job requirements for a reliable analysis.",
            detected_company=detected_company,
            detected_role=detected_role,
            stripped_boilerplate_count=boilerplate_removed_count,
        )

    # Check for truncated provider descriptions (e.g. Adzuna 500-char preview ending with ellipsis or cut mid-word)
    is_truncated = False
    raw_len = len(raw_jd.strip())
    if normalized_text.endswith(("…", "...")) or raw_jd.strip().endswith(("…", "...")):
        is_truncated = True
    elif raw_len == 500 or abs(raw_len - 500) <= 2:
        is_truncated = True
    elif char_len < 650 and re.search(r"\b(?:as|of|the|part of|in|and|to|for|with|or|is|a|an|at)\s*$", normalized_text, re.IGNORECASE):
        is_truncated = True

    if is_truncated:
        description_quality = "PARTIAL"
        quality_warning = "Your job provider supplied a shortened description. Paste the full job description for the most reliable analysis."
    else:
        description_quality = "FULL"
        quality_warning = None

    return PreprocessedJD(
        raw_text=raw_jd,
        cleaned_text=normalized_text,
        analysis_quality="sufficient",
        description_quality=description_quality,
        quality_warning=quality_warning,
        detected_company=detected_company,
        detected_role=detected_role,
        stripped_boilerplate_count=boilerplate_removed_count,
    )
