from __future__ import annotations
import numpy as np
import networkx as nx

from backend.config import (
    CROSS_ENCODER_WEIGHT, GRAPH_SCORE_WEIGHT, MMR_WEIGHT, MMR_LAMBDA, FINAL_CHUNKS
)
from backend.retrieval.graph_proximity import compute_graph_proximity


_cross_encoder = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def _cosine_sim(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def _mmr_select(
    candidates: list[dict],
    query_embedding: list[float],
    lambda_: float = MMR_LAMBDA,
    k: int = FINAL_CHUNKS,
) -> list[int]:
    """Returns indices of selected candidates in MMR order."""
    if not candidates:
        return []

    selected_indices: list[int] = []
    remaining = list(range(len(candidates)))

    while len(selected_indices) < k and remaining:
        scores = []
        for idx in remaining:
            emb = candidates[idx].get("embedding")
            if emb is None:
                relevance = 0.0
            else:
                relevance = _cosine_sim(emb, query_embedding)

            if not selected_indices:
                redundancy = 0.0
            else:
                redundancies = []
                for sel_idx in selected_indices:
                    sel_emb = candidates[sel_idx].get("embedding")
                    emb_c = candidates[idx].get("embedding")
                    if sel_emb and emb_c:
                        redundancies.append(_cosine_sim(emb_c, sel_emb))
                    else:
                        redundancies.append(0.0)
                redundancy = max(redundancies) if redundancies else 0.0

            scores.append(lambda_ * relevance - (1 - lambda_) * redundancy)

        best = remaining[int(np.argmax(scores))]
        selected_indices.append(best)
        remaining.remove(best)

    return selected_indices


def rerank_chunks(
    query: str,
    candidates: list[dict],
    query_embedding: list[float],
    anchor_papers: list[str],
    graph: nx.MultiDiGraph,
    k: int = FINAL_CHUNKS,
) -> list[dict]:
    """
    Three-stage reranking:
    1. Cross-encoder semantic score
    2. Graph proximity boost
    3. MMR diversity

    candidates: list of dicts with keys: content, paper_id, embedding (optional)
    """
    if not candidates:
        return []

    # Stage 1: cross-encoder scores
    ce = _get_cross_encoder()
    pairs = [(query, c.get("content", "")) for c in candidates]
    ce_scores: list[float] = ce.predict(pairs).tolist()

    # Stage 2: graph proximity
    graph_scores: list[float] = [
        compute_graph_proximity(c.get("paper_id", ""), anchor_papers, graph)
        for c in candidates
    ]

    # Attach intermediate scores
    for i, c in enumerate(candidates):
        c["_ce_score"] = ce_scores[i]
        c["_graph_score"] = graph_scores[i]

    # Stage 3: MMR-based selection
    # Score for MMR ordering: combine CE + graph first, use MMR for diversity
    combined_scores = [
        CROSS_ENCODER_WEIGHT * ce_scores[i] + GRAPH_SCORE_WEIGHT * graph_scores[i]
        for i in range(len(candidates))
    ]
    for i, c in enumerate(candidates):
        c["_combined_score"] = combined_scores[i]

    # Sort by combined score before MMR to give MMR best candidates to work with
    sorted_indices = sorted(range(len(candidates)), key=lambda i: combined_scores[i], reverse=True)
    sorted_candidates = [candidates[i] for i in sorted_indices]

    selected = _mmr_select(sorted_candidates, query_embedding, lambda_=MMR_LAMBDA, k=k)
    return [sorted_candidates[i] for i in selected]
