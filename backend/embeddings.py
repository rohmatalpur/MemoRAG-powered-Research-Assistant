from __future__ import annotations
from functools import lru_cache

import openai

from backend.config import OPENAI_API_KEY, EMBEDDING_MODEL


_client: openai.OpenAI | None = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return _client


def embed(text: str) -> list[float]:
    """Embed a single string. Returns list of floats."""
    client = _get_client()
    text = text.replace("\n", " ").strip()
    if not text:
        from backend.config import EMBEDDING_DIM
        return [0.0] * EMBEDDING_DIM
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Embed a batch of strings."""
    client = _get_client()
    results: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ").strip() for t in texts[i:i + batch_size]]
        batch = [t if t else " " for t in batch]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        for item in sorted(response.data, key=lambda x: x.index):
            results.append(item.embedding)
    return results


def average_embeddings(embeddings: list[list[float]]) -> list[float]:
    if not embeddings:
        from backend.config import EMBEDDING_DIM
        return [0.0] * EMBEDDING_DIM
    n = len(embeddings)
    dim = len(embeddings[0])
    avg = [sum(emb[i] for emb in embeddings) / n for i in range(dim)]
    return avg
