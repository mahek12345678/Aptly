"""Resume text extraction and deterministic structured parsing service.

Supports PDF (via PyMuPDF) and DOCX (via python-docx) extraction.
Implements a modular parsing architecture ready for LLM-assisted enhancement.
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Canonical section header aliases for deterministic boundary detection
SECTION_PATTERNS: dict[str, list[str]] = {
    "education": [
        "education",
        "academic background",
        "academics",
        "educational qualifications",
        "academic history",
        "degrees",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "internships",
        "relevant experience",
        "career history",
    ],
    "skills": [
        "skills",
        "technical skills",
        "skills & competencies",
        "core skills",
        "technologies",
        "expertise",
        "tools & technologies",
        "areas of expertise",
        "skills & abilities",
    ],
    "projects": [
        "projects",
        "personal projects",
        "academic projects",
        "key projects",
        "selected projects",
        "technical projects",
    ],
    "certifications": [
        "certifications",
        "licenses & certifications",
        "certificates",
        "credentials",
        "professional certifications",
    ],
    "achievements": [
        "achievements",
        "honors & awards",
        "awards & achievements",
        "accomplishments",
        "honors",
        "awards",
        "achievements & leadership",
        "leadership & achievements",
        "achievements and leadership",
        "leadership and achievements",
    ],
    "leadership": [
        "leadership",
        "leadership & involvement",
        "leadership experience",
        "leadership & activities",
        "positions of responsibility",
        "co-curricular",
        "extracurricular activities",
        "extracurriculars",
        "achievements & leadership",
        "leadership & achievements",
    ],
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "about me",
        "career summary",
        "executive summary",
        "objective",
    ],
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(
    r"(?:(?:\+?1\s*(?:[.-]\s*)?)?(?:\(\s*([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?([2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?([0-9]{4})(?:\s*(?:#|x\.?|ext\.?|extension)\s*(\d+))?|\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
)


def extract_raw_text(file_path: str | Path) -> str:
    """Extract clean text from a PDF or DOCX file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found at: {file_path}")

    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_from_pdf(path)
    elif ext == ".docx":
        return _extract_from_docx(path)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Only .pdf and .docx are supported.")


