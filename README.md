# Aptly

### Plan. Apply. Grow.

**Aptly is an AI-powered career operating system that helps you discover relevant opportunities, understand your fit, tailor your resume, manage applications, and track your journey from search to offer — all in one workspace.**

🌐 **Live Demo:** https://aptly-seven.vercel.app  
💻 **Repository:** https://github.com/mahek12345678/Aptly

---

## About Aptly

Job searching is fragmented.

Candidates discover jobs on one platform, analyze job descriptions somewhere else, tailor resumes manually or with separate AI tools, and then maintain application progress in spreadsheets or notes.

**Aptly brings this workflow together.**

```text
Resume + Career Preferences
            ↓
     Discover Real Jobs
            ↓
     Personalized Ranking
            ↓
      Analyze Job Fit
            ↓
       Tailor Resume
            ↓
           Apply
            ↓
     Track Application
            ↓
      Learn & Improve
```

Aptly is designed around three simple stages:

**PLAN → APPLY → GROW**

---

## Features

### AI-Powered Job Discovery

Aptly discovers real job opportunities and ranks them according to the user's resume and career preferences.

The matching pipeline combines:

- Semantic resume ↔ job similarity
- Preferred roles
- Opportunity type
- Location / work-mode preferences
- Verified skill overlap

Real job listings are sourced through the **Adzuna Jobs API**.

---

### Resume ↔ Role Matching

Each opportunity is compared against the candidate's profile to provide a personalized match.

Aptly separates the ranking into meaningful signals rather than showing an unexplained AI score.

```text
Resume Similarity
        +
Preference Fit
        ↓
 Personalized Job Match
```

Users can see why a role matches their profile and where potential gaps exist.

---

### JD Analyzer

Paste a job description or analyze a job directly from Aptly.

The analyzer identifies:

- Required qualifications
- Preferred qualifications
- Experience requirements
- Skills and technologies
- Responsibilities
- Verified resume evidence
- Related experience
- Missing requirements

Requirements are classified as:

```text
VERIFIED
RELATED
MISSING
```

This keeps the analysis grounded in the candidate's actual resume.

---

### Safe AI Resume Tailoring

Aptly can tailor resume content toward a selected opportunity while following an important rule:

> **Never fabricate candidate experience.**

The system uses verified resume evidence and the job description to improve relevance while keeping the candidate's background truthful.

Missing skills remain gaps rather than being silently added to the resume.

---

### Application Tracking

Aptly includes a visual application pipeline:

```text
Applied → OA / Assessment → Interview → Offer → Rejected
```

Applications can be organized and updated from a Kanban-style workspace.

The tracker stores useful information including:

- Company
- Role
- Application URL
- Current status
- Source
- Notes
- Application date

---

### Application Intent Tracking

External job applications create a common tracking problem: users leave the platform to apply and may forget to record the application.

Aptly handles this with an application-intent workflow.

```text
Click Apply
    ↓
Record Application Intent
    ↓
Open Employer Website
    ↓
Return to Aptly
    ↓
"Did you apply?"
    ↓
Yes → Add to Application Tracker
Not Yet → Keep Pending
```

This keeps application metrics cleaner without assuming that clicking **Apply** means an application was actually submitted.

---

### Career Dashboard

The dashboard acts as the user's career control tower.

It provides visibility into:

- Jobs applied
- Replies received
- Offers received
- Pipeline velocity
- Search funnel drop-off
- Upcoming activity
- Recent activity
- Personalized job matches

Instead of only storing applications, Aptly helps users understand how their job search is progressing.

---

### Ask Aptly

**Ask Aptly** is a contextual AI career assistant available throughout the workspace.

It can use relevant career context to help users understand:

- Job opportunities
- Application progress
- Resume information
- Career next steps

Voice interaction is also supported using **ElevenLabs**.

---

### Career Profile

Aptly converts an uploaded resume into a structured career profile containing information such as:

- Skills
- Education
- Experience
- Projects
- Certifications
- Achievements
- Career preferences

The profile acts as the evidence layer used by other Aptly features.

---

## System Architecture

