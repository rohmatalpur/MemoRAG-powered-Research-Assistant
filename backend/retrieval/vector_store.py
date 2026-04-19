from __future__ import annotations
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from backend.config import QDRANT_HOST, QDRANT_PORT, EMBEDDING_DIM

COLLECTIONS = ["chunks", "papers", "concepts", "memories"]


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collections(client: QdrantClient) -> None:
    existing = {c.name for c in client.get_collections().collections}
    for name in COLLECTIONS:
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )


def upsert_chunk(client: QdrantClient, chunk_id: str, vector: list[float], payload: dict) -> None:
    client.upsert(
        collection_name="chunks",
        points=[PointStruct(id=chunk_id, vector=vector, payload=payload)],
    )


def upsert_paper_memory(client: QdrantClient, paper_id: str, vector: list[float], payload: dict) -> None:
    client.upsert(
        collection_name="memories",
        points=[PointStruct(id=paper_id, vector=vector, payload=payload)],
    )


def upsert_paper_vec(client: QdrantClient, paper_id: str, vector: list[float], payload: dict) -> None:
    client.upsert(
        collection_name="papers",
        points=[PointStruct(id=paper_id, vector=vector, payload=payload)],
    )


def search_memories(
    client: QdrantClient,
    query_vec: list[float],
    limit: int = 40,
) -> list[dict]:
    results = client.search(
        collection_name="memories",
        query_vector=query_vec,
        limit=limit,
        with_payload=True,
    )
    return [
        {**r.payload, "_score": r.score, "id": str(r.id)}
        for r in results
    ]


def search_chunks(
    client: QdrantClient,
    query_vec: list[float],
    limit: int = 50,
    paper_id_filter: Optional[str] = None,
) -> list[dict]:
    filt = None
    if paper_id_filter:
        filt = Filter(must=[FieldCondition(
            key="paper_id",
            match=MatchValue(value=paper_id_filter),
        )])

    results = client.search(
        collection_name="chunks",
        query_vector=query_vec,
        limit=limit,
        with_payload=True,
        query_filter=filt,
    )
    return [
        {**r.payload, "_score": r.score, "id": str(r.id), "vector": None}
        for r in results
    ]


def search_concepts(
    client: QdrantClient,
    query_vec: list[float],
    limit: int = 10,
) -> list[dict]:
    results = client.search(
        collection_name="concepts",
        query_vector=query_vec,
        limit=limit,
        with_payload=True,
    )
    return [
        {"id": str(r.id), "payload": r.payload, "_score": r.score}
        for r in results
    ]


def delete_paper_vectors(client: QdrantClient, paper_id: str) -> None:
    for coll in ["chunks", "memories", "papers"]:
        client.delete(
            collection_name=coll,
            points_selector=Filter(must=[FieldCondition(
                key="paper_id",
                match=MatchValue(value=paper_id),
            )]),
        )
