from __future__ import annotations
import networkx as nx

from backend.models import PaperMemory


def build_compressed_memory_block(
    top_memories: list[dict],   # list of Qdrant payloads with paper_id, memory_digest
    graph: nx.MultiDiGraph,
    max_memories: int = 20,
) -> str:
    """
    Re-rank top memories by PageRank score and format into a context block.
    top_memories: [{paper_id, title, authors, year, core_claim, key_results, methodology, ...}]
    """
    def pagerank_score(m: dict) -> float:
        pid = m.get("paper_id", "")
        if pid in graph:
            return graph.nodes[pid].get("pagerank_score", 0.0)
        return 0.0

    sorted_memories = sorted(
        top_memories,
        key=lambda m: 0.6 * m.get("_score", 0.0) + 0.4 * pagerank_score(m),
        reverse=True,
    )[:max_memories]

    parts: list[str] = []
    for i, m in enumerate(sorted_memories, 1):
        title = m.get("title", "Unknown")
        authors = m.get("authors", [])
        year = m.get("year", "")
        author_str = ", ".join(authors[:2]) if authors else "Unknown"
        if len(authors) > 2:
            author_str += " et al."
        header = f"[{i}] {title} ({author_str}, {year})"

        lines = [header]
        if m.get("core_claim"):
            lines.append(f"  Claim: {m['core_claim']}")
        if m.get("key_results"):
            results = m["key_results"]
            if isinstance(results, list):
                lines.append(f"  Results: {'; '.join(results[:2])}")
            else:
                lines.append(f"  Results: {results}")
        if m.get("methodology"):
            lines.append(f"  Method: {m['methodology'][:150]}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def format_cluster_summary(
    relevant_concepts: list[dict],
    graph: nx.MultiDiGraph,
    max_concepts: int = 10,
) -> str:
    """
    Format top concept nodes and their paper connections into a readable summary.
    relevant_concepts: Qdrant search results with payload {label, definition}
    """
    parts: list[str] = []
    seen_labels: set[str] = set()

    for concept in relevant_concepts[:max_concepts]:
        payload = concept.get("payload", concept)
        label = payload.get("label", "")
        if not label or label in seen_labels:
            continue
        seen_labels.add(label)

        definition = payload.get("definition", "")[:150]
        concept_id = concept.get("id", "")

        # Find papers that discuss this concept
        paper_titles: list[str] = []
        if concept_id and concept_id in graph:
            for pred, _, data in graph.in_edges(concept_id, data=True):
                if data.get("rel") == "DISCUSSES" and graph.nodes.get(pred, {}).get("type") == "paper":
                    paper_titles.append(graph.nodes[pred].get("title", pred))

        line = f"• {label}: {definition}"
        if paper_titles:
            line += f" [discussed in: {', '.join(paper_titles[:3])}]"
        parts.append(line)

    return "\n".join(parts) if parts else "No relevant concept clusters found."
