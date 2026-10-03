"""Vector storage and semantic embeddings service using ChromaDB and SentenceTransformers.

Persists resume chunks in ChromaDB with metadata (user_id, resume_id, section, chunk_index).
Ensures user data isolation and model reuse across requests.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Lazy-loaded embedding service supporting local CPU SentenceTransformer, ONNX, and remote providers."""

    _instance: Any = None
    _provider: Optional[str] = None

    @classmethod
    def get_model(cls) -> Any:
        provider = (getattr(settings, "EMBEDDING_PROVIDER", "local") or "local").lower()
        if cls._instance is None or cls._provider != provider:
            cls._provider = provider
            if provider == "local":
                import os

                # Force CPU-only execution and limit thread overhead in memory-constrained environments
                os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
                os.environ.setdefault("OMP_NUM_THREADS", "1")
                os.environ.setdefault("MKL_NUM_THREADS", "1")
                try:
                    import torch

                    torch.set_num_threads(1)
                except ImportError:
                    pass

                from sentence_transformers import SentenceTransformer

                logger.info(
                    "Loading SentenceTransformer model (CPU-only): %s",
                    settings.EMBEDDING_MODEL_NAME,
                )
                cls._instance = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, device="cpu")
                logger.info("SentenceTransformer CPU model loaded successfully.")

            elif provider == "onnx":
                # Ultra-lightweight ONNX runtime (~65MB RSS) using Chroma's built-in all-MiniLM-L6-v2
                from chromadb.utils import embedding_functions

                logger.info("Loading Chroma DefaultEmbeddingFunction (ONNX all-MiniLM-L6-v2)")
                cls._instance = embedding_functions.DefaultEmbeddingFunction()
                logger.info("ONNX embedding function loaded successfully.")

            elif provider == "remote":
                logger.info("Configured remote embedding provider (URL: %s)", settings.REMOTE_EMBEDDING_URL)
                cls._instance = "remote"

            else:
                logger.warning("Unknown EMBEDDING_PROVIDER '%s', falling back to local CPU", provider)
                from sentence_transformers import SentenceTransformer

                cls._instance = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, device="cpu")

        return cls._instance

    @classmethod
    def generate_embeddings(cls, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        provider = (getattr(settings, "EMBEDDING_PROVIDER", "local") or "local").lower()
        model = cls.get_model()

        if provider == "local" or hasattr(model, "encode"):
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings.tolist()

        elif provider == "onnx":
            result = model(texts)
            return [list(vec) for vec in result]

        elif provider == "remote":
            return cls._generate_remote_embeddings(texts)

        if hasattr(model, "encode"):
            return model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()
        return []

    @classmethod
    def _generate_remote_embeddings(cls, texts: list[str]) -> list[list[float]]:
        import requests

        url = settings.REMOTE_EMBEDDING_URL
        api_key = settings.REMOTE_EMBEDDING_API_KEY
        if not url:
            raise ValueError("REMOTE_EMBEDDING_URL must be configured when EMBEDDING_PROVIDER=remote")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        resp = requests.post(
            url,
            json={"input": texts, "model": settings.EMBEDDING_MODEL_NAME},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and isinstance(data["data"], list):
            return [item["embedding"] for item in data["data"]]
        raise ValueError("Unexpected remote embedding API response format")


class VectorStoreService:
    """ChromaDB vector store for chunked resume storage and querying with lazy initialization."""

    def __init__(self, persist_dir: Optional[Path] = None, collection_name: Optional[str] = None):
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIR)
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.jobs_collection_name = "aptly_jobs"
        self._client = None
        self._collection = None
        self._jobs_collection = None

    @property
    def client(self):
        """Lazy-initialize persistent ChromaDB client only on first access."""
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        """Lazy-load the resume vector collection only on first access."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    @property
    def jobs_collection(self):
        """Lazy-load the jobs vector collection only on first access."""
        if self._jobs_collection is None:
            self._jobs_collection = self.client.get_or_create_collection(
                name=self.jobs_collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._jobs_collection

    def store_job_embedding(
        self,
        job_id: uuid.UUID | str,
        company: str,
        role_title: str,
        description: str,
        source: str = "mock",
    ) -> None:
        """Embed and persist a job listing in ChromaDB. Caches so unchanged listings are skipped."""
        j_id = str(job_id)
        try:
            existing = self.jobs_collection.get(ids=[j_id])
            if existing and existing.get("ids"):
                return

            text_to_embed = f"{role_title} at {company}. {description}"
            embedding = EmbeddingService.generate_embeddings([text_to_embed])[0]

            self.jobs_collection.upsert(
                ids=[j_id],
                embeddings=[embedding],
                documents=[text_to_embed],
                metadatas=[{
                    "job_id": j_id,
                    "company": company,
                    "role_title": role_title,
                    "source": source,
                }],
            )
            logger.info("Stored embedding for job %s (%s at %s)", j_id, role_title, company)
        except Exception as exc:
            logger.warning("Error storing job embedding %s: %s", j_id, exc)

    def query_jobs_similarity(
        self,
        query_text: str,
        n_results: int = 50,
    ) -> Dict[str, Any]:
        """Query job listings for similarity to candidate text."""
        query_embedding = EmbeddingService.generate_embeddings([query_text])[0]
        return self.jobs_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

    def compute_cosine_similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts using the singleton embedding model."""
        import numpy as np
        emb = EmbeddingService.generate_embeddings([text_a, text_b])
        v1, v2 = np.array(emb[0]), np.array(emb[1])
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        sim = float(np.dot(v1, v2) / (norm1 * norm2))
        return max(0.0, min(1.0, sim))

    def store_resume_chunks(
        self,
        resume_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
        parsed_data: Dict[str, Any],
        raw_text: str,
    ) -> int:
        """Chunk a parsed resume by section, generate embeddings, and store in ChromaDB.
        Deletes any previous vectors for this resume before storing.
        """
        r_id = str(resume_id)
        u_id = str(user_id)

        # 1. Clean out existing chunks for this resume to prevent stale duplicates
        self.delete_resume_vectors(resume_id=r_id, user_id=u_id)

        # 2. Extract section chunks
        chunks: list[dict[str, Any]] = self._create_resume_chunks(
            r_id=r_id,
            u_id=u_id,
            parsed_data=parsed_data,
            raw_text=raw_text,
        )

        if not chunks:
            logger.warning("No chunks generated for resume %s (user %s)", r_id, u_id)
            return 0

        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        ids = [c["id"] for c in chunks]

        # 3. Generate embeddings using shared model
        embeddings = EmbeddingService.generate_embeddings(documents)

        # 4. Upsert vectors into ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "Stored %d vector chunks for resume %s (user %s) in ChromaDB collection '%s'",
            len(chunks),
            r_id,
            u_id,
            self.collection_name,
        )
        return len(chunks)

    def delete_resume_vectors(self, resume_id: uuid.UUID | str, user_id: uuid.UUID | str) -> None:
        """Safely delete all vector chunks for a specific resume belonging to a user."""
        r_id = str(resume_id)
        u_id = str(user_id)

        try:
            # Query IDs with strict user_id and resume_id isolation
            results = self.collection.get(
                where={
                    "$and": [
                        {"user_id": {"$eq": u_id}},
                        {"resume_id": {"$eq": r_id}},
                    ]
                }
            )
            existing_ids = results.get("ids", [])
            if existing_ids:
                self.collection.delete(ids=existing_ids)
                logger.info("Deleted %d existing chunks for resume %s", len(existing_ids), r_id)
        except Exception as exc:
            logger.warning("Error deleting vectors for resume %s: %s", r_id, exc)

    def delete_all_user_vectors(self, user_id: uuid.UUID | str) -> None:
        """Safely delete all vector chunks belonging to a user."""
        u_id = str(user_id)
        try:
            results = self.collection.get(where={"user_id": {"$eq": u_id}})
            existing_ids = results.get("ids", [])
            if existing_ids:
                self.collection.delete(ids=existing_ids)
                logger.info("Deleted %d existing chunks for user %s", len(existing_ids), u_id)
        except Exception as exc:
            logger.warning("Error deleting all vectors for user %s: %s", u_id, exc)

    def query_resume_vectors(
        self,
        user_id: uuid.UUID | str,
        query: str,
        n_results: int = 5,
        section_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query vector database for similar chunks strictly scoped to the user."""
        u_id = str(user_id)
        query_embedding = EmbeddingService.generate_embeddings([query])[0]

        where_clause: dict[str, Any]
        if section_filter:
            where_clause = {
                "$and": [
                    {"user_id": {"$eq": u_id}},
                    {"section": {"$eq": section_filter}},
                ]
            }
        else:
            where_clause = {"user_id": {"$eq": u_id}}

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
        )

    def _create_resume_chunks(
        self,
        r_id: str,
        u_id: str,
        parsed_data: Dict[str, Any],
        raw_text: str,
    ) -> list[dict[str, Any]]:
        """Chunk parsed resume by meaningful sections."""
        chunks: list[dict[str, Any]] = []
        chunk_idx = 0

        # 1. Summary Chunk
        summary = parsed_data.get("summary")
        if summary and len(summary.strip()) > 10:
            chunks.append({
                "id": f"{r_id}_summary_{chunk_idx}",
                "text": f"Professional Summary: {summary.strip()}",
                "metadata": {
                    "user_id": u_id,
                    "resume_id": r_id,
                    "section": "summary",
                    "chunk_index": chunk_idx,
                },
            })
            chunk_idx += 1

        # 2. Skills Chunk(s)
        skills = parsed_data.get("skills", [])
        if skills:
            skills_text = ", ".join(skills)
            chunks.append({
                "id": f"{r_id}_skills_{chunk_idx}",
                "text": f"Skills: {skills_text}",
                "metadata": {
                    "user_id": u_id,
                    "resume_id": r_id,
                    "section": "skills",
                    "chunk_index": chunk_idx,
                },
            })
            chunk_idx += 1

        # 3. Experience Chunks (one chunk per role/entry if itemized, or section text)
        experience_items = parsed_data.get("experience", [])
        if experience_items:
            for item in experience_items:
                if isinstance(item, dict):
                    item_text = item.get("entry") or f"{item.get('role', '')} at {item.get('company', '')}: {' '.join(item.get('bullets', []))}"
                else:
                    item_text = str(item)
                if len(item_text.strip()) > 10:
                    chunks.append({
                        "id": f"{r_id}_experience_{chunk_idx}",
                        "text": f"Experience: {item_text.strip()}",
                        "metadata": {
                            "user_id": u_id,
                            "resume_id": r_id,
                            "section": "experience",
                            "chunk_index": chunk_idx,
                        },
                    })
                    chunk_idx += 1

        # 4. Education Chunks
        education_items = parsed_data.get("education", [])
        if education_items:
            for item in education_items:
                if isinstance(item, dict):
                    item_text = item.get("entry") or f"{item.get('degree', '')} from {item.get('institution', '')}"
                else:
                    item_text = str(item)
                if len(item_text.strip()) > 10:
                    chunks.append({
                        "id": f"{r_id}_education_{chunk_idx}",
                        "text": f"Education: {item_text.strip()}",
                        "metadata": {
                            "user_id": u_id,
                            "resume_id": r_id,
                            "section": "education",
                            "chunk_index": chunk_idx,
                        },
                    })
                    chunk_idx += 1

        # 5. Projects Chunks
        project_items = parsed_data.get("projects", [])
        if project_items:
            for item in project_items:
                if isinstance(item, dict):
                    item_text = item.get("entry") or item.get("description") or f"{item.get('project_title', '')} {' '.join(item.get('project_bullets', []))}"
                else:
                    item_text = str(item)
                if len(item_text.strip()) > 10:
                    chunks.append({
                        "id": f"{r_id}_projects_{chunk_idx}",
                        "text": f"Project: {item_text.strip()}",
                        "metadata": {
                            "user_id": u_id,
                            "resume_id": r_id,
                            "section": "projects",
                            "chunk_index": chunk_idx,
                        },
                    })
                    chunk_idx += 1

        # 6. Certifications Chunks
        cert_items = parsed_data.get("certifications", [])
        if cert_items:
            for item in cert_items:
                if len(item.strip()) > 5:
                    chunks.append({
                        "id": f"{r_id}_certifications_{chunk_idx}",
                        "text": f"Certification: {item.strip()}",
                        "metadata": {
                            "user_id": u_id,
                            "resume_id": r_id,
                            "section": "certifications",
                            "chunk_index": chunk_idx,
                        },
                    })
                    chunk_idx += 1

        # 7. Achievements Chunks
        achievement_items = parsed_data.get("achievements", [])
        if achievement_items:
            for item in achievement_items:
                if len(item.strip()) > 5:
                    chunks.append({
                        "id": f"{r_id}_achievements_{chunk_idx}",
                        "text": f"Achievement: {item.strip()}",
                        "metadata": {
                            "user_id": u_id,
                            "resume_id": r_id,
                            "section": "achievements",
                            "chunk_index": chunk_idx,
                        },
                    })
                    chunk_idx += 1

        # 8. Fallback: If no structured sections were created, chunk raw_text directly
        if not chunks and raw_text:
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            for p in paragraphs:
                if len(p) > 20:
                    chunks.append({
                        "id": f"{r_id}_raw_{chunk_idx}",
                        "text": p,
                        "metadata": {
                            "user_id": u_id,
                            "resume_id": r_id,
                            "section": "raw_content",
                            "chunk_index": chunk_idx,
                        },
                    })
                    chunk_idx += 1

        return chunks


# Singleton vector store instance
vector_store = VectorStoreService()
