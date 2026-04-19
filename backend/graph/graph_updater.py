from __future__ import annotations
import networkx as nx
from qdrant_client import QdrantClient

from backend.models import ParsedPaper, PaperMemory, ConceptMemory, RelationalMemory
from backend.graph.concept_dedup import upsert_concept
from backend.graph.community import detect_clusters, upsert_cluster_nodes
from backend.memory.memory_llm import MemoryLLM


def update_graph_for_paper(
    paper: ParsedPaper,
    paper_memory: PaperMemory,
    concept_memories: list[ConceptMemory],
    relational_memory: RelationalMemory,
    graph: nx.MultiDiGraph,
    qdrant: QdrantClient,
    embed_fn,
    memory_llm: MemoryLLM,
    session_id: str,
    existing_paper_ids: set[str],
) -> dict:
    """
    Full graph update for a newly ingested paper.
    Returns delta: {new_edges, new_concepts, new_clusters, contradictions}
    """
    delta = {"new_edges": 0, "new_concepts": 0, "new_clusters": 0, "contradictions": 0}

    # a) Add PaperNode
    graph.add_node(
        paper.paper_id,
        type="paper",
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        session_added=session_id,
        memory_digest=paper_memory.core_claim,
        pagerank_score=0.0,
    )

    # b) Upsert concepts and DISCUSSES edges
    for concept in concept_memories:
        old_node_count = graph.number_of_nodes()
        upsert_concept(concept, paper.paper_id, graph, qdrant, embed_fn)
        if graph.number_of_nodes() > old_node_count:
            delta["new_concepts"] += 1
        delta["new_edges"] += 1

    # c) Relational edges to papers already in library
    for rel in relational_memory.references:
        ref_title = rel.get("ref_title", "")
        rel_type = rel.get("rel_type", "foundational")
        reason = rel.get("reason", "")
        matched_id = _find_paper_by_title(ref_title, graph)
        if matched_id:
            rel_map = {
                "foundational": "CITES",
                "extends": "EXTENDS",
                "critiques": "CRITIQUES",
                "uses_as_baseline": "CITES",
                "agrees_with": "CITES",
            }
            edge_rel = rel_map.get(rel_type, "CITES")
            graph.add_edge(paper.paper_id, matched_id,
                           rel=edge_rel,
                           context=reason[:200])
            delta["new_edges"] += 1

    # d) CONTRADICTS detection
    for concept_id, cdata in list(graph.nodes(data=True)):
        if cdata.get("type") != "concept":
            continue
        concept_label = cdata.get("label", "")

        # Papers that also discuss this concept
        peer_paper_ids: list[str] = []
        for pred, _, edata in graph.in_edges(concept_id, data=True):
            if (edata.get("rel") == "DISCUSSES"
                    and pred != paper.paper_id
                    and graph.nodes.get(pred, {}).get("type") == "paper"):
                peer_paper_ids.append(pred)

        for peer_id in peer_paper_ids[:5]:  # cap to avoid too many LLM calls
            peer_data = graph.nodes[peer_id]
            contradicts, reason = memory_llm.detect_contradiction(
                concept=concept_label,
                paper_a_title=paper.title,
                claim_a=paper_memory.core_claim,
                paper_b_title=peer_data.get("title", ""),
                claim_b=peer_data.get("memory_digest", ""),
            )
            if contradicts:
                graph.add_edge(paper.paper_id, peer_id,
                               rel="CONTRADICTS",
                               on_concept=concept_label,
                               evidence=reason[:300])
                delta["contradictions"] += 1
                delta["new_edges"] += 1

    # e) Cluster re-detection
    clusters = detect_clusters(graph)
    new_clusters = upsert_cluster_nodes(graph, clusters, memory_llm.name_cluster)
    delta["new_clusters"] = len(new_clusters)

    return delta


def _find_paper_by_title(ref_title: str, graph: nx.MultiDiGraph) -> str | None:
    if not ref_title:
        return None
    ref_lower = ref_title.lower().strip()
    best_id: str | None = None
    best_score = 0

    for node_id, data in graph.nodes(data=True):
        if data.get("type") != "paper":
            continue
        title = data.get("title", "").lower().strip()
        if not title:
            continue
        # Simple overlap score
        score = _title_overlap(ref_lower, title)
        if score > best_score and score > 0.6:
            best_score = score
            best_id = node_id

    return best_id


def _title_overlap(a: str, b: str) -> float:
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / max(len(words_a), len(words_b))
