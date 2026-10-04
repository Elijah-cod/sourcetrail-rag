"""Checks the real embedding model. Skipped if the model can't be downloaded."""

import math

import pytest

from app.config import get_settings


@pytest.fixture(scope="module")
def embedder():
    try:
        from app.embed import FastEmbedEmbedder

        s = get_settings()
        return FastEmbedEmbedder(s.embedding_model, s.embedding_dim, s.model_cache_dir)
    except Exception as exc:  # no internet, blocked download, ...
        pytest.skip(f"embedding model unavailable: {exc}")


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def test_vectors_have_384_dimensions(embedder):
    vectors = embedder.embed_documents(["hello world", "second text"])
    assert len(vectors) == 2 and all(len(v) == 384 for v in vectors)
    assert len(embedder.embed_query("a question")) == 384


def test_similar_meaning_scores_higher(embedder):
    question = embedder.embed_query("How do I install the software?")
    install, bananas = embedder.embed_documents(
        ["Installation steps: download the package and run the setup script.",
         "Bananas are a good source of potassium."]
    )
    assert cosine(question, install) > cosine(question, bananas)
