import asyncio
import json
from app.services.llm_service import llm_service

desc = """Introduction Ladybird Web Solution is offering an internship programme for freshers to start their careers in the field of software development. Purpose of this engagement is to hire good candidates and offer them full time job after they finish the internship. Who are we looking for? Freshers graduated from reputed engineering colleges in India Candidate having Creative Thinking and Original Approach Willingness & ability to learn & work on new technologies Responsibilities/Learning As part of the"""

resume_data = {
    "projects": [
        {
            "project_id": "proj_1",
            "title": "Route53 Clone",
            "bullets": [
                "Built full-stack application with Next.js/TypeScript frontend and FastAPI REST backend.",
                "Designed relational schema in SQLite with SQLAlchemy.",
                "Implemented data validation and transaction handling.",
                "Documented scaling plan for DNS query routing.",
            ],
        },
        {
            "project_id": "proj_2",
            "title": "AI Research Paper Assistant",
            "bullets": ["Built RAG pipeline using ChromaDB vector database and FastAPI."],
        },
        {
            "project_id": "proj_3",
            "title": "Lendora AI",
            "bullets": ["Built machine learning credit risk evaluation pipeline."],
        },
    ],
    "skills": ["Python", "FastAPI", "TypeScript", "Next.js", "System Design"],
    "experience": [],
    "education": ["Computer Science, Expected Graduation: 2028"],
    "achievements": ["Solved 150+ DSA problems on LeetCode"],
}

async def main():
    jd_data = await llm_service.analyze_job_description(desc)
    res = await llm_service.evaluate_resume_match(jd_data, resume_data)
    print("overall_match_score:", res.get("overall_match_score"))
    print("match_breakdown:", res.get("match_breakdown"))
    print("verified_matches:", [m["canonical_requirement"] for m in res.get("verified_matches", [])])
    print("requirements:")
    for r in res.get("normalized_requirements", []):
        print(f"  canonical: {r.get('canonical')}, category: {r.get('category')}, importance: {r.get('importance')}, status: {r.get('match_status')}")

asyncio.run(main())
