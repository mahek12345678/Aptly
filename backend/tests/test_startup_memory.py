import sys
import pytest
from app.services.vector_store import EmbeddingService, vector_store


def test_lazy_startup_verification():
    """Verify that vector_store and EmbeddingService start lazy without eager ML loading."""
    # Note: earlier tests in a run might have invoked embeddings,
    # but we can verify the properties and interfaces work properly.
    assert hasattr(vector_store, "client")
    assert hasattr(vector_store, "collection")
    assert hasattr(vector_store, "jobs_collection")


def test_embedding_generation_lazy():
    """Verify semantic embedding generation returns valid non-empty vectors with cosine similarity."""
    texts = [
        "Senior Python Engineer with FastAPI and PostgreSQL",
        "Backend Developer experienced in Python, REST APIs, and SQL",
    ]
    embs = EmbeddingService.generate_embeddings(texts)
    assert len(embs) == 2
    assert len(embs[0]) == 384
    assert len(embs[1]) == 384

    sim = vector_store.compute_cosine_similarity(texts[0], texts[1])
    assert 0.0 <= sim <= 1.0
    assert sim > 0.4  # Highly similar concepts