def _extract_from_pdf(path: Path) -> str:
    """Extract text from PDF using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    pages_text: list[str] = []
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text:
                pages_text.append(text)
    finally:
        doc.close()

    raw_text = "\n\n".join(pages_text)
    return _clean_text(raw_text)


def _extract_from_docx(path: Path) -> str:
    """Extract text from DOCX using python-docx."""
    import docx

    doc = docx.Document(str(path))
    paragraphs: list[str] = []

    for para in doc.paragraphs:
        line = para.text.strip()
        if line:
            paragraphs.append(line)

    # Extract text from tables if present
    for table in doc.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                # Deduplicate repeated text from merged cells
                deduped: list[str] = []
                for cell_text in row_cells:
                    if not deduped or deduped[-1] != cell_text:
                        deduped.append(cell_text)
                paragraphs.append(" | ".join(deduped))

    raw_text = "\n".join(paragraphs)
    return _clean_text(raw_text)


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove invisible control characters."""
    if not text:
        return ""
    # Strip null bytes and non-printable control characters (except newline, tab, carriage return)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize multiple line breaks
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class BaseResumeParser(ABC):
    """Abstract base class for resume parsing."""

    @abstractmethod
    def parse(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw text into structured resume fields."""
        pass


class DeterministicResumeParser(BaseResumeParser):
    """Deterministic, heuristic-based resume parser with section segmentation."""

    def parse(self, raw_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            return {
                "name": None,
                "email": None,
                "phone": None,
                "summary": None,
                "education": [],
                "skills": [],
                "experience": [],
                "projects": [],
                "certifications": [],
                "achievements": [],
                "leadership": [],
                "sections": {},
                "raw_text": raw_text,
            }

        # 1. Segment text into sections based on recognized headers
        sections = self._segment_sections(lines)

        # 2. Extract contact info from header block or anywhere in raw text
        header_lines = sections.get("header", [])
        email = self._extract_email(raw_text)
        phone = self._extract_phone(raw_text)
        name = self._extract_name(header_lines, email)
        headline = self._extract_headline(header_lines, name)

        # 3. Parse individual structured components
        skills, skill_categories = self._parse_skills(sections.get("skills", []))
        education = self._parse_education(sections.get("education", []))
        experience = self._parse_experience(sections.get("experience", []))
        projects = self._parse_projects(sections.get("projects", []))
        certifications = self._parse_items(sections.get("certifications", []))
        achievements = self._parse_items(sections.get("achievements", []))
        leadership = self._parse_items(sections.get("leadership", []))
        summary = "\n".join(sections.get("summary", [])).strip() or None

        # Build clean section texts
        section_texts: dict[str, str] = {}
        for sec_name, sec_lines in sections.items():
            if sec_lines:
                section_texts[sec_name] = "\n".join(sec_lines)

        return {
            "name": name,
            "headline": headline,
            "email": email,
            "phone": phone,
            "summary": summary,
            "education": education,
            "skills": skills,
            "skill_categories": skill_categories,
            "experience": experience,
            "projects": projects,
            "certifications": certifications,
            "achievements": achievements,
            "leadership": leadership,
            "sections": section_texts,
            "raw_text": raw_text,
        }

    def _clean_token(self, text: str) -> str:
        """Clean tokenization / linebreak artifacts from skill, bullet, or title."""
        if not text:
            return ""
        # 1. Join hyphenated words split by newline: e.g. 'client-\nside' -> 'client-side'
        t = re.sub(r"(\b\w+)-\s*\n\s*(\w+\b)", r"\1-\2", text)
        # 2. Join words split by newline without hyphens: e.g. 'client\nside' -> 'client side'
        t = re.sub(r"(\b\w+)\s*\n\s*(\w+\b)", r"\1 \2", t)
        # 3. Collapse internal whitespace
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\s*\n\s*", " ", t)
        # 4. Strip surrounding bullets, hashtags, spaces
        t = re.sub(r"^[#*_\-\s|•▪–—>:]+|[#*_\-\s|•▪–—>:]+$", "", t)
        return t.strip()

    def _is_skill_category_line(self, line: str) -> bool:
        """Detect if line is a skill category header like 'Languages | ...' or 'Backend & Web | ...'"""
        pattern = r"^(?:languages|programming\s*languages|backend|backend\s*&\s*web|data\s*&\s*systems|tools\s*&\s*cloud|databases?|frameworks?|cloud\s*&\s*devops|web\s*technologies|frontend|technical\s*skills|core\s*skills|libraries)\s*[|:]"
        return bool(re.match(pattern, line.strip(), re.IGNORECASE))

    def _segment_sections(self, lines: list[str]) -> dict[str, list[str]]:
        """Identify section headings and group lines under appropriate sections."""
        sections: dict[str, list[str]] = {"header": []}
        current_section = "header"

        for line in lines:
            clean = line.strip()
            if not clean:
                continue

            # If line is a skill category definition, always route to skills section
            if self._is_skill_category_line(clean):
                current_section = "skills"
                sections.setdefault("skills", []).append(clean)
                continue

            matched_section = self._match_section_header(clean)
            if matched_section:
                current_section = matched_section
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections.setdefault(current_section, []).append(clean)

        return sections

    def _match_section_header(self, line: str) -> Optional[str]:
        """Check if a line looks like a known section header."""
        clean_line = re.sub(r"^[#*_\-\s:]+|[#*_\-\s:]+$", "", line).strip().lower()
        if len(clean_line) > 45 or len(clean_line.split()) > 5:
            return None

        for section_key, aliases in SECTION_PATTERNS.items():
            for alias in aliases:
                if clean_line == alias or clean_line.startswith(f"{alias}:"):
                    return section_key

        return None

    def _extract_email(self, text: str) -> Optional[str]:
        match = EMAIL_REGEX.search(text)
        return match.group(0).strip() if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        match = PHONE_REGEX.search(text)
        if match:
            clean = match.group(0).strip()
            digits = re.sub(r"\D", "", clean)
            if 7 <= len(digits) <= 15:
                return clean
        return None

    def _extract_name(self, header_lines: list[str], email: Optional[str]) -> Optional[str]:
        """Infer candidate's name from early lines in the resume."""
        for line in header_lines[:5]:
            clean = re.sub(r"^[#*_\-\s]+|[#*_\-\s]+$", "", line).strip()
            if not clean:
                continue
            if email and email.lower() in clean.lower():
                continue
            if "@" in clean or "http" in clean.lower() or "github.com" in clean.lower() or "linkedin.com" in clean.lower():
                continue
            if PHONE_REGEX.search(clean):
                continue
            words = clean.split()
            if 1 <= len(words) <= 4 and len(clean) <= 40 and all(w[0].isalpha() for w in words if w):
                return clean
        return None

    def _extract_headline(self, header_lines: list[str], name: Optional[str]) -> Optional[str]:
        """Infer candidate headline/role from header lines."""
        for line in header_lines[:5]:
            clean = re.sub(r"^[#*_\-\s]+|[#*_\-\s]+$", "", line).strip()
            if not clean:
                continue
            if name and clean.lower() == name.lower():
                continue
            if "@" in clean or "http" in clean.lower() or "github.com" in clean.lower() or "linkedin.com" in clean.lower():
                continue
            if PHONE_REGEX.search(clean):
                continue
            # Must not be a location alone
            return clean
        return None

    def _parse_skills(self, lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
        """Extract a structured deduplicated list of skills and canonical category groupings."""
        skills: list[str] = []
        skill_categories: dict[str, list[str]] = {}

        for line in lines:
            category: Optional[str] = None
            items: str = line

            if "|" in line:
                cat_part, _, rest = line.partition("|")
                if len(cat_part.strip().split()) <= 5:
                    category = self._clean_token(cat_part.strip())
                    items = rest
            elif ":" in line:
                cat_part, _, rest = line.partition(":")
                if len(cat_part.strip().split()) <= 5:
                    category = self._clean_token(cat_part.strip())
                    items = rest

            parts = re.split(r"[,•;·\t]+", items)
            cat_skills: list[str] = []

            for part in parts:
                clean = self._clean_token(part)
                # Never treat the category name itself as a skill
                if category and clean.lower() == category.lower():
                    continue
                if clean and len(clean) <= 60 and clean.lower() not in [s.lower() for s in skills]:
                    skills.append(clean)
                    cat_skills.append(clean)

            if category and cat_skills:
                existing_cat = next((c for c in skill_categories if c.lower() == category.lower()), None)
                if existing_cat:
                    for s in cat_skills:
                        if s.lower() not in [x.lower() for x in skill_categories[existing_cat]]:
                            skill_categories[existing_cat].append(s)
                else:
                    skill_categories[category] = cat_skills

        return skills, skill_categories

    def _parse_items(self, lines: list[str]) -> list[str]:
        """Group lines into distinct items/entries (by blank line, bullet points, or entries)."""
        items: list[str] = []
        current_item_lines: list[str] = []

        for line in lines:
            clean = line.strip()
            if not clean:
                continue

            is_bullet = clean.startswith(("-", "*", "•", "▪", "–", "—", ">"))
            bullet_clean = self._clean_token(clean)
            if is_bullet and current_item_lines:
                item_text = self._clean_token(" ".join(current_item_lines))
                if item_text:
                    items.append(item_text)
                current_item_lines = [bullet_clean]
            else:
                if bullet_clean:
                    current_item_lines.append(bullet_clean)

        if current_item_lines:
            item_text = self._clean_token(" ".join(current_item_lines))
            if item_text:
                items.append(item_text)

        if not items and lines:
            items = [self._clean_token(l) for l in lines if self._clean_token(l)]

        return items

    def _parse_education(self, lines: list[str]) -> list[dict[str, Any]]:
        """Parse education lines into structured education objects with institution, degree, and grad_year."""
        if not lines:
            return []

        entries: list[dict[str, Any]] = []
        for line in lines:
            clean = self._clean_token(line)
            if not clean or clean.lower().startswith("cgpa") or clean.lower().startswith("relevant coursework"):
                continue

            segments = [s.strip() for s in clean.split("|") if s.strip()]
            main_part = segments[0] if segments else clean

            dash_match = re.search(r"[\u2014\u2013\u2012–—]|\s+-\s+", main_part)
            if dash_match:
                inst = main_part[:dash_match.start()].strip()
                degree = main_part[dash_match.end():].strip()
            else:
                inst = main_part.strip()
                degree = ""

            year_matches = re.findall(r"\b(202[0-9]|203[0-9])\b", clean)
            grad_year = year_matches[-1] if year_matches else ""
            dates = ""
            date_range_match = re.search(r"(\d{4}\s*[\u2014\u2013\u2012–—\-]\s*\d{4})", clean)
            if date_range_match:
                dates = date_range_match.group(1)

            entries.append({
                "institution": inst or "University",
                "degree": degree,
                "grad_year": grad_year,
                "dates": dates or grad_year,
                "entry": clean,
            })

        return entries

    def _parse_experience(self, lines: list[str]) -> list[dict[str, Any]]:
        """
        Group lines into distinct experience entries, keeping company, role, location,
        date range (e.g. 'May 2026 – Jul 2026'), and bullets properly associated.
        """
        if not lines:
            return []

        entries: list[dict[str, Any]] = []
        current: Optional[dict[str, Any]] = None

        for line in lines:
            clean = line.strip()
            if not clean:
                continue

            is_bullet = clean.startswith(("-", "*", "•", "▪", "–", "—", ">"))
            bullet_text = re.sub(r"^[-*•▪–—>\s]+", "", clean).strip()

            if is_bullet:
                if current is None:
                    current = {
                        "company": "Organization",
                        "role": "Software Engineer",
                        "location": "",
                        "dates": "",
                        "start_date": "",
                        "end_date": "",
                        "bullets": [],
                    }
                if bullet_text:
                    current["bullets"].append(self._clean_token(bullet_text))
            else:
                if current and (current["bullets"] or current["company"] != "Organization"):
                    self._finalize_experience(current)
                    entries.append(current)

                current = self._parse_experience_header(clean)

        if current:
            self._finalize_experience(current)
            entries.append(current)

        return entries

    def _parse_experience_header(self, header: str) -> dict[str, Any]:
        """Parse experience header into structured metadata."""
        clean = self._clean_token(header)
        segments = [s.strip() for s in clean.split("|") if s.strip()]

        date_pattern = re.compile(
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b|\b\d{4}\b",
            re.IGNORECASE,
        )
        dates = ""
        location = ""
        non_date_segments: list[str] = []

        for seg in segments:
            if date_pattern.search(seg) and re.search(r"\b\d{4}\b|\bpresent\b", seg, re.IGNORECASE):
                dates = seg
            elif any(
                re.search(r"\b" + re.escape(loc_word) + r"\b", seg, re.IGNORECASE)
                for loc_word in [
                    "india", "usa", "uk", "bengaluru", "bangalore", "surat", "mumbai",
                    "delhi", "pune", "hyderabad", "san francisco", "remote", "hybrid",
                    "ca", "ny", "wa", "tx"
                ]
            ):
                location = seg
            else:
                non_date_segments.append(seg)

        first_part = non_date_segments[0] if non_date_segments else clean
        role = ""
        company = ""

        dash_match = re.search(r"[\u2014\u2013\u2012–—]|\s+-\s+", first_part)
        if dash_match:
            p1 = first_part[:dash_match.start()].strip()
            p2 = first_part[dash_match.end():].strip()
        else:
            p1, p2 = first_part.strip(), ""

        p1, p2 = p1.strip(), p2.strip()
        role_keywords = [
            "intern", "engineer", "developer", "lead", "manager", "consultant",
            "analyst", "architect", "fellow", "associate", "specialist"
        ]

        if any(k in p1.lower() for k in role_keywords):
            role = p1
            company = p2
        elif any(k in p2.lower() for k in role_keywords):
            company = p1
            role = p2
        else:
            role = p1
            company = p2 or "Organization"

        if not location and len(non_date_segments) > 1:
            location = non_date_segments[1]

        start_date = ""
        end_date = ""
        if dates:
            d_parts = re.split(r"[–—\-]|(?:\s+to\s+)", dates)
            if len(d_parts) >= 2:
                start_date = d_parts[0].strip()
                end_date = d_parts[1].strip()
            elif len(d_parts) == 1:
                start_date = d_parts[0].strip()

        return {
            "company": company or "Organization",
            "role": role or "Software Engineer",
            "location": location,
            "dates": dates,
            "start_date": start_date,
            "end_date": end_date,
            "bullets": [],
            "header": header,
        }

    def _finalize_experience(self, exp: dict[str, Any]) -> None:
        company = exp.get("company", "Organization")
        role = exp.get("role", "Software Engineer")
        location = exp.get("location", "")
        dates = exp.get("dates", "")
        bullets = exp.get("bullets", [])

        parts = [p for p in [company, role, location, dates] if p]
        header_line = " | ".join(parts)
        if bullets:
            exp["entry"] = header_line + "\n" + "\n".join(f"- {b}" for b in bullets)
        else:
            exp["entry"] = header_line

    def _parse_projects(self, lines: list[str]) -> list[dict[str, Any]]:
        """
        Group lines into distinct project entities (ResumeProject model), preserving:
        project_id, title, technologies, links, bullets.
        Never creates projects from section headers, skills, or achievements.
        """
        if not lines:
            return []

        projects: list[dict[str, Any]] = []
        current_project: Optional[dict[str, Any]] = None

        for line in lines:
            clean = line.strip()
            if not clean:
                continue

            # Stop or skip if an accidental section or skill category line appears
            if self._is_skill_category_line(clean) or self._match_section_header(clean):
                continue

            clean_proj_match = re.match(r"^(?:project\s*\d*\s*[:\-]\s*|project\s*[:\-]\s*)", clean, re.IGNORECASE)
            if clean_proj_match:
                clean = clean[clean_proj_match.end():].strip()
                if not clean:
                    continue

            is_bullet = clean.startswith(("-", "*", "•", "▪", "–", "—", ">"))
            bullet_content = self._clean_token(re.sub(r"^[-*•▪–—>\s]+", "", clean).strip())

            tech_match = re.match(r"^(?:tech|technologies|stack|tools)\s*[:\-]\s*(.*)$", clean, re.IGNORECASE)
            link_match = re.match(r"^(?:links?|url|github|demo)\s*[:\-]\s*(.*)$", clean, re.IGNORECASE)
            bullets_header_match = re.match(r"^bullets\s*[:\-]\s*$", clean, re.IGNORECASE)

            if bullets_header_match:
                continue

            if is_bullet:
                if current_project is None:
                    current_project = {
                        "project_id": f"proj_{len(projects) + 1}",
                        "title": "Project",
                        "project_title": "Project",
                        "technologies": [],
                        "project_technologies": [],
                        "links": [],
                        "bullets": [],
                        "project_bullets": [],
                        "header": "Project",
                    }
                if bullet_content:
                    current_project["bullets"].append(bullet_content)
                    current_project["project_bullets"].append(bullet_content)
            elif tech_match and current_project:
                tech_str = tech_match.group(1).strip()
                techs = [self._clean_token(t) for t in re.split(r"[,•|;]+", tech_str) if self._clean_token(t)]
                current_project["technologies"].extend(techs)
                current_project["project_technologies"].extend(techs)
            elif link_match and current_project:
                link_str = link_match.group(1).strip()
                links = [l.strip() for l in re.split(r"[,•|\s]+", link_str) if l.strip()]
                current_project["links"].extend(links)
            else:
                is_pure_tech_line = False
                if current_project and not current_project["bullets"]:
                    potential_techs = [self._clean_token(t) for t in re.split(r"[,•|;]+", clean) if self._clean_token(t)]
                    if len(potential_techs) >= 2 and all(len(t.split()) <= 3 for t in potential_techs):
                        is_pure_tech_line = True

                if is_pure_tech_line and current_project:
                    potential_techs = [self._clean_token(t) for t in re.split(r"[,•|;]+", clean) if self._clean_token(t)]
                    current_project["technologies"].extend(potential_techs)
                    current_project["project_technologies"].extend(potential_techs)
                else:
                    if current_project and (current_project["bullets"] or current_project["title"] != "Project"):
                        self._finalize_project(current_project)
                        projects.append(current_project)

                    title_part = clean
                    tech_part = ""
                    if "|" in clean:
                        title_part, _, tech_part = clean.partition("|")
                    elif " - " in clean and not clean.startswith("-"):
                        title_part, _, tech_part = clean.partition(" - ")
                    elif ":" in clean:
                        title_part, _, tech_part = clean.partition(":")

                    title = self._clean_token(title_part)
                    technologies = [self._clean_token(t) for t in re.split(r"[,•|;]+", tech_part) if self._clean_token(t)]

                    current_project = {
                        "project_id": f"proj_{len(projects) + 1}",
                        "title": title,
                        "project_title": title,
                        "technologies": technologies,
                        "project_technologies": technologies,
                        "links": [],
                        "bullets": [],
                        "project_bullets": [],
                        "header": clean,
                    }

        if current_project:
            self._finalize_project(current_project)
            projects.append(current_project)

        # Ensure unique projects by title and deduplicate
        unique_projects: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for p in projects:
            norm_title = p.get("title", "").strip().lower()
            if norm_title and norm_title not in seen_titles:
                seen_titles.add(norm_title)
                p["project_id"] = f"proj_{len(unique_projects) + 1}"
                unique_projects.append(p)

        return unique_projects

        return projects

    def _finalize_project(self, proj: dict[str, Any]) -> None:
        header = proj.get("header") or proj.get("title") or proj.get("project_title", "Project")
        bullets = proj.get("bullets", []) or proj.get("project_bullets", [])
        proj["bullets"] = bullets
        proj["project_bullets"] = bullets
        proj["title"] = proj.get("title") or proj.get("project_title") or header
        proj["project_title"] = proj["title"]
        proj["technologies"] = proj.get("technologies") or proj.get("project_technologies", [])
        proj["project_technologies"] = proj["technologies"]
        proj["links"] = proj.get("links", [])
        if bullets:
            proj["description"] = f"{header}: {' '.join(bullets)}"
            proj["entry"] = f"{header}\n" + "\n".join(f"- {b}" for b in bullets)
        else:
            proj["description"] = header
            proj["entry"] = header


# Default parser instance
resume_parser = DeterministicResumeParser()
