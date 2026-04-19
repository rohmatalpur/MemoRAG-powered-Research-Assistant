from __future__ import annotations
from collections import defaultdict

import networkx as nx

from backend.config import MIN_CLUSTER_PAPERS, MIN_CLUSTER_CONCEPTS


def detect_clusters(graph: nx.MultiDiGraph) -> list[dict]:
    """
    Run Louvain community detection. Returns list of cluster dicts.
    Falls back to simple connected-components if python-louvain not available.
    """
    undirected = graph.to_undirected()
    if undirected.number_of_nodes() < 4:
        return []

    try:
        import community as community_louvain
        partition = community_louvain.best_partition(undirected)
    except ImportError:
        # Fallback: connected components
        components = list(nx.connected_components(undirected))
        partition = {}
        for cid, comp in enumerate(components):
            for node in comp:
                partition[node] = cid

    clusters_raw: dict[int, list[str]] = defaultdict(list)
    for node_id, cluster_id in partition.items():
        clusters_raw[cluster_id].append(node_id)

    valid: list[dict] = []
    for cid, members in clusters_raw.items():
        paper_members = [m for m in members if graph.nodes.get(m, {}).get("type") == "paper"]
        concept_members = [m for m in members if graph.nodes.get(m, {}).get("type") == "concept"]
        if len(paper_members) >= MIN_CLUSTER_PAPERS and len(concept_members) >= MIN_CLUSTER_CONCEPTS:
            valid.append({
                "cluster_id": cid,
                "paper_members": paper_members,
                "concept_members": concept_members,
                "all_members": members,
            })

    return valid


def upsert_cluster_nodes(
    graph: nx.MultiDiGraph,
    clusters: list[dict],
    name_fn,  # callable: list[str] -> str
) -> list[str]:
    """
    Create or update ClusterNode entries in the graph.
    Returns list of cluster node ids that are new.
    """
    new_cluster_ids: list[str] = []

    existing_clusters = {
        data["cluster_id"]: nid
        for nid, data in graph.nodes(data=True)
        if data.get("type") == "cluster"
    }

    for cluster in clusters:
        cid = cluster["cluster_id"]
        node_key = f"cluster_{cid}"

        paper_titles = [
            graph.nodes[pid].get("title", pid)
            for pid in cluster["paper_members"]
        ]

        if node_key not in graph:
            label = name_fn(paper_titles)
            graph.add_node(node_key,
                           type="cluster",
                           cluster_id=cid,
                           label=label,
                           members=cluster["all_members"],
                           paper_count=len(cluster["paper_members"]))
            new_cluster_ids.append(node_key)
        else:
            # Update member list
            graph.nodes[node_key]["members"] = cluster["all_members"]
            graph.nodes[node_key]["paper_count"] = len(cluster["paper_members"])

    return new_cluster_ids