```text
                         ┌─────────────────────┐
                         │     React Client    │
                         │ TypeScript + Vite   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    FastAPI API      │
                         │       Python        │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
     ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
     │ PostgreSQL   │       │   ChromaDB   │       │ Redis/Celery │
     │ User + Apps  │       │  Embeddings  │       │ Background   │
     └──────────────┘       └──────────────┘       └──────────────┘
             │                      │
             │                      ▼
             │              Semantic Retrieval
             │
             └──────────────────────┬──────────────────────┐
                                    │                      │
                                    ▼                      ▼
                             ┌────────────┐          ┌────────────┐
                             │ Groq LLM   │          │ Adzuna API │
                             │ AI Layer   │          │ Real Jobs  │
                             └────────────┘          └────────────┘
```

---

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- `@hello-pangea/dnd`

### Backend

- FastAPI
- Python
- Async SQLAlchemy
- Alembic
- Pydantic

### Database & Retrieval

- PostgreSQL
- Neon
- ChromaDB
- Vector embeddings

### AI

- Groq
- Llama 3.3 70B Versatile
- Semantic search
- Retrieval-Augmented Generation (RAG)
- Structured LLM outputs

### External Integrations

- Adzuna Jobs API
- Google OAuth
- ElevenLabs

### Background Processing

- Celery
- Redis

### Deployment

- **Frontend:** Vercel
- **Backend:** Render
- **Database:** Neon PostgreSQL

---

## Job Recommendation Pipeline

Aptly does not use an LLM as the source of truth for live vacancies.

Instead:

```text
Adzuna Jobs API
       ↓
Normalize Listings
       ↓
Deduplicate Jobs
       ↓
PostgreSQL
       ↓
Generate Embeddings
       ↓
ChromaDB
       ↓
Semantic Shortlisting
       ↓
Preference Scoring
       ↓
Grounded AI Explanation
       ↓
Personalized Job Feed
```

This separates **job retrieval** from **AI reasoning**.

---

## Matching Strategy

Aptly combines semantic similarity with explicit career preferences.

```text
Final Match =
70% Semantic Resume Similarity
+
30% Preference Fit
```

Preference fit considers:

```text
Target Roles       → 40%
Opportunity Type   → 25%
Location / Remote  → 15%
Skill Overlap      → 20%
```

This provides a more interpretable ranking than relying only on LLM-generated recommendations.

---

## Resume Processing Pipeline

```text
Resume Upload
     ↓
PDF / DOCX Parsing
     ↓
Structured Resume Extraction
     ↓
Skills / Experience / Projects
     ↓
Chunking
     ↓
Embeddings
     ↓
ChromaDB
     ↓
Retrieval for Matching & Analysis
```

Supported resume formats:

- PDF
- DOCX

---

## Authentication

Aptly uses **Google OAuth** for authentication.

```text
Google Sign-In
      ↓
Frontend Credential
      ↓
FastAPI Verification
      ↓
User Account
      ↓
JWT Session
      ↓
Protected Workspace
```

---

## Project Structure

```text
Aptly/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── lib/
│   │   └── pages/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
└── README.md
```

---

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/mahek12345678/Aptly.git
cd Aptly
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Backend

Create a Python virtual environment and install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

### 4. Environment Variables

Aptly requires environment variables for services such as:

```text
PostgreSQL
Google OAuth
Groq
Adzuna
ElevenLabs
Redis
```

Create your own local environment configuration.

**Never commit API keys or production secrets to GitHub.**

---

## Production

| Service | Platform |
|---|---|
| Frontend | Vercel |
| Backend API | Render |
| PostgreSQL | Neon |
| Job Data | Adzuna |
| LLM | Groq |
| Voice | ElevenLabs |

### Live Application

**https://aptly-seven.vercel.app**

---

## What I Learned

Building Aptly involved much more than connecting an interface to an LLM.

Some of the key areas explored while building the project include:

- Full-stack application architecture
- REST API design
- PostgreSQL data modeling
- Vector databases
- Semantic search
- Retrieval-Augmented Generation
- Grounded LLM outputs
- Structured AI responses
- Resume parsing
- External API integration
- Google OAuth
- Background processing
- Production CORS and authentication
- Cloud deployment
- Production debugging

---

## Future Improvements

Some directions for future versions include:

- Additional job providers
- Improved recommendation feedback loops
- Better application analytics
- Interview preparation workflows
- Persistent cloud vector infrastructure
- Expanded career intelligence features

---

## Author

**Mahek Advani**

B.Tech Computer Science Engineering  
Bennett University

GitHub: [mahek12345678](https://github.com/mahek12345678)

---

## Feedback

Aptly is actively evolving.

If you find the project useful or have suggestions, feel free to open an issue or contribute.

If you like the project, consider giving the repository a ⭐.
