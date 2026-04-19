from __future__ import annotations
import networkx as nx
from qdrant_client import QdrantClient

from backend.models import MemoryClue
from backend.retrieval.vector_store import search_chunks, search_memories, search_concepts
from backend.retrieval.reranker import rerank_chunks
from backend.memory.compressor import build_compressed_memory_block, format_cluster_summary
from backend.config import RETRIEVAL_CANDIDATES, TOP_MEMORIES_FOR_CLUE


def embed_text(text: str, embed_fn) -> list[float]:
    return embed_fn(text)


def build_retrieval_signal(query: str, clue: MemoryClue) -> str:
    parts = [query]
    if clue.text:
        parts.append(clue.text)
    if clue.suggested_terms:
        parts.append("Key terms: " + ", ".join(clue.suggested_terms))
    return "\n\n".join(parts)


def retrieve_and_rerank(
    query: str,
    clue: MemoryClue,
    qdrant: QdrantClient,
    graph: nx.MultiDiGraph,
    embed_fn,
    k: int = 10,
) -> list[dict]:
    # Build clue-guided retrieval signal
    retrieval_text = build_retrieval_signal(query, clue)
    retrieval_vec = embed_fn(retrieval_text)

    # Fetch top-N chunk candidates
    candidates = search_chunks(qdrant, retrieval_vec, limit=RETRIEVAL_CANDIDATES)

    # Attach embeddings to candidates for MMR (re-embed content)
    for c in candidates:
        c["embedding"] = embed_fn(c.get("content", ""))

    # Rerank
    top_chunks = rerank_chunks(
        query=query,
        candidates=candidates,
        query_embedding=retrieval_vec,
        anchor_papers=clue.mentioned_papers,
        graph=graph,
        k=k,
    )
    return top_chunks


def compress_global_memory(
    query: str,
    qdrant: QdrantClient,
    graph: nx.MultiDiGraph,
    embed_fn,
) -> str:
    query_vec = embed_fn(query)

    top_memories = search_memories(qdrant, query_vec, limit=TOP_MEMORIES_FOR_CLUE)
    relevant_concepts = search_concepts(qdrant, query_vec, limit=10)

    memory_block = build_compressed_memory_block(top_memories, graph)
    cluster_summary = format_cluster_summary(relevant_concepts, graph)

    return memory_block, cluster_summary
