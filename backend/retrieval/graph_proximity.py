from __future__ import annotations
import networkx as nx


def compute_graph_proximity(
    paper_id: str,
    anchor_papers: list[str],
    graph: nx.MultiDiGraph,
    max_hops: int = 3,
) -> float:
    """
    Score a paper by its graph distance to anchor papers.
    1.0 for direct connection, 0.5 for 2 hops, etc. Capped at max_hops.
    """
    if not anchor_papers or paper_id not in graph:
        return 0.0

    undirected = graph.to_undirected()
    scores: list[float] = []

    for anchor in anchor_papers:
        if anchor not in undirected:
            scores.append(0.0)
            continue
        if anchor == paper_id:
            scores.append(1.0)
            continue
        try:
            length = nx.shortest_path_length(undirected, paper_id, anchor)
            if length > max_hops:
                scores.append(0.0)
            else:
                scores.append(1.0 / (1.0 + length))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            scores.append(0.0)

    return sum(scores) / len(anchor_papers) if scores else 0.0
