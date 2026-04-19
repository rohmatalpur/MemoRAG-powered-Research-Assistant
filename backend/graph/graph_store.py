from __future__ import annotations
import os
import pickle
from pathlib import Path

import networkx as nx

from backend.config import GRAPH_PATH


def load_graph() -> nx.MultiDiGraph:
    path = Path(GRAPH_PATH)
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return nx.MultiDiGraph()


def save_graph(G: nx.MultiDiGraph) -> None:
    path = Path(GRAPH_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(G, f)


def recompute_pagerank(G: nx.MultiDiGraph) -> None:
    paper_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "paper"]
    if len(paper_nodes) < 2:
        for pid in paper_nodes:
            G.nodes[pid]["pagerank_score"] = 1.0
        return

    paper_subgraph = G.subgraph(paper_nodes).copy()
    try:
        scores = nx.pagerank(paper_subgraph, alpha=0.85)
    except Exception:
        scores = {pid: 1.0 / len(paper_nodes) for pid in paper_nodes}

    for paper_id, score in scores.items():
        G.nodes[paper_id]["pagerank_score"] = score


def get_graph_export(G: nx.MultiDiGraph) -> dict:
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            "id": node_id,
            "type": data.get("type", "unknown"),
            "label": data.get("title") or data.get("label", node_id),
            "year": data.get("year"),
            "session_added": data.get("session_added"),
            "pagerank_score": data.get("pagerank_score", 0.0),
            "paper_count": data.get("paper_count", 0),
        })

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "rel": data.get("rel", ""),
            "similarity": data.get("similarity"),
            "on_concept": data.get("on_concept"),
        })

    return {"nodes": nodes, "edges": edges}
