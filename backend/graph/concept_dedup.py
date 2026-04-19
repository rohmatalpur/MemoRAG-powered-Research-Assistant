from __future__ import annotations
from uuid import uuid4

import networkx as nx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.models import ConceptMemory
from backend.config import CONCEPT_MERGE_THRESHOLD, CONCEPT_SIMILAR_THRESHOLD


def upsert_concept(
    concept: ConceptMemory,
    paper_id: str,
    graph: nx.MultiDiGraph,
    qdrant: QdrantClient,
    embed_fn,
) -> str:
    """
    Find or create a concept node. Returns the concept_id to use.
    Also adds a DISCUSSES edge from paper_id → concept_id.
    """
    if not concept.concept or not concept.definition:
        return ""

    concept_text = f"{concept.concept}: {concept.definition}"
    concept_vec = embed_fn(concept_text)

    hits = qdrant.search(
        collection_name="concepts",
        query_vector=concept_vec,
        limit=5,
        score_threshold=CONCEPT_SIMILAR_THRESHOLD,
    )

    concept_id: str
    if not hits:
        concept_id = _create_new_concept(concept, concept_vec, graph, qdrant)
    else:
        top_hit = hits[0]
        if top_hit.score > CONCEPT_MERGE_THRESHOLD:
            # Merge: reuse existing node
            concept_id = str(top_hit.id)
            if concept_id in graph:
                graph.nodes[concept_id]["paper_count"] = graph.nodes[concept_id].get("paper_count", 0) + 1
        else:
            # Similar but distinct
            concept_id = _create_new_concept(concept, concept_vec, graph, qdrant)
            graph.add_edge(concept_id, str(top_hit.id),
                           rel="SIMILAR_TO",
                           similarity=float(top_hit.score))

    # DISCUSSES edge: paper → concept
    if paper_id and concept_id:
        graph.add_edge(paper_id, concept_id,
                       rel="DISCUSSES",
                       introduces=concept.introduced_here)

    return concept_id


def _create_new_concept(
    concept: ConceptMemory,
    vector: list[float],
    graph: nx.MultiDiGraph,
    qdrant: QdrantClient,
) -> str:
    concept_id = str(uuid4())
    graph.add_node(
        concept_id,
        type="concept",
        label=concept.concept,
        definition=concept.definition,
        embedding_id=concept_id,
        paper_count=1,
    )
    qdrant.upsert(
        collection_name="concepts",
        points=[PointStruct(
            id=concept_id,
            vector=vector,
            payload={
                "label": concept.concept,
                "definition": concept.definition[:500],
            },
        )],
    )
    return concept_id
