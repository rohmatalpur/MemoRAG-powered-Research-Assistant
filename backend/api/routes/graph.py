from __future__ import annotations
import networkx as nx
from fastapi import APIRouter, HTTPException

from backend.graph.graph_store import load_graph, save_graph, get_graph_export
from backend.graph.community import detect_clusters, upsert_cluster_nodes
from backend.memory.memory_llm import MemoryLLM

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
async def get_graph():
    graph = load_graph()
    return get_graph_export(graph)


@router.get("/clusters")
async def get_clusters():
    graph = load_graph()
    clusters = [
        {
            "cluster_id": data.get("cluster_id"),
            "label": data.get("label", ""),
            "paper_count": data.get("paper_count", 0),
            "members": data.get("members", []),
        }
        for node_id, data in graph.nodes(data=True)
        if data.get("type") == "cluster"
    ]
    return clusters


@router.post("/clusters/redetect")
async def redetect_clusters():
    """Re-run community detection on the current graph and save results."""
    graph = load_graph()
    memory_llm = MemoryLLM()
    clusters = detect_clusters(graph)
    new_ids = upsert_cluster_nodes(graph, clusters, memory_llm.name_cluster)
    save_graph(graph)
    return {
        "clusters_found": len(clusters),
        "new_cluster_nodes": len(new_ids),
        "clusters": [
            {
                "cluster_id": data.get("cluster_id"),
                "label": data.get("label", ""),
                "paper_count": data.get("paper_count", 0),
            }
            for node_id, data in graph.nodes(data=True)
            if data.get("type") == "cluster"
        ],
    }


@router.get("/paper/{paper_id}/neighbors")
async def get_paper_neighbors(paper_id: str, depth: int = 1):
    graph = load_graph()
    if paper_id not in graph:
        raise HTTPException(404, "Paper not found in graph")

    neighbors: list[dict] = []
    for neighbor in nx.ego_graph(graph, paper_id, radius=depth).nodes():
        if neighbor == paper_id:
            continue
        data = graph.nodes[neighbor]
        neighbors.append({
            "id": neighbor,
            "type": data.get("type", ""),
            "label": data.get("title") or data.get("label", ""),
            "edge_types": [
                d.get("rel", "")
                for _, _, d in graph.edges(paper_id, data=True)
                if _ == paper_id and neighbor in graph[paper_id]
            ],
        })
    return neighbors


@router.get("/concepts")
async def get_concepts():
    graph = load_graph()
    return [
        {
            "id": node_id,
            "label": data.get("label", ""),
            "definition": data.get("definition", ""),
            "paper_count": data.get("paper_count", 0),
        }
        for node_id, data in graph.nodes(data=True)
        if data.get("type") == "concept"
    ]


@router.get("/concepts/{concept_id}/papers")
async def get_concept_papers(concept_id: str):
    graph = load_graph()
    if concept_id not in graph:
        raise HTTPException(404, "Concept not found")

    papers: list[dict] = []
    for pred, _, data in graph.in_edges(concept_id, data=True):
        if data.get("rel") == "DISCUSSES":
            pdata = graph.nodes.get(pred, {})
            if pdata.get("type") == "paper":
                papers.append({
                    "paper_id": pred,
                    "title": pdata.get("title", ""),
                    "year": pdata.get("year"),
                    "introduces": data.get("introduces", False),
                })
    return papers
