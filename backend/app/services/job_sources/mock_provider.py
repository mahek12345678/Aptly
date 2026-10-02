"""Mock and development job source providing realistic software engineering listings."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from app.services.job_sources.base import BaseJobSource, JobListingData


class MockJobSource(BaseJobSource):
    """Provides high-quality realistic software engineering listings for development and matching."""

    async def fetch_jobs(self) -> List[JobListingData]:
        now = datetime.now(timezone.utc)

        return [
            JobListingData(
                external_id="stripe-backend-2026",
                source="mock",
                company="Stripe",
                role_title="Backend Engineer",
                location="San Francisco, CA (Hybrid)",
                employment_type="full_time",
                compensation="$170,000 - $210,000 / yr",
                deadline=now + timedelta(days=21),
                posted_at=now - timedelta(days=2),
                application_url="https://stripe.com/jobs/backend-engineer",
                description=(
                    "Stripe builds economic infrastructure for the internet. As a Backend Engineer, "
                    "you will design and build scalable distributed APIs and financial ledger services. "
                    "Requirements: Strong proficiency in Python, PostgreSQL, and distributed systems. "
                    "Experience with Docker, Kubernetes, and RESTful API architecture is highly desired. "
                    "You will partner with product teams to support millions of transactions daily."
                ),
            ),
            JobListingData(
                external_id="datadog-dist-systems-2026",
                source="mock",
                company="Datadog",
                role_title="Distributed Systems Engineer",
                location="New York, NY",
                employment_type="full_time",
                compensation="$165,000 - $195,000 / yr",
                deadline=now + timedelta(days=14),
                posted_at=now - timedelta(days=3),
                application_url="https://careers.datadoghq.com/distributed-systems",
                description=(
                    "Datadog is the monitoring and security platform for cloud applications. "
                    "We are seeking an engineer to build high-throughput telemetry pipelines. "
                    "Requirements: Deep knowledge of Go, Python, Kafka, and PostgreSQL. "
                    "Familiarity with Linux internals, distributed databases, and high-concurrency systems."
                ),
            ),
            JobListingData(
                external_id="figma-product-eng-2026",
                source="mock",
                company="Figma",
                role_title="Product Software Engineer",
                location="San Francisco, CA",
                employment_type="full_time",
                compensation="$160,000 - $190,000 / yr",
                deadline=now + timedelta(days=18),
                posted_at=now - timedelta(days=1),
                application_url="https://figma.com/careers/product-engineer",
                description=(
                    "Figma is connecting everyone in design and software creation. "
                    "We need Product Engineers to craft seamless collaborative web interfaces. "
                    "Requirements: Expertise in TypeScript, React, WebAssembly, and modern web performance. "
                    "Experience collaborating closely with product designers and backend systems."
                ),
            ),
            JobListingData(
                external_id="linear-fullstack-2026",
                source="mock",
                company="Linear",
                role_title="Full Stack Engineer",
                location="Remote",
                employment_type="full_time",
                compensation="$150,000 - $185,000 / yr",
                deadline=now + timedelta(days=30),
                posted_at=now - timedelta(days=4),
                application_url="https://linear.app/careers/fullstack",
                description=(
                    "Linear is the issue tracker modern software teams love. "
                    "We build fast, keyboard-first, real-time sync engines. "
                    "Requirements: Proficiency in TypeScript, React, Node.js, and PostgreSQL. "
                    "Obsession with UI polish, snappy latency, and clean component architecture."
                ),
            ),
            JobListingData(
                external_id="openai-platform-2026",
                source="mock",
                company="OpenAI",
                role_title="Software Engineer, Platform & API",
                location="San Francisco, CA",
                employment_type="full_time",
                compensation="$200,000 - $280,000 / yr",
                deadline=now + timedelta(days=25),
                posted_at=now - timedelta(days=5),
                application_url="https://openai.com/careers/platform-engineer",
                description=(
                    "OpenAI builds safe and beneficial AI. Our Platform team scales developer APIs "
                    "serving millions of inferences per second. "
                    "Requirements: Python, Go, Kubernetes, Redis, and high-scale cloud infrastructure. "
                    "Familiarity with LLM deployment, vector databases, and asynchronous streaming."
                ),
            ),
            JobListingData(
                external_id="vercel-frontend-infra-2026",
                source="mock",
                company="Vercel",
                role_title="Frontend Infrastructure Engineer",
                location="Remote",
                employment_type="full_time",
                compensation="$155,000 - $185,000 / yr",
                deadline=now + timedelta(days=20),
                posted_at=now - timedelta(days=2),
                application_url="https://vercel.com/careers/frontend-infra",
                description=(
                    "Vercel enables developers to build and deploy modern web apps. "
                    "We are seeking an engineer to improve Next.js core workflows and Edge runtime. "
                    "Requirements: TypeScript, React, Next.js, Rust or Node.js runtime fundamentals. "
                    "Experience with compiler toolchains, bundling, and web standards."
                ),
            ),
            JobListingData(
                external_id="google-swe-intern-2026",
                source="mock",
                company="Google",
                role_title="Software Engineering Intern",
                location="Mountain View, CA",
                employment_type="internship",
                compensation="$55 / hr",
                deadline=now + timedelta(days=12),
                posted_at=now - timedelta(days=6),
                application_url="https://careers.google.com/internships",
                description=(
                    "Join Google as a Software Engineering Intern. "
                    "Work on scalable products used by billions of users worldwide. "
                    "Requirements: Currently pursuing BS, MS, or PhD in Computer Science. "
                    "Solid knowledge of algorithms, data structures, and Python, C++, or Java. "
                    "Experience with Git and web development."
                ),
            ),
            JobListingData(
                external_id="meta-pe-intern-2026",
                source="mock",
                company="Meta",
                role_title="Production Engineering Intern",
                location="Menlo Park, CA",
                employment_type="internship",
                compensation="$58 / hr",
                deadline=now + timedelta(days=9),
                posted_at=now - timedelta(days=4),
                application_url="https://metacareers.com/internships",
                description=(
                    "Meta Production Engineers ensure our global services run reliably at massive scale. "
                    "Requirements: Enrolled in university program in Computer Science or related. "
                    "Proficiency in Python or C++, Linux systems, networking protocols, and debugging."
                ),
            ),
            JobListingData(
                external_id="apple-ios-dev-2026",
                source="mock",
                company="Apple",
                role_title="iOS Software Developer",
                location="Cupertino, CA",
                employment_type="full_time",
                compensation="$160,000 - $190,000 / yr",
                deadline=now + timedelta(days=28),
                posted_at=now - timedelta(days=3),
                application_url="https://jobs.apple.com/ios-dev",
                description=(
                    "Apple creates hardware and software experiences that delight users. "
                    "The iOS platform team is looking for passionate Swift and UIKit/SwiftUI engineers. "
                    "Requirements: Swift, Objective-C, iOS SDK, Core Data, and performance optimization."
                ),
            ),
            JobListingData(
                external_id="spotify-backend-systems-2026",
                source="mock",
                company="Spotify",
                role_title="Backend Systems Engineer",
                location="Boston, MA",
                employment_type="full_time",
                compensation="$155,000 - $185,000 / yr",
                deadline=now + timedelta(days=16),
                posted_at=now - timedelta(days=5),
                application_url="https://lifeatspotify.com/jobs/backend-systems",
                description=(
                    "Spotify powers music and podcast streaming across the world. "
                    "Join our Backend Systems squad building microservices and audio ingestion pipelines. "
                    "Requirements: Java or Python, Google Cloud Platform (GCP), PostgreSQL, and Docker."
                ),
            ),
            JobListingData(
                external_id="airbnb-fullstack-2026",
                source="mock",
                company="Airbnb",
                role_title="Full Stack Engineer, Guest Experience",
                location="Seattle, WA",
                employment_type="full_time",
                compensation="$165,000 - $195,000 / yr",
                deadline=now + timedelta(days=22),
                posted_at=now - timedelta(days=2),
                application_url="https://careers.airbnb.com/positions",
                description=(
                    "Airbnb makes travel accessible to everyone. We are looking for Full Stack Engineers "
                    "to enhance the discovery and booking flow for millions of travelers. "
                    "Requirements: React, TypeScript, Java or Python backend services, GraphQL, and MySQL."
                ),
            ),
            JobListingData(
                external_id="netflix-cloud-infra-2026",
                source="mock",
                company="Netflix",
                role_title="Cloud Infrastructure Engineer",
                location="Los Gatos, CA",
                employment_type="full_time",
                compensation="$180,000 - $230,000 / yr",
                deadline=now + timedelta(days=19),
                posted_at=now - timedelta(days=4),
                application_url="https://jobs.netflix.com/jobs",
                description=(
                    "Netflix streams entertainment to 250M+ households globally. "
                    "Join Cloud Infrastructure to operate AWS clusters and multi-region microservice fabrics. "
                    "Requirements: Python or Go, AWS, Docker, Kubernetes, Terraform, and site reliability."
                ),
            ),
        ]
