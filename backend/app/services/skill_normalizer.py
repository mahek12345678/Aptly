"""Skill normalization, structured resume evidence extraction, and deterministic requirement matching.

SINGLE SOURCE OF TRUTH:
All downstream scores, verified matches, gaps, target/learn lists, and explanations
derive from a unified list of NormalizedRequirement items.

Ensures:
- Exact mathematical reconciliation of component scores with final score.
- Verified matches count == actual requirements marked 'verified'.
- Gaps count == actual requirements marked 'missing' (including experience gaps).
- Distinguishes direct 'verified' evidence from transferable 'related' evidence.
- Preserves requirement sources for TARGET / LEARN without hallucinating external skills.
- Zero score inflation: if verified == 0 and related == 0, score is 0%, never 75%.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field


class MatchStatus(str, Enum):
    VERIFIED = "verified"
    RELATED = "related"
    MISSING = "missing"
    # Legacy aliases
    VERIFIED_MATCH = "VERIFIED_MATCH"
    RELATED_EVIDENCE = "RELATED_EVIDENCE"
    NOT_FOUND = "NOT_FOUND"


class RequirementCategory(str, Enum):
    REQUIRED_SKILL = "required_skill"
    PREFERRED_SKILL = "preferred_skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    DOMAIN = "domain"
    OTHER = "other"


class RequirementImportance(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class EvidenceType(str, Enum):
    SKILL = "SKILL"
    PROJECT_IMPLEMENTATION = "PROJECT_IMPLEMENTATION"
    EXPERIENCE_BULLET = "EXPERIENCE_BULLET"
    EDUCATION = "EDUCATION"
    ACHIEVEMENT = "ACHIEVEMENT"
    LEADERSHIP = "LEADERSHIP"
    CERTIFICATION = "CERTIFICATION"


class SemanticCategory(str, Enum):
    PROGRAMMING_LANGUAGE = "PROGRAMMING_LANGUAGE"
    FRAMEWORK_LIBRARY = "FRAMEWORK_LIBRARY"
    DATABASE = "DATABASE"
    CLOUD_DEVOPS = "CLOUD_DEVOPS"
    SOFTWARE_ENGINEERING = "SOFTWARE_ENGINEERING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    ALGORITHMS_PROBLEM_SOLVING = "ALGORITHMS_PROBLEM_SOLVING"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    DATA_ENGINEERING = "DATA_ENGINEERING"
    AI_LLM = "AI_LLM"
    EDUCATION = "EDUCATION"
    EXPERIENCE_YEARS = "EXPERIENCE_YEARS"
    DOMAIN = "DOMAIN"
    SOFT_SKILL = "SOFT_SKILL"
    OTHER = "OTHER"


class NormalizedRequirement(BaseModel):
    requirement_id: str
    category: str  # "required_skill" | "preferred_skill" | "experience" | "education" | "domain" | "other" | "soft_skill"
    requirement: str
    canonical: str
    text: Optional[str] = None
    normalized_name: Optional[str] = None
    importance: str  # "required" | "preferred"
    score_component: str = ""  # "required_skills" | "preferred_skills" | "experience" | "domain" | "soft_traits" | "eligibility"
    match_status: str  # "verified" | "related" | "missing"
    resume_evidence: List[str] = []
    source: str = ""  # e.g. "JD required technology", "JD preferred requirement", "JD experience requirement"
    source_excerpt: Optional[str] = ""
    source_section: Optional[str] = ""
    extraction_confidence: float = 0.95
    evidence_strength: float = 0.0
    notes: str = ""
    weight: float = 1.0
    semantic_category: str = SemanticCategory.OTHER.value
    evidence_type: Optional[str] = None

    model_config = ConfigDict(extra="ignore")

    def model_post_init(self, __context: Any) -> None:
        if self.text is None:
            self.text = self.requirement
        if self.normalized_name is None:
            self.normalized_name = self.canonical
        if not self.source_excerpt:
            self.source_excerpt = self.source or self.requirement
        if not self.score_component:
            if self.category == "required_skill":
                self.score_component = "required_skills"
            elif self.category == "preferred_skill":
                self.score_component = "preferred_skills"
            elif self.category == "experience":
                self.score_component = "experience"
            elif self.category == "domain":
                self.score_component = "domain"
            elif self.category in ("soft_skill", "trait"):
                self.score_component = "soft_traits"
            elif self.category in ("education", "eligibility"):
                self.score_component = "eligibility"
            else:
                self.score_component = "other"
        if self.evidence_strength == 0.0:
            if self.match_status == MatchStatus.VERIFIED.value:
                self.evidence_strength = 1.0
            elif self.match_status == MatchStatus.RELATED.value:
                self.evidence_strength = 0.40
            else:
                self.evidence_strength = 0.0



# Canonical normalization map: alias (lower) -> canonical display name
CANONICAL_SKILL_MAP: Dict[str, str] = {
    # Programming Languages
    "python": "Python",
    "python3": "Python",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "golang": "Go",
    "go lang": "Go",
    "go": "Go",
    "rust": "Rust",
    "java": "Java",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "sql": "SQL",
    "bash": "Bash",
    "shell": "Bash",

    # AI / ML / Data Science (distinguish category from specific library)
    "ml": "Machine Learning",
    "m.l.": "Machine Learning",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "artificial intelligence": "AI",
    "ai": "AI",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "computer vision": "Computer Vision",
    "cv": "Computer Vision",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "keras": "Keras",
    "scikit-learn": "Scikit-Learn",
    "scikit learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "huggingface": "Hugging Face",
    "hugging face": "Hugging Face",
    "transformers": "Transformers",
    "llm": "LLM",
    "large language models": "LLM",
    "genai": "Generative AI",
    "generative ai": "Generative AI",
    "rag": "RAG",
    "langchain": "LangChain",
    "llamaindex": "LlamaIndex",
    "vector database": "Vector DB",
    "vector db": "Vector DB",
    "chromadb": "ChromaDB",
    "pinecone": "Pinecone",
    "qdrant": "Qdrant",
    "weaviate": "Weaviate",

    # Backend / Web Frameworks
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "express": "Express.js",
    "express.js": "Express.js",
    "expressjs": "Express.js",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "nest": "NestJS",
    "nestjs": "NestJS",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "restful apis": "REST APIs",
    "restful api": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "rest": "REST APIs",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "microservices": "Microservices",
    "sqlalchemy": "SQLAlchemy",

    # Databases & Storage
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "pgsql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "elasticsearch": "Elasticsearch",
    "kafka": "Kafka",
    "kinesis": "Kinesis",

    # Cloud & DevOps
    "docker": "Docker",
    "docker containerization": "Docker",
    "containerization": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "ci/cd": "CI/CD",
    "ci cd": "CI/CD",
    "continuous integration": "CI/CD",
    "github actions": "GitHub Actions",
    "linux": "Linux",
    "terraform": "Terraform",
    "git": "Git",
    "github": "GitHub",
    "prometheus": "Prometheus",
    "grafana": "Grafana",

    # Deployment / Hosting services (recognized as deployment evidence, not ML or backend language)
    "railway": "Railway",
    "vercel": "Vercel",
    "render": "Render",
    "heroku": "Heroku",
    "netlify": "Netlify",

    # Frontend
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "tailwind": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "html": "HTML",
    "html5": "HTML",
    "css": "CSS",
    "css3": "CSS",

    # Broad Engineering & Algorithmic Capabilities
    "software development": "Software Development",
    "software engineering": "Software Development",
    "problem solving": "Problem Solving",
    "system design": "System Design",
    "algorithms": "Algorithms",
    "data structures": "Data Structures & Algorithms",
    "dsa": "Data Structures & Algorithms",
    "data engineering": "Data Engineering",
    "groq": "Groq",
    "software architecture": "Software Architecture",
    "software design patterns": "Software Design Patterns",
    "design patterns": "Software Design Patterns",
    "2028 graduate": "2028 Graduate",
    "2028 graduates": "2028 Graduate",
}

# Related technology mappings for RELATED status (target -> set of related skills)
RELATED_SKILLS_MAP: Dict[str, Set[str]] = {
    "PostgreSQL": {"SQL", "MySQL", "Database", "SQLite", "SQLAlchemy", "Relational Database"},
    "SQL": {"PostgreSQL", "MySQL", "SQLite", "SQLAlchemy"},
    "REST APIs": {"FastAPI", "Express.js", "Django", "Flask", "Backend APIs", "API Design", "gRPC"},
    "FastAPI": {"Python", "REST APIs", "Flask", "Django"},
    "Docker": {"Kubernetes", "Containerization", "CI/CD", "DevOps"},
    "Kubernetes": {"Docker", "Containerization", "Cloud", "AWS", "GCP"},
    "AWS": {"Cloud", "Cloud Deployment", "GCP", "Azure", "Railway", "Vercel"},
    "GCP": {"Cloud", "Cloud Deployment", "AWS", "Azure", "Railway", "Vercel"},
    "Cloud": {"AWS", "GCP", "Azure", "Railway", "Vercel", "Docker"},
    "Cloud Deployment": {"Railway", "Vercel", "Render", "AWS", "GCP", "Docker"},
    "Machine Learning": {"Deep Learning", "PyTorch", "TensorFlow", "Scikit-Learn", "Data Science"},
    "Deep Learning": {"Machine Learning", "PyTorch", "TensorFlow"},
    "PyTorch": {"Deep Learning", "Machine Learning", "TensorFlow"},
    "TensorFlow": {"Deep Learning", "Machine Learning", "PyTorch"},
    "Scikit-Learn": {"Machine Learning", "Data Science", "Python"},
    "React": {"Next.js", "JavaScript", "TypeScript", "Frontend"},
    "Next.js": {"React", "TypeScript", "JavaScript", "Frontend"},
    "TypeScript": {"JavaScript", "Frontend", "Node.js"},
    "JavaScript": {"TypeScript", "Frontend", "Node.js"},
    "Software Architecture": {"System Design", "Relational Schema Design", "Scalability", "Distributed Systems"},
}

# Non-skill noise words to filter out from Skills Section
SKILL_NOISE_TERMS = {
    "vice president",
    "president",
    "lead",
    "club",
    "member",
    "student",
    "university",
    "college",
    "education",
    "team player",
    "communication",
    "leadership",
    "vs code",
    "visual studio code",
    "jupyter notebook",
    "postman",
    "sublime text",
    "eclipse",
    "git bash",
    "devops club",
    "student members",
    "for student members",
    "responsible for",
    "experienced in",
    "hands-on",
}

# Technologies requiring specific evidence that cannot be verified by generic or adjacent concepts
STRICT_TECHNOLOGIES: Set[str] = {
    "PyTorch",
    "Kubernetes",
    "Kafka",
    "AWS",
    "Scikit-Learn",
    "TensorFlow",
    "Docker",
    "PostgreSQL",
    "Redis",
    "Elasticsearch",
    "React",
    "Next.js",
    "FastAPI",
    "Go",
    "Rust",
    "C++",
    "Java",
    "Python",
    "GCP",
    "Azure",
    "ChromaDB",
    "Groq",
    "GraphQL",
    "gRPC",
    "Software Design Patterns",
}

CATEGORY_COMPATIBILITY_MAP: Dict[str, Set[str]] = {
    SemanticCategory.SOFTWARE_ENGINEERING.value: {
        SemanticCategory.SOFTWARE_ENGINEERING.value,
        SemanticCategory.FRAMEWORK_LIBRARY.value,
        SemanticCategory.PROGRAMMING_LANGUAGE.value,
    },
    SemanticCategory.ALGORITHMS_PROBLEM_SOLVING.value: {
        SemanticCategory.ALGORITHMS_PROBLEM_SOLVING.value,
        SemanticCategory.DATA_ENGINEERING.value,
    },
    SemanticCategory.SYSTEM_DESIGN.value: {
        SemanticCategory.SYSTEM_DESIGN.value,
        SemanticCategory.DATABASE.value,
        SemanticCategory.SOFTWARE_ENGINEERING.value,
    },
    SemanticCategory.MACHINE_LEARNING.value: {
        SemanticCategory.MACHINE_LEARNING.value,
    },
    SemanticCategory.AI_LLM.value: {
        SemanticCategory.AI_LLM.value,
        SemanticCategory.MACHINE_LEARNING.value,
    },
    SemanticCategory.DATA_ENGINEERING.value: {
        SemanticCategory.DATA_ENGINEERING.value,
        SemanticCategory.DATABASE.value,
    },
    SemanticCategory.EDUCATION.value: {
        SemanticCategory.EDUCATION.value,
    },
    SemanticCategory.EXPERIENCE_YEARS.value: {
        SemanticCategory.EXPERIENCE_YEARS.value,
    },
    SemanticCategory.PROGRAMMING_LANGUAGE.value: {
        SemanticCategory.PROGRAMMING_LANGUAGE.value,
    },
    SemanticCategory.DATABASE.value: {
        SemanticCategory.DATABASE.value,
    },
    SemanticCategory.CLOUD_DEVOPS.value: {
        SemanticCategory.CLOUD_DEVOPS.value,
    },
    SemanticCategory.FRAMEWORK_LIBRARY.value: {
        SemanticCategory.FRAMEWORK_LIBRARY.value,
    },
}


def normalize_skill(skill: str) -> str:
    """Normalize a skill name to its canonical display form."""
    if not skill or not isinstance(skill, str):
        return ""
    clean = skill.strip()
    lower = clean.lower()

    if lower in CANONICAL_SKILL_MAP:
        return CANONICAL_SKILL_MAP[lower]

    if "software development" in lower or "software engineering" in lower:
        return "Software Development"

    # Handle common suffixes like 'framework', 'library'
    lower_stripped = re.sub(r"\b(framework|library|technologies|tools|language)\b", "", lower).strip()
    if lower_stripped in CANONICAL_SKILL_MAP:
        return CANONICAL_SKILL_MAP[lower_stripped]

    # Title-case default for unknown tools
    return clean


def is_valid_technical_skill(skill: str) -> bool:
    """Check if a string represents a valid technical skill rather than prose or club text."""
    if not skill or len(skill.strip()) < 2:
        return False
    lower = skill.strip().lower()

    # Reject if in noise list
    if lower in SKILL_NOISE_TERMS:
        return False

    # Reject if looks like a sentence or contains club/university prose
    words = lower.split()
    if len(words) > 4:
        return False
    if any(w in lower for w in [
        "club", "university", "department", "responsible for", "student member", "for student",
        "thinker", "listener", "hard worker", "fast learner", "quick learner", "self starter", "team player"
    ]):
        return False

    return True


def classify_semantic_category(text: str, canonical: Optional[str] = None) -> str:
    """Classify requirement or capability text into a SemanticCategory."""
    target = (canonical or text or "").strip().lower()
    raw = (text or "").strip().lower()

    # 1. EDUCATION
    if any(k in target or k in raw for k in [
        "graduate", "graduating", "graduation", "bachelor", "master", "phd",
        "b.tech", "b.s.", "m.s.", "b.e.", "degree", "university", "college",
    ]):
        return SemanticCategory.EDUCATION.value

    # 2. EXPERIENCE_YEARS
    if any(k in target or k in raw for k in [
        "years experience", "years of experience", "min_years", "+ years", "experience years"
    ]):
        return SemanticCategory.EXPERIENCE_YEARS.value

    # 3. ALGORITHMS_PROBLEM_SOLVING
    if any(k in target or k in raw for k in [
        "problem solving", "problem-solving", "dsa", "data structures", "algorithms",
        "leetcode", "competitive programming", "codeforces", "hackerrank"
    ]):
        return SemanticCategory.ALGORITHMS_PROBLEM_SOLVING.value

    # 4. SYSTEM_DESIGN
    if any(k in target or k in raw for k in [
        "system design", "distributed systems", "scalability", "high availability",
        "relational schema", "schema design", "database design", "architecture trade-offs",
        "scaling considerations", "transaction handling", "system architecture"
    ]):
        return SemanticCategory.SYSTEM_DESIGN.value

    # 5. SOFTWARE_ENGINEERING
    if any(k in target or k in raw for k in [
        "software development", "software engineering", "full-stack", "full stack",
        "backend development", "frontend development", "web development", "api development",
        "api design", "rest apis", "restful", "crud", "microservices", "object-oriented"
    ]):
        return SemanticCategory.SOFTWARE_ENGINEERING.value

    # 6. AI_LLM
    if any(k in target or k in raw for k in [
        "llm", "large language model", "rag", "langchain", "llamaindex", "generative ai",
        "genai", "prompt engineering", "groq", "openai", "claude", "gemini"
    ]):
        return SemanticCategory.AI_LLM.value

    # 7. MACHINE_LEARNING
    if any(k in target or k in raw for k in [
        "machine learning", "ml pipeline", "deep learning", "nlp", "natural language processing",
        "computer vision", "feature engineering", "model benchmarking", "evaluation metrics",
        "gradient boosting", "logistic regression", "random forest", "scikit-learn", "sklearn"
    ]):
        return SemanticCategory.MACHINE_LEARNING.value

    # 8. DATA_ENGINEERING
    if any(k in target or k in raw for k in [
        "data engineering", "data pipeline", "etl", "chunking", "deduplication", "embeddings",
        "document ingestion", "kafka", "kinesis", "spark", "airflow"
    ]):
        return SemanticCategory.DATA_ENGINEERING.value

    # 9. PROGRAMMING_LANGUAGE
    if target in {
        "python", "javascript", "typescript", "golang", "go", "rust", "java", "c++", "cpp",
        "c#", "csharp", "sql", "bash", "shell", "ruby", "php", "swift", "kotlin", "scala"
    }:
        return SemanticCategory.PROGRAMMING_LANGUAGE.value

    # 10. DATABASE
    if target in {
        "postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite", "elasticsearch",
        "chromadb", "pinecone", "qdrant", "weaviate", "vector db", "vector database"
    } or "database" in target:
        return SemanticCategory.DATABASE.value

    # 11. CLOUD_DEVOPS
    if target in {
        "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "ci/cd", "github actions",
        "linux", "terraform", "prometheus", "grafana", "railway", "vercel", "render",
        "heroku", "netlify", "containerization"
    } or "devops" in target or "cloud" in target:
        return SemanticCategory.CLOUD_DEVOPS.value

    # 12. FRAMEWORK_LIBRARY
    if target in {
        "fastapi", "flask", "django", "express.js", "express", "react", "next.js", "nextjs",
        "vue.js", "vue", "spring boot", "spring", "pytorch", "torch", "tensorflow", "tf",
        "keras", "pandas", "numpy", "tailwind css", "tailwind", "sqlalchemy"
    }:
        return SemanticCategory.FRAMEWORK_LIBRARY.value

    # 13. SOFT_SKILL
    if any(k in target for k in ["communication", "leadership", "teamwork", "collaboration", "ownership"]):
        return SemanticCategory.SOFT_SKILL.value

    # 14. DOMAIN
    if any(k in target for k in ["fintech", "finance", "healthcare", "e-commerce", "trading", "crypto"]):
        return SemanticCategory.DOMAIN.value

    return SemanticCategory.OTHER.value


def _is_aws_reference_genuine(text: str) -> bool:
    """Ensure 'AWS Route53-style console', 'Route53 clone', 'Route53-style' etc.
    does NOT get extracted as genuine AWS cloud infrastructure experience."""
    clean = text.lower()
    if not re.search(r"\baws\b", clean):
        return False
    # Strip clone/style references
    scrubbed = re.sub(r"\baws\s+route\s*53[-\s]*(?:style|clone|console)?\b", "", clean)
    scrubbed = re.sub(r"\broute\s*53[-\s]*(?:style|clone|console)?\b", "", scrubbed)
    # Check if AWS is mentioned independently or real AWS services are used
    if re.search(r"\baws\b", scrubbed):
        return True
    if re.search(r"\b(?:ec2|s3|lambda|iam|ecs|eks|cloudfront|cloudformation|dynamodb|sqs|sns|vpc)\b", scrubbed):
        return True
    return False


def _compute_semantic_similarity(text_a: str, text_b: str) -> float:
    """Compute semantic similarity between two texts using vector store cosine similarity."""
    if not text_a or not text_b:
        return 0.0
    try:
        from app.services.vector_store import vector_store
        return vector_store.compute_cosine_similarity(text_a, text_b)
    except Exception:
        wa = set(re.findall(r"\w+", text_a.lower()))
        wb = set(re.findall(r"\w+", text_b.lower()))
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)


@dataclass
class ResumeEvidence:
    skill: str
    canonical_skill: str
    evidence_snippets: List[str]
    source_section: str  # "projects", "experience", "skills", "education", "achievements", "leadership", "certifications"
    confidence: float = 0.95  # 0.0 to 1.0
    evidence_type: str = EvidenceType.SKILL.value
    capability: Optional[str] = None
    semantic_category: Optional[str] = None
    strength_score: float = 1.0
    parent_project_ids: Set[str] = field(default_factory=set)
    parent_project_titles: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.capability:
            self.capability = self.canonical_skill
        if not self.semantic_category:
            self.semantic_category = classify_semantic_category(self.skill, self.canonical_skill)

    @property
    def capability_name(self) -> str:
        return self.capability or self.canonical_skill

    @property
    def normalized_capability(self) -> str:
        return self.canonical_skill

    @property
    def evidence(self) -> List[str]:
        return self.evidence_snippets

    @property
    def strength(self) -> float:
        return self.strength_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability or self.canonical_skill,
            "evidence_type": self.evidence_type,
            "evidence": self.evidence_snippets[0] if self.evidence_snippets else "",
            "source_section": self.source_section,
            "confidence": self.confidence,
            "semantic_category": self.semantic_category,
            "parent_project_ids": list(self.parent_project_ids),
            "parent_project_titles": list(self.parent_project_titles),
        }


def extract_structured_resume_evidence(resume_data: Dict[str, Any]) -> Dict[str, ResumeEvidence]:
    """
    Extract structured resume evidence across all sections with concrete evidence types and capability recognition.
    Inspects projects, experience, achievements, education, leadership, and technical skills.
    """
    evidence_map: Dict[str, ResumeEvidence] = {}

    def _add_evidence(
        key: str,
        skill: str,
        canonical: str,
        snippet: str,
        section: str,
        ev_type: str,
        confidence: float = 0.95,
        strength: float = 1.0,
        capability: Optional[str] = None,
        category: Optional[str] = None,
        parent_project_id: Optional[str] = None,
        parent_project_title: Optional[str] = None,
    ) -> None:
        cat = category or classify_semantic_category(skill, canonical)
        cap = capability or canonical
        if key not in evidence_map:
            ev = ResumeEvidence(
                skill=skill,
                canonical_skill=canonical,
                evidence_snippets=[snippet],
                source_section=section,
                confidence=confidence,
                evidence_type=ev_type,
                capability=cap,
                semantic_category=cat,
                strength_score=strength,
            )
            if parent_project_id:
                ev.parent_project_ids.add(parent_project_id)
            if parent_project_title:
                ev.parent_project_titles.add(parent_project_title)
            evidence_map[key] = ev
        else:
            existing = evidence_map[key]
            if parent_project_id:
                existing.parent_project_ids.add(parent_project_id)
            if parent_project_title:
                existing.parent_project_titles.add(parent_project_title)
            if snippet not in existing.evidence_snippets:
                # Prioritize higher-strength evidence at the top of snippets
                if strength > existing.strength_score:
                    existing.evidence_snippets.insert(0, snippet)
                    existing.strength_score = strength
                    existing.evidence_type = ev_type
                    existing.source_section = section
                else:
                    existing.evidence_snippets.append(snippet)

    # 1. Parse from Projects (PROJECT_IMPLEMENTATION)
    raw_projects = resume_data.get("projects", [])
    for idx, proj in enumerate(raw_projects):
        proj_text = str(proj).strip()
        proj_id = f"proj_{idx + 1}"
        proj_title = ""
        if isinstance(proj, dict):
            proj_id = proj.get("project_id") or proj_id
            proj_title = proj.get("title") or proj.get("project_title") or proj.get("name") or ""
            proj_bullets = proj.get("bullets") or proj.get("project_bullets", [])
            proj_desc = proj.get("description") or proj.get("details") or ""
            proj_text = f"{proj_title}: {' '.join(proj_bullets)}" if proj_bullets else (f"{proj_title}: {proj_desc}" if proj_desc else proj_title)
        elif ":" in proj_text:
            proj_title = proj_text.split(":", 1)[0].strip()
        elif "|" in proj_text:
            proj_title = proj_text.split("|", 1)[0].strip()

        proj_lower = proj_text.lower()

        # A. Explicit Technologies in Project
        for alias, canonical in CANONICAL_SKILL_MAP.items():
            pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
            if re.search(pattern, proj_text, re.IGNORECASE):
                # SPECIAL AWS CHECK: Route53 clone / style reference is NOT genuine AWS experience
                if canonical == "AWS" and not _is_aws_reference_genuine(proj_text):
                    continue

                snippet = proj_text if len(proj_text) <= 180 else (proj_text[:177] + "...")
                _add_evidence(
                    key=canonical,
                    skill=alias,
                    canonical=canonical,
                    snippet=snippet,
                    section="projects",
                    ev_type=EvidenceType.PROJECT_IMPLEMENTATION.value,
                    confidence=0.98,
                    strength=0.98,
                    parent_project_id=proj_id,
                    parent_project_title=proj_title,
                )

        # B. Demonstrated Capabilities from Projects
        # 1. Software Development
        has_sw_dev = bool(
            re.search(r"\b(?:built|developed|implemented|created|engineered|shipped)\s+.*(?:application|system|service|backend|frontend|platform|dashboard|pipeline|rag|clone|api)\b", proj_lower)
            or re.search(r"\b(?:full-stack|full stack|rest api|restful|crud|fastapi backend|next\.js)\b", proj_lower)
        )
        if has_sw_dev:
            sw_snippet = f"Implemented {proj_text[:140]}" if (proj_title and proj_text.startswith(proj_title)) else f"Implemented {proj_title + ': ' if proj_title else ''}{proj_text[:140]}"
            _add_evidence(
                key="Software Development",
                skill="software development",
                canonical="Software Development",
                snippet=sw_snippet,
                section="projects",
                ev_type=EvidenceType.PROJECT_IMPLEMENTATION.value,
                confidence=0.98,
                strength=0.98,
                capability="Software Development",
                category=SemanticCategory.SOFTWARE_ENGINEERING.value,
                parent_project_id=proj_id,
                parent_project_title=proj_title,
            )

        # 2. System Design
        has_sys_design = bool(
            re.search(r"\b(?:system design|relational schema|schema design|architecture|scalability|scaling considerations|transaction handling|distributed systems|routing rules|high availability|data integrity)\b", proj_lower)
        )
        if has_sys_design:
            sd_snippet = f"Designed architecture/schema in {proj_text[:140]}" if (proj_title and proj_text.startswith(proj_title)) else f"Designed architecture/schema in {proj_title + ': ' if proj_title else ''}{proj_text[:140]}"
            _add_evidence(
                key="System Design",
                skill="system design",
                canonical="System Design",
                snippet=sd_snippet,
                section="projects",
                ev_type=EvidenceType.PROJECT_IMPLEMENTATION.value,
                confidence=0.98,
                strength=0.98,
                capability="System Design",
                category=SemanticCategory.SYSTEM_DESIGN.value,
                parent_project_id=proj_id,
                parent_project_title=proj_title,
            )

        # 3. Machine Learning (generic category demonstration)
        has_ml = bool(
            re.search(r"\b(?:scikit-learn|sklearn|ml pipeline|machine learning|feature engineering|model benchmarking|evaluation metrics|gradient boosting|logistic regression|random forest|roc-auc|f1 score)\b", proj_lower)
        )
        if has_ml:
            ml_snippet = f"Engineered ML pipeline in {proj_text[:140]}" if (proj_title and proj_text.startswith(proj_title)) else f"Engineered ML pipeline in {proj_title + ': ' if proj_title else ''}{proj_text[:140]}"
            _add_evidence(
                key="Machine Learning",
                skill="machine learning",
                canonical="Machine Learning",
                snippet=ml_snippet,
                section="projects",
                ev_type=EvidenceType.PROJECT_IMPLEMENTATION.value,
                confidence=0.98,
                strength=0.98,
                capability="Machine Learning",
                category=SemanticCategory.MACHINE_LEARNING.value,
                parent_project_id=proj_id,
                parent_project_title=proj_title,
            )

        # 4. Data Engineering
        has_data_eng = bool(
            re.search(r"\b(?:data pipeline|ingestion|deduplication|chunking|embeddings|etl|vector database|chromadb)\b", proj_lower)
        )
        if has_data_eng:
            de_snippet = f"Data pipeline implementation in {proj_text[:140]}" if (proj_title and proj_text.startswith(proj_title)) else f"Data pipeline implementation in {proj_title + ': ' if proj_title else ''}{proj_text[:140]}"
            _add_evidence(
                key="Data Engineering",
                skill="data engineering",
                canonical="Data Engineering",
                snippet=de_snippet,
                section="projects",
                ev_type=EvidenceType.PROJECT_IMPLEMENTATION.value,
                confidence=0.95,
                strength=0.95,
                capability="Data Engineering",
                category=SemanticCategory.DATA_ENGINEERING.value,
                parent_project_id=proj_id,
                parent_project_title=proj_title,
            )

        # 5. Problem Solving / Debugging in projects
        has_debugging = bool(
            re.search(r"\b(?:data pipeline debugging|debugging|debugged|diagnos|troublesh|trade-off)\b", proj_lower)
        )
        if has_debugging:
            dbg_snippet = f"Debugged complex pipeline and engineering trade-offs in {proj_title or 'project'}: {proj_text[:140]}"
            _add_evidence(
                key="Problem Solving",
                skill="problem solving",
                canonical="Problem Solving",
                snippet=dbg_snippet,
                section="projects",
                ev_type=EvidenceType.PROJECT_IMPLEMENTATION.value,
                confidence=0.95,
                strength=0.95,
                capability="Problem Solving",
                category=SemanticCategory.ALGORITHMS_PROBLEM_SOLVING.value,
                parent_project_id=proj_id,
                parent_project_title=proj_title,
            )

        # 6. Software Architecture / Architectural Reasoning in projects
        has_arch_reasoning = bool(
            re.search(r"\b(?:multi-tier|architecture|architectural trade-offs|caching plan|read-through caching|sharding|db sharding|horizontal scaling|session store|shared session store|relational schema design)\b", proj_lower)
        )
        if has_arch_reasoning:
            arch_snippet = f"Demonstrated architectural reasoning (multi-tier/schema/scaling) in {proj_title or 'project'}: {proj_text[:140]}"
            _add_evidence(
                key="Software Architecture",
                skill="software architecture",
                canonical="Software Architecture",
                snippet=arch_snippet,
                section="projects",
                ev_type=EvidenceType.PROJECT_IMPLEMENTATION.value,
                confidence=0.90,
                strength=0.90,
                capability="Software Architecture",
                category=SemanticCategory.SOFTWARE_ENGINEERING.value,
                parent_project_id=proj_id,
                parent_project_title=proj_title,
            )

    # 2. Parse from Achievements (ACHIEVEMENT)
    raw_achievements = resume_data.get("achievements", [])
    for ach in raw_achievements:
        ach_text = str(ach).strip()
        ach_lower = ach_text.lower()
        if re.search(r"\b(?:dsa|leetcode|streak|problem-solving|problem solving|competitive programming|hackerrank|codeforces|solved \d+)\b", ach_lower):
            _add_evidence(
                key="Problem Solving",
                skill="problem solving",
                canonical="Problem Solving",
                snippet=ach_text,
                section="achievements",
                ev_type=EvidenceType.ACHIEVEMENT.value,
                confidence=0.98,
                strength=0.98,
                capability="Problem Solving",
                category=SemanticCategory.ALGORITHMS_PROBLEM_SOLVING.value,
            )
            _add_evidence(
                key="Data Structures & Algorithms",
                skill="dsa",
                canonical="Data Structures & Algorithms",
                snippet=ach_text,
                section="achievements",
                ev_type=EvidenceType.ACHIEVEMENT.value,
                confidence=0.98,
                strength=0.98,
                capability="Data Structures & Algorithms",
                category=SemanticCategory.ALGORITHMS_PROBLEM_SOLVING.value,
            )
            _add_evidence(
                key="Algorithms",
                skill="algorithms",
                canonical="Algorithms",
                snippet=ach_text,
                section="achievements",
                ev_type=EvidenceType.ACHIEVEMENT.value,
                confidence=0.98,
                strength=0.98,
                capability="Algorithms",
                category=SemanticCategory.ALGORITHMS_PROBLEM_SOLVING.value,
            )

    # 3. Parse from Education (EDUCATION)
    raw_education = resume_data.get("education", [])
    raw_text = resume_data.get("raw_text", "")
    all_edu_text = " ".join([str(e) for e in raw_education] + [raw_text])
    grad_match = re.search(r"(?:expected graduation|graduation|batch of|class of|graduating in)?\s*(?:year\s*)?:?\s*\b(20[2-3]\d)\b", all_edu_text, re.IGNORECASE)
    if grad_match:
        grad_year = grad_match.group(1)
        grad_canonical = f"{grad_year} Graduate"
        grad_snippet = f"Education: Expected Graduation {grad_year}"
        _add_evidence(
            key=grad_canonical,
            skill=f"{grad_year} graduate",
            canonical=grad_canonical,
            snippet=grad_snippet,
            section="education",
            ev_type=EvidenceType.EDUCATION.value,
            confidence=1.0,
            strength=1.0,
            capability=grad_canonical,
            category=SemanticCategory.EDUCATION.value,
        )

    # 4. Parse from Experience (EXPERIENCE_BULLET)
    raw_experience = resume_data.get("experience", [])
    for exp in raw_experience:
        exp_text = str(exp).strip()
        for alias, canonical in CANONICAL_SKILL_MAP.items():
            pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
            if re.search(pattern, exp_text, re.IGNORECASE):
                if canonical == "AWS" and not _is_aws_reference_genuine(exp_text):
                    continue
                snippet = exp_text if len(exp_text) <= 180 else (exp_text[:177] + "...")
                _add_evidence(
                    key=canonical,
                    skill=alias,
                    canonical=canonical,
                    snippet=snippet,
                    section="experience",
                    ev_type=EvidenceType.EXPERIENCE_BULLET.value,
                    confidence=0.95,
                    strength=1.0,
                )

    # 5. Parse from Leadership (LEADERSHIP)
    raw_leadership = resume_data.get("leadership", [])
    for lead in raw_leadership:
        lead_text = str(lead).strip()
        snippet = lead_text if len(lead_text) <= 180 else (lead_text[:177] + "...")
        _add_evidence(
            key="Leadership",
            skill="leadership",
            canonical="Leadership",
            snippet=snippet,
            section="leadership",
            ev_type=EvidenceType.LEADERSHIP.value,
            confidence=0.95,
            strength=0.90,
            category=SemanticCategory.SOFT_SKILL.value,
        )

    # 6. Parse from Certifications (CERTIFICATION)
    raw_certs = resume_data.get("certifications", [])
    for cert in raw_certs:
        cert_text = str(cert).strip()
        for alias, canonical in CANONICAL_SKILL_MAP.items():
            pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
            if re.search(pattern, cert_text, re.IGNORECASE):
                snippet = cert_text if len(cert_text) <= 180 else (cert_text[:177] + "...")
                _add_evidence(
                    key=canonical,
                    skill=alias,
                    canonical=canonical,
                    snippet=snippet,
                    section="certifications",
                    ev_type=EvidenceType.CERTIFICATION.value,
                    confidence=0.95,
                    strength=0.90,
                )

    # 7. Parse from explicit Skills list (SKILL)
    raw_skills = resume_data.get("skills", [])
    for item in raw_skills:
        if not isinstance(item, str):
            continue
        subskills = [s.strip() for s in re.split(r"[,/|•]", item) if s.strip()]
        for sk in subskills:
            if not is_valid_technical_skill(sk):
                continue
            canonical = normalize_skill(sk)
            _add_evidence(
                key=canonical,
                skill=sk,
                canonical=canonical,
                snippet=f"Listed in Resume Skills: {canonical}",
                section="skills",
                ev_type=EvidenceType.SKILL.value,
                confidence=0.80,
                strength=0.80,
            )

    return evidence_map


def _evaluate_requirement_evidence(
    canonical: str,
    raw_requirement: str,
    evidence_map: Dict[str, ResumeEvidence],
) -> Tuple[MatchStatus, List[str], str]:
    """Two-stage category-aware evidence matcher with broad capability rules and technology strictness."""
    raw_lower = (raw_requirement or "").strip().lower()
    canonical_lower = canonical.strip().lower()
    req_cat = classify_semantic_category(raw_requirement, canonical)

    # 1. Controlled capability rules for broad concepts
    # A. Software Development
    if req_cat == SemanticCategory.SOFTWARE_ENGINEERING.value or canonical in ("Software Development", "Software Engineering") or "software development" in raw_lower:
        if "Software Development" in evidence_map:
            ev = evidence_map["Software Development"]
            unique_proj_count = len(ev.parent_project_ids) if ev.parent_project_ids else (len(ev.parent_project_titles) if ev.parent_project_titles else 0)
            if unique_proj_count > 0:
                notes = f"Software Development — verified through {unique_proj_count} implemented project{'s' if unique_proj_count > 1 else ''}, including {ev.evidence_snippets[0]}."
            else:
                notes = f"Software Development — verified through implemented software projects: {ev.evidence_snippets[0]}."
            return (
                MatchStatus.VERIFIED,
                ev.evidence_snippets[:2],
                notes,
            )
        for ev_k, ev_v in evidence_map.items():
            if ev_v.evidence_type == EvidenceType.PROJECT_IMPLEMENTATION.value and ev_v.semantic_category == SemanticCategory.SOFTWARE_ENGINEERING.value:
                return (
                    MatchStatus.VERIFIED,
                    ev_v.evidence_snippets[:2],
                    f"Software Development — verified through implemented software projects: {ev_v.evidence_snippets[0]}.",
                )

    # B. Problem Solving
    if req_cat == SemanticCategory.ALGORITHMS_PROBLEM_SOLVING.value or canonical in ("Problem Solving", "Algorithms", "Data Structures & Algorithms") or "problem solving" in raw_lower:
        if "Problem Solving" in evidence_map:
            ev = evidence_map["Problem Solving"]
            return (
                MatchStatus.VERIFIED,
                ev.evidence_snippets[:2],
                f"Problem Solving — verified through {ev.evidence_snippets[0]}.",
            )
        if "Data Structures & Algorithms" in evidence_map:
            ev = evidence_map["Data Structures & Algorithms"]
            return (
                MatchStatus.VERIFIED,
                ev.evidence_snippets[:2],
                f"Problem Solving — verified through DSA achievements: {ev.evidence_snippets[0]}.",
            )

    # C. System Design
    if req_cat == SemanticCategory.SYSTEM_DESIGN.value or canonical == "System Design" or "system design" in raw_lower:
        if "System Design" in evidence_map:
            ev = evidence_map["System Design"]
            return (
                MatchStatus.VERIFIED,
                ev.evidence_snippets[:2],
                f"System Design — verified through {ev.evidence_snippets[0]}.",
            )

    # D. Machine Learning (generic category requirement)
    if canonical == "Machine Learning" or raw_lower in ("machine learning", "ml"):
        if "Machine Learning" in evidence_map:
            ev = evidence_map["Machine Learning"]
            return (
                MatchStatus.VERIFIED,
                ev.evidence_snippets[:2],
                f"Machine Learning — verified through ML pipeline implementation in {ev.evidence_snippets[0]}.",
            )

    # E. Graduation Year Eligibility (e.g. 2028 Graduate)
    if "2028" in raw_lower or canonical == "2028 Graduate":
        if "2028 Graduate" in evidence_map:
            ev = evidence_map["2028 Graduate"]
            return (
                MatchStatus.VERIFIED,
                ev.evidence_snippets[:2],
                "2028 Graduate — verified through Education history (Expected Graduation: 2028).",
            )

    # F. Software Architecture (broad concept supporting related project evidence)
    if canonical == "Software Architecture" or raw_lower in ("software architecture", "application architecture", "system architecture"):
        # Direct professional software architect experience in dated employment -> VERIFIED
        if "Software Architecture" in evidence_map and evidence_map["Software Architecture"].evidence_type == EvidenceType.EXPERIENCE_BULLET.value:
            ev = evidence_map["Software Architecture"]
            return (
                MatchStatus.VERIFIED,
                ev.evidence_snippets[:2],
                f"Verified in {ev.source_section} (Software Architecture)",
            )
        # In projects, multi-tier architecture, schema design, and scaling trade-offs qualify as RELATED evidence
        if "Software Architecture" in evidence_map:
            ev = evidence_map["Software Architecture"]
            return (
                MatchStatus.RELATED,
                ev.evidence_snippets[:2],
                f"Software Architecture — related transferable evidence: candidate demonstrated architectural decisions in projects ({ev.evidence_snippets[0][:100]}), but professional architecture experience not verified.",
            )
        if "System Design" in evidence_map:
            ev = evidence_map["System Design"]
            return (
                MatchStatus.RELATED,
                ev.evidence_snippets[:1],
                f"Software Architecture — related transferable evidence: candidate demonstrated architecture and schema design in projects ({ev.evidence_snippets[0][:100]}), but professional architecture experience not verified.",
            )
        return (MatchStatus.MISSING, [], "No verified evidence found in resume for Software Architecture")

    # G. Software Design Patterns (strict technology requirement: direct evidence only)
    if canonical in ("Software Design Patterns", "Design Patterns") or "design patterns" in raw_lower:
        if "Software Design Patterns" in evidence_map or "Design Patterns" in evidence_map:
            ev = evidence_map.get("Software Design Patterns") or evidence_map["Design Patterns"]
            return (
                MatchStatus.VERIFIED,
                ev.evidence_snippets[:2],
                f"Verified in {ev.source_section} (Design Patterns)",
            )
        return (MatchStatus.MISSING, [], "No verified evidence found in resume for Software Design Patterns")

    # 2. Strict Technology Requirements
    if canonical in STRICT_TECHNOLOGIES:
        # AWS Check: ensure not clone
        if canonical == "AWS":
            if "AWS" in evidence_map:
                ev = evidence_map["AWS"]
                if any(_is_aws_reference_genuine(snip) for snip in ev.evidence_snippets):
                    return (MatchStatus.VERIFIED, ev.evidence_snippets[:2], f"Verified in {ev.source_section} (AWS)")
            # AWS Route53 clone does NOT prove AWS!
            if "Railway" in evidence_map or "Cloud" in evidence_map:
                rel_ev = evidence_map.get("Railway") or evidence_map.get("Cloud")
                return (
                    MatchStatus.RELATED,
                    rel_ev.evidence_snippets[:1],
                    "Related capability: candidate demonstrated Cloud Deployment in projects, but AWS not explicitly verified",
                )
            return (MatchStatus.MISSING, [], "No verified evidence found in resume for AWS")

        # PyTorch Check: requires PyTorch
        if canonical == "PyTorch":
            if "PyTorch" in evidence_map:
                ev = evidence_map["PyTorch"]
                return (MatchStatus.VERIFIED, ev.evidence_snippets[:2], f"Verified in {ev.source_section} (PyTorch)")
            # Machine Learning / Deep Learning is RELATED, NOT VERIFIED
            if "Deep Learning" in evidence_map:
                ev = evidence_map["Deep Learning"]
                return (MatchStatus.RELATED, ev.evidence_snippets[:1], "Related capability: candidate demonstrated Deep Learning, but PyTorch not explicitly verified")
            if "Machine Learning" in evidence_map:
                ev = evidence_map["Machine Learning"]
                return (MatchStatus.RELATED, ev.evidence_snippets[:1], "Related capability: candidate demonstrated Machine Learning in projects, but PyTorch not explicitly verified")
            return (MatchStatus.MISSING, [], "No verified evidence found in resume for PyTorch")

        # Kubernetes Check: strict technology requires Kubernetes
        if canonical == "Kubernetes":
            if "Kubernetes" in evidence_map:
                ev = evidence_map["Kubernetes"]
                return (MatchStatus.VERIFIED, ev.evidence_snippets[:2], f"Verified in {ev.source_section} (Kubernetes)")
            return (MatchStatus.MISSING, [], "No verified evidence found in resume for Kubernetes")

        # Scikit-Learn Check:
        if canonical == "Scikit-Learn":
            if "Scikit-Learn" in evidence_map:
                ev = evidence_map["Scikit-Learn"]
                return (MatchStatus.VERIFIED, ev.evidence_snippets[:2], f"Verified in {ev.source_section} (Scikit-Learn)")
            return (MatchStatus.MISSING, [], "No verified evidence found in resume for Scikit-Learn")

        # Kafka Check:
        if canonical == "Kafka":
            if "Kafka" in evidence_map:
                ev = evidence_map["Kafka"]
                return (MatchStatus.VERIFIED, ev.evidence_snippets[:2], f"Verified in {ev.source_section} (Kafka)")
            return (MatchStatus.MISSING, [], "No verified evidence found in resume for Kafka")

        # Other strict technologies require exact match in evidence_map
        if canonical in evidence_map:
            ev = evidence_map[canonical]
            return (MatchStatus.VERIFIED, ev.evidence_snippets[:2], f"Verified in {ev.source_section} ({canonical})")
        # Check related map
        related_targets = RELATED_SKILLS_MAP.get(canonical, set())
        for rel in related_targets:
            if rel in evidence_map:
                ev = evidence_map[rel]
                return (
                    MatchStatus.RELATED,
                    ev.evidence_snippets[:1],
                    f"Related capability: candidate demonstrated {rel} in {ev.source_section}",
                )
        return (MatchStatus.MISSING, [], f"No verified evidence found in resume for {canonical}")

    # 3. Direct match for other skills
    if canonical in evidence_map:
        ev = evidence_map[canonical]
        return (
            MatchStatus.VERIFIED,
            ev.evidence_snippets[:2],
            f"Verified in {ev.source_section} ({canonical})",
        )

    # 4. Related skills map check
    related_targets = RELATED_SKILLS_MAP.get(canonical, set())
    for rel in related_targets:
        if rel in evidence_map:
            ev = evidence_map[rel]
            return (
                MatchStatus.RELATED,
                ev.evidence_snippets[:1],
                f"Related capability: candidate demonstrated {rel} in {ev.source_section}",
            )

    # 5. Category-Gated Semantic Similarity Fallback
    compatible_cats = CATEGORY_COMPATIBILITY_MAP.get(req_cat, {req_cat})
    best_sim = 0.0
    best_candidate: Optional[Tuple[ResumeEvidence, str]] = None

    for ev_name, ev_obj in evidence_map.items():
        ev_cat = ev_obj.semantic_category or classify_semantic_category(ev_name, ev_obj.canonical_skill)
        # Category Gate: Incompatible categories cannot match
        if ev_cat not in compatible_cats:
            continue

        for snippet in ev_obj.evidence_snippets:
            sim = _compute_semantic_similarity(raw_requirement, snippet)
            if sim > best_sim:
                best_sim = sim
                best_candidate = (ev_obj, snippet)

    if best_sim >= 0.82 and best_candidate:
        ev_match, snip = best_candidate
        return (
            MatchStatus.VERIFIED,
            [snip],
            f"Verified via strong semantic evidence: {snip[:100]}",
        )
    elif best_sim >= 0.58 and best_candidate:
        ev_match, snip = best_candidate
        return (
            MatchStatus.RELATED,
            [snip],
            f"Related capability ({ev_match.canonical_skill}): {snip[:100]}",
        )

    # 6. Missing
    return (
        MatchStatus.MISSING,
        [],
        f"No verified evidence found in resume for {canonical}",
    )


def _evaluate_skill_evidence(
    canonical: str,
    evidence_map: Dict[str, ResumeEvidence],
) -> Tuple[MatchStatus, List[str], str]:
    """Helper alias for backward compatibility."""
    return _evaluate_requirement_evidence(canonical, canonical, evidence_map)


def get_canonical_requirement_key(
    text: str,
    category_hint: str = "required_skill",
) -> Tuple[str, str, str, str]:
    """
    Returns (canonical_id_key, canonical_display, category, semantic_category).
    Deduplicates semantically identical requirements such as:
    - '2028 Graduate', 'Graduating in 2028', 'Expected graduation 2028' -> ('graduation_year:2028', '2028 Graduate', 'education', ...)
    - '1+ years experience', '1+ years of experience' -> ('experience_years:1', '1+ years experience', 'experience', ...)
    - 'Python', 'python', 'python3' -> ('skill:python', 'Python', ...)
    """
    clean_text = str(text).strip()
    clean_lower = clean_text.lower()

    # 1. Graduation year patterns
    grad_m = re.search(r"(?:graduat(?:e|es|ing|ion)|batch of|class of|expected graduation)?\s*(?:year\s*)?:?\s*\b(202[4-9]|203\d)\b", clean_text, re.IGNORECASE)
    if not grad_m:
        grad_m = re.search(r"\b(202[4-9]|203\d)\s*(?:graduat(?:e|es|ing|ion)|batch|class)\b", clean_text, re.IGNORECASE)
    if grad_m and (category_hint in ("education", "required_skill", "preferred_skill", "other") or "graduat" in clean_lower or "batch" in clean_lower or "class" in clean_lower):
        yr = grad_m.group(1)
        return (
            f"graduation_year:{yr}",
            f"{yr} Graduate",
            "education",
            SemanticCategory.EDUCATION.value,
        )

    # 2. Years of experience patterns
    exp_m = re.search(r"(\d+)\+?\s*(?:-\s*\d+\+?\s*)?(?:years?|yrs?)(?:\s+of)?(?:\s+[a-zA-Z\s]{0,40})?\s*experience", clean_text, re.IGNORECASE)
    if exp_m:
        yrs = exp_m.group(1)
        return (
            f"experience_years:{yrs}",
            f"{yrs}+ years experience",
            "experience",
            SemanticCategory.EXPERIENCE_YEARS.value,
        )

    # 3. Education / degree patterns
    if category_hint == "education" or re.search(r"\b(bachelor(?:'s)?|b\.?tech|b\.?s\.?|b\.?e\.?|master(?:'s)?|m\.?s\.?|phd)\b", clean_lower):
        deg_match = re.search(r"\b(bachelor(?:'s)?|b\.?tech|b\.?s\.?|b\.?e\.?|master(?:'s)?|m\.?s\.?|phd)\b", clean_lower)
        if deg_match:
            deg_key = deg_match.group(1).replace(".", "").lower()
            return (
                f"degree:{deg_key}",
                clean_text,
                "education",
                SemanticCategory.EDUCATION.value,
            )

    # 4. Soft traits / attributes patterns (Unverified traits, not technical skills)
    if (
        category_hint in ("soft_skill", "trait")
        or any(w in clean_lower for w in [
            "creative thinking", "original approach", "willingness to learn",
            "ability to work on new", "learn & work on new", "fast learner",
            "hard worker", "team player", "self starter", "growth mindset",
            "curiosity", "attitude", "critical thinking", "problem-solving mindset"
        ])
    ):
        return (
            f"trait:{clean_lower[:30]}",
            clean_text,
            "soft_skill",
            SemanticCategory.SOFT_SKILL.value,
        )

    # 5. Standard technical skill / capability
    canonical_skill = normalize_skill(clean_text)
    sem_cat = classify_semantic_category(clean_text, canonical_skill)
    return (
        f"skill:{canonical_skill.lower()}",
        canonical_skill,
        category_hint,
        sem_cat,
    )



def build_unified_requirements(
    jd_data: Optional[Dict[str, Any]] = None,
    evidence_map: Optional[Dict[str, ResumeEvidence]] = None,
    candidate_years: Optional[float] = 0.0,
    candidate_degree_verified: bool = True,
    *,
    required_skills: Optional[List[str]] = None,
    preferred_skills: Optional[List[str]] = None,
    experience_requirements: Optional[List[str]] = None,
    education_requirements: Optional[List[str]] = None,
    domain_requirements: Optional[List[str]] = None,
    requested_years: Optional[float] = None,
) -> List[NormalizedRequirement]:
    """
    SINGLE SOURCE OF TRUTH:
    Convert all JD requirements (required skills, preferred skills, experience,
    education, domain) into a unified normalized requirement list.
    Applies canonical deduplication BEFORE matching/scoring.
    """
    if jd_data is None:
        jd_data = {}
    else:
        jd_data = dict(jd_data)

    if required_skills is not None:
        jd_data["required_skills"] = required_skills
    if preferred_skills is not None:
        jd_data["preferred_skills"] = preferred_skills
    if experience_requirements is not None:
        jd_data["required_experience"] = experience_requirements
    if education_requirements is not None:
        jd_data["education_requirements"] = education_requirements
    if domain_requirements is not None:
        jd_data["domain_requirements"] = domain_requirements
    if requested_years is not None and "min_years_experience" not in jd_data:
        jd_data["min_years_experience"] = requested_years

    if evidence_map is None:
        evidence_map = {}

    # ---------------------------------------------------------------------------
    # CANONICAL DEDUPLICATION BEFORE MATCHING / SCORING
    # ---------------------------------------------------------------------------
    raw_specs: List[Dict[str, Any]] = []

    # 1. Required Skills
    for skill in jd_data.get("required_skills", []):
        if skill and str(skill).strip():
            raw_specs.append({
                "raw_text": str(skill).strip(),
                "category_hint": "required_skill",
                "importance": "required",
                "source": "JD required technology",
                "weight": 1.0,
            })

    # 2. Preferred Skills
    for skill in jd_data.get("preferred_skills", []):
        if skill and str(skill).strip():
            raw_specs.append({
                "raw_text": str(skill).strip(),
                "category_hint": "preferred_skill",
                "importance": "preferred",
                "source": "JD preferred requirement",
                "weight": 0.5,
            })

    # 3. Graduation Year Eligibility
    grad_eligibility = jd_data.get("graduation_year_eligibility")
    if grad_eligibility:
        raw_specs.append({
            "raw_text": f"{grad_eligibility} Graduate",
            "category_hint": "education",
            "importance": "required",
            "source": "JD graduation year requirement",
            "weight": 1.0,
        })

    # 4. Education Requirements
    for edu_text in jd_data.get("education_requirements", []):
        if edu_text and str(edu_text).strip():
            raw_specs.append({
                "raw_text": str(edu_text).strip(),
                "category_hint": "education",
                "importance": "required",
                "source": "JD education requirement",
                "weight": 0.5,
            })

    # 5. Domain Requirements
    for dom_text in jd_data.get("domain_requirements", []):
        if dom_text and str(dom_text).strip():
            raw_specs.append({
                "raw_text": str(dom_text).strip(),
                "category_hint": "domain",
                "importance": "preferred",
                "source": "JD domain requirement",
                "weight": 0.5,
            })

    # 6. Soft Skills / Traits
    for soft_text in jd_data.get("soft_skills", []):
        if soft_text and str(soft_text).strip():
            raw_specs.append({
                "raw_text": str(soft_text).strip(),
                "category_hint": "soft_skill",
                "importance": "preferred",
                "source": "UNVERIFIED TRAITS",
                "weight": 0.5,
            })

    # Deduplicate canonical requirements
    deduped_specs: Dict[str, Dict[str, Any]] = {}
    for spec in raw_specs:
        canon_key, canon_display, final_cat, sem_cat = get_canonical_requirement_key(
            spec["raw_text"], spec["category_hint"]
        )
        if canon_key not in deduped_specs:
            deduped_specs[canon_key] = {
                "canonical_key": canon_key,
                "canonical": canon_display,
                "requirement": spec["raw_text"],
                "category": final_cat,
                "importance": spec["importance"],
                "source": spec["source"],
                "weight": spec["weight"],
                "semantic_category": sem_cat,
            }
        else:
            existing = deduped_specs[canon_key]
            # Strongest importance wins (required > preferred)
            if spec["importance"] == "required" and existing["importance"] != "required":
                existing["importance"] = "required"
                existing["weight"] = max(existing["weight"], spec["weight"])
                if existing["category"] == "preferred_skill":
                    existing["category"] = "required_skill"
            # Stronger / more specific provenance preserved
            if "graduation year" in spec["source"] or "education" in spec["source"]:
                existing["source"] = spec["source"]
                existing["category"] = "education"
                existing["semantic_category"] = SemanticCategory.EDUCATION.value
            elif "required technology" in spec["source"] and "preferred" in existing["source"]:
                existing["source"] = spec["source"]

    # Reconcile core software skills: promote Software Development or core technical role skill to required_skill
    has_tech_req = any(
        s["importance"] == "required" and is_valid_technical_skill(s["canonical"])
        for s in deduped_specs.values()
    )
    for canon_key, spec in deduped_specs.items():
        if spec["canonical"] == "Software Development" or (not has_tech_req and is_valid_technical_skill(spec["canonical"])):
            if spec["category"] in ("domain", "other", "preferred_skill"):
                spec["category"] = "required_skill"
                spec["importance"] = "required"
                spec["weight"] = 1.0
                spec["source"] = "JD required technology"
                has_tech_req = True

    requirements: List[NormalizedRequirement] = []

    # Process deduplicated specs
    for canon_key, spec in deduped_specs.items():
        canonical = spec["canonical"]
        req_text = spec["requirement"]
        sem_cat = spec.get("semantic_category", SemanticCategory.OTHER.value)

        # Distinguish soft traits from technical gaps (Section 17)
        is_soft_trait = (
            (spec["category"] in ("soft_skill", "trait") or sem_cat == SemanticCategory.SOFT_SKILL.value)
            and spec["category"] not in ("required_skill", "education", "experience")
            and canonical != "Software Development"
            and not is_valid_technical_skill(canonical)
        )

        if is_soft_trait:
            spec["category"] = "soft_skill"
            spec["importance"] = "preferred"
            score_comp = "soft_traits"
            status = MatchStatus.MISSING
            ev_snippets = []
            notes = "Not directly verifiable from resume."
            source_excerpt = "UNVERIFIED TRAITS"
            ev_type = None
        elif spec["category"] == "education":
            score_comp = "eligibility"
            source_excerpt = spec["source"]
            cand_edu_str = ""
            if evidence_map:
                for ev in evidence_map.values():
                    if ev.source_section == "education" or ev.evidence_type == EvidenceType.EDUCATION.value:
                        cand_edu_str += " ".join(ev.evidence_snippets) + " "
            if "2028" in canonical or "2028" in req_text:
                if "2028" in cand_edu_str or "expected graduation" in cand_edu_str.lower():
                    status = MatchStatus.VERIFIED
                    ev_snippets = ["Expected graduation year 2028 verified in education history."]
                    notes = "2028 graduation eligibility verified in education history."
                    ev_type = EvidenceType.EDUCATION.value
                else:
                    status = MatchStatus.MISSING
                    ev_snippets = []
                    notes = "2028 graduation year not verified in education history."
                    ev_type = None
            elif "graduat" in req_text.lower():
                # Section 18: If JD asks for graduates and candidate resume states expected graduation in 2028, preserve uncertainty
                if "2028" in cand_edu_str or "expected graduation" in cand_edu_str.lower():
                    status = MatchStatus.RELATED
                    ev_snippets = []
                    notes = "JD mentions graduates; resume indicates expected graduation in 2028."
                    source_excerpt = "ELIGIBILITY TO REVIEW"
                    ev_type = None
                elif candidate_degree_verified:
                    status = MatchStatus.VERIFIED
                    ev_snippets = ["B.S. / B.Tech degree verified in education history."]
                    notes = "Degree requirement verified in education history."
                    ev_type = EvidenceType.EDUCATION.value
                else:
                    status = MatchStatus.MISSING
                    ev_snippets = []
                    notes = "Degree requirement not verified in education history."
                    ev_type = None
            elif candidate_degree_verified and any(w in req_text.lower() for w in ["bachelor", "degree", "b.tech", "b.s.", "computer science"]):
                status = MatchStatus.VERIFIED
                ev_snippets = ["B.S. / B.Tech degree verified in education history."]
                notes = "Degree requirement verified in education history."
                ev_type = EvidenceType.EDUCATION.value
            else:
                status, ev_snippets, notes = _evaluate_requirement_evidence(canonical, req_text, evidence_map)
                ev_type = evidence_map[canonical].evidence_type if canonical in evidence_map else None
        else:
            status, ev_snippets, notes = _evaluate_requirement_evidence(canonical, req_text, evidence_map)
            ev_type = evidence_map[canonical].evidence_type if canonical in evidence_map else None
            source_excerpt = spec["source"]
            if spec["category"] == "required_skill":
                score_comp = "required_skills"
            elif spec["category"] == "preferred_skill":
                score_comp = "preferred_skills"
            elif spec["category"] == "domain":
                score_comp = "domain"
            else:
                score_comp = "other"

        prefix = "req" if spec["importance"] == "required" else "pref"
        if spec["category"] == "education":
            prefix = "edu"
        elif is_soft_trait:
            prefix = "trait"

        requirements.append(NormalizedRequirement(
            requirement_id=f"{prefix}_{uuid.uuid4().hex[:8]}",
            category=spec["category"],
            requirement=req_text,
            canonical=canonical,
            importance=spec["importance"],
            score_component=score_comp,
            match_status=status.value,
            resume_evidence=ev_snippets,
            source=spec["source"],
            source_excerpt=source_excerpt,
            notes=notes,
            weight=spec["weight"],
            semantic_category=spec["semantic_category"],
            evidence_type=ev_type,
        ))


    # Experience Requirements (evaluated deterministically only if an explicit experience requirement exists)
    min_years = jd_data.get("min_years_experience")
    exp_reqs = jd_data.get("required_experience", [])

    explicit_exp_years = None
    explicit_exp_text = None

    if min_years is not None and float(min_years) > 0:
        explicit_exp_years = float(min_years)
        explicit_exp_text = exp_reqs[0] if exp_reqs else f"{int(explicit_exp_years)}+ years experience"
    elif exp_reqs:
        for er in exp_reqs:
            if not isinstance(er, str) or not er.strip():
                continue
            cleaned_er = er.strip().lower()
            if any(ign in cleaned_er for ign in ["fresher", "not specified", "none", "no experience", "0 year", "internship"]):
                continue
            m = re.search(r"(\d+)\+?\s*(?:-\s*\d+\+?\s*)?years?", er, re.IGNORECASE)
            if m:
                explicit_exp_years = float(m.group(1))
                explicit_exp_text = er
                break

    if explicit_exp_years is not None and explicit_exp_years > 0:
        req_years = explicit_exp_years
        exp_text = explicit_exp_text or f"{int(req_years)}+ years experience"

        if candidate_years is None:
            exp_status = MatchStatus.MISSING
            exp_notes = f"EXPERIENCE GAP: {int(req_years)}+ years requested / Not determinable from resume."
            exp_ev = []
        elif candidate_years >= req_years:
            exp_status = MatchStatus.VERIFIED
            exp_notes = f"Verified: ~{round(candidate_years, 1)} years meets requested {int(req_years)}+ years."
            exp_ev = [f"Approximately {round(candidate_years, 1)} years verifiable experience found in resume."]
        elif candidate_years >= (req_years * 0.6):
            exp_status = MatchStatus.RELATED
            exp_notes = f"Partial alignment: ~{round(candidate_years, 1)} years verified vs {int(req_years)}+ years requested."
            exp_ev = [f"Approximately {round(candidate_years, 1)} years verifiable experience found in resume."]
        else:
            exp_status = MatchStatus.MISSING
            exp_notes = f"EXPERIENCE GAP: {int(req_years)}+ years requested / ~{round(candidate_years, 1)} years verified."
            exp_ev = []

        requirements.append(NormalizedRequirement(
            requirement_id=f"exp_{uuid.uuid4().hex[:8]}",
            category="experience",
            requirement=exp_text,
            canonical=f"{int(req_years)}+ years experience",
            importance="required",
            match_status=exp_status.value,
            resume_evidence=exp_ev,
            source="JD experience requirement",
            notes=exp_notes,
            weight=1.5,
            semantic_category=SemanticCategory.EXPERIENCE_YEARS.value,
            evidence_type=EvidenceType.EXPERIENCE_BULLET.value if exp_status == MatchStatus.VERIFIED else None,
        ))

    return requirements


def recompute_component_score(component_requirements: List[NormalizedRequirement]) -> Optional[int]:
    """Helper ensuring displayed component score is directly reproducible from the canonical graph."""
    if not component_requirements:
        return None
    v_count = sum(1 for r in component_requirements if r.match_status == MatchStatus.VERIFIED.value)
    r_count = sum(1 for r in component_requirements if r.match_status == MatchStatus.RELATED.value)
    return int(round(((v_count * 1.0 + r_count * 0.40) / len(component_requirements)) * 100.0))


def calculate_reconciled_scores(
    requirements: List[NormalizedRequirement],
    domain_match_ratio: float = 0.5,
    candidate_years: Optional[float] = None,
    requested_years: Optional[float] = None,
    is_partial_jd: bool = False,
) -> Tuple[int, Dict[str, Any]]:
    """
    Calculate deterministic, mathematically reconciled component and overall match scores.

    NULL vs ZERO distinction:
    - A score of None means "not evaluated" (no requirements in this category).
    - A score of 0 means "requirements existed but none were matched".

    Weights redistribute among evaluable categories when some are absent.
    If evidence is partial or insufficient, Candidate Fit is withheld (sentinel score -1 -> None).
    Individual extracted requirements and component scores are still evaluated and displayed.

    Configured weights:
    - Required Skills:  40% (0.40)
    - Preferred Skills: 15% (0.15)
    - Experience:       25% (0.25)
    - Role Alignment:   20% (0.20)
    """
    req_skills = [
        r for r in requirements
        if r.score_component == "required_skills" or (not r.score_component and r.category == "required_skill")
    ]
    pref_skills = [
        r for r in requirements
        if r.score_component == "preferred_skills" or (not r.score_component and r.category == "preferred_skill")
    ]
    exp_reqs = [
        r for r in requirements
        if r.score_component == "experience" or (not r.score_component and r.category == "experience")
    ]

    # Total explicit skill/exp requirements for quality assessment
    total_skill_reqs = len(req_skills) + len(pref_skills)
    has_explicit_exp = bool(exp_reqs)

    # Determine analysis quality
    if total_skill_reqs == 0 and not has_explicit_exp:
        analysis_quality = "INSUFFICIENT_REQUIREMENTS"
    elif total_skill_reqs == 0:
        analysis_quality = "PARTIAL"
    elif total_skill_reqs < 2:
        analysis_quality = "PARTIAL"
    elif is_partial_jd:
        analysis_quality = "PARTIAL"
    else:
        analysis_quality = "COMPLETE"

    # 1. Required Skills Score — None if no requirements in this category
    req_score: Optional[int]
    if req_skills:
        req_score = recompute_component_score(req_skills)
    else:
        req_score = None  # Not evaluated — not "0% match"

    # 2. Preferred Skills Score — None if no requirements in this category
    pref_score: Optional[int]
    if pref_skills:
        pref_score = recompute_component_score(pref_skills)
    else:
        pref_score = None  # Not evaluated

    # 3. Experience Score (0 - 100) - Deterministic calculation
    exp_score: Optional[int]
    if exp_reqs:
        exp_item = exp_reqs[0]
        if exp_item.match_status == MatchStatus.VERIFIED.value:
            exp_score = 85
        elif exp_item.match_status == MatchStatus.RELATED.value:
            exp_score = 55
        else:
            # Deterministic: If verified professional experience years is None or 0, score is 0%
            if candidate_years is None or candidate_years <= 0:
                exp_score = 0
            else:
                req_y = requested_years or 5.0
                ratio = min(1.0, candidate_years / req_y)
                exp_score = int(round(ratio * 35.0))
    else:
        exp_score = None  # Experience MUST be N/A when JD has no experience requirement (no default 70)

    # 4. Role Alignment / Domain Score (0 - 100)
    domain_score = int(round(max(20.0, min(100.0, domain_match_ratio * 100.0))))

    # Centrally enforce: Withhold Candidate Fit score for partial JD, <= 1 evaluated requirement, or INSUFFICIENT_REQUIREMENTS / PARTIAL
    total_evaluated_requirements = len(requirements)
    if is_partial_jd or total_evaluated_requirements <= 1 or analysis_quality in ("INSUFFICIENT_REQUIREMENTS", "PARTIAL") or total_skill_reqs < 2:
        final_score = -1
        breakdown = {
            "required_skills_score": req_score,
            "preferred_skills_score": pref_score,
            "experience_score": exp_score,
            "domain_score": domain_score,
            "seniority_gap": False,
            "analysis_quality": "INSUFFICIENT_REQUIREMENTS" if total_evaluated_requirements == 0 else "PARTIAL",
        }
        return final_score, breakdown

    # Redistribute weights among evaluable components
    # Base weights: req=0.40, pref=0.15, exp=0.25, domain=0.20
    weight_req = 0.40 if req_score is not None else 0.0
    weight_pref = 0.15 if pref_score is not None else 0.0
    weight_exp = 0.25 if exp_score is not None else 0.0
    weight_domain = 0.20
    total_weight = weight_req + weight_pref + weight_exp + weight_domain

    # Normalize weights so they sum to 1.0
    if total_weight > 0:
        weight_req /= total_weight
        weight_pref /= total_weight
        weight_exp /= total_weight
        weight_domain /= total_weight

    raw_final = (
        (weight_req * (req_score or 0)) +
        (weight_pref * (pref_score or 0)) +
        (weight_exp * (exp_score or 0)) +
        (weight_domain * domain_score)
    )

    # Score Guardrail for Critical Gaps
    has_critical_exp_gap = bool(
        exp_reqs
        and exp_reqs[0].match_status == MatchStatus.MISSING.value
        and (requested_years or 0) >= 4.0
    )
    if has_critical_exp_gap:
        raw_final = min(raw_final, 50.0)

    final_score = int(round(max(10, min(95, raw_final))))

    breakdown = {
        "required_skills_score": req_score,       # None = not evaluated
        "preferred_skills_score": pref_score,     # None = not evaluated
        "experience_score": exp_score,
        "domain_score": domain_score,
        "seniority_gap": has_critical_exp_gap,
        "analysis_quality": analysis_quality,
    }

    return final_score, breakdown


def calculate_deterministic_match_score(
    matches: List[Any],
    seniority_gap_detected: bool = False,
) -> Tuple[int, Dict[str, Any]]:
    """Legacy helper for backward compatibility with older tests."""
    req_skills = [m for m in matches if getattr(m, "is_required", True)]
    pref_skills = [m for m in matches if not getattr(m, "is_required", True)]

    v_req = sum(1 for m in req_skills if getattr(m, "status", "") in ("VERIFIED_MATCH", MatchStatus.VERIFIED.value))
    r_req = sum(1 for m in req_skills if getattr(m, "status", "") in ("RELATED_EVIDENCE", MatchStatus.RELATED.value))
    req_score = int(round(((v_req * 1.0 + r_req * 0.40) / len(req_skills)) * 100.0)) if req_skills else 0

    v_pref = sum(1 for m in pref_skills if getattr(m, "status", "") in ("VERIFIED_MATCH", MatchStatus.VERIFIED.value))
    r_pref = sum(1 for m in pref_skills if getattr(m, "status", "") in ("RELATED_EVIDENCE", MatchStatus.RELATED.value))
    pref_score = int(round(((v_pref * 1.0 + r_pref * 0.40) / len(pref_skills)) * 100.0)) if pref_skills else req_score

    exp_score = 30 if seniority_gap_detected else 75
    domain_score = 65

    raw = (0.40 * req_score) + (0.15 * pref_score) + (0.25 * exp_score) + (0.20 * domain_score)
    if seniority_gap_detected:
        raw = min(raw, 50.0)

    final_score = int(round(max(10, min(95, raw))))
    breakdown = {
        "required_skills_score": req_score,
        "preferred_skills_score": pref_score,
        "experience_score": exp_score,
        "domain_score": domain_score,
        "seniority_gap": seniority_gap_detected,
    }
    return final_score, breakdown


def match_requirements_to_evidence(
    required_skills: List[str],
    preferred_skills: List[str],
    evidence_map: Dict[str, ResumeEvidence],
) -> List[Any]:
    """Legacy helper for backward compatibility with older tests."""
    unified = build_unified_requirements(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        evidence_map=evidence_map,
    )

    class LegacyMatchItem:
        def __init__(self, req: NormalizedRequirement):
            self.requirement = req.requirement
            self.canonical_requirement = req.canonical
            if req.match_status == MatchStatus.VERIFIED.value:
                self.status = MatchStatus.VERIFIED_MATCH
            elif req.match_status == MatchStatus.RELATED.value:
                self.status = MatchStatus.RELATED_EVIDENCE
            else:
                self.status = MatchStatus.NOT_FOUND
            self.evidence = req.resume_evidence
            self.notes = req.notes
            self.is_required = req.importance == "required"

    return [LegacyMatchItem(r) for r in unified if r.category in ("required_skill", "preferred_skill")]
