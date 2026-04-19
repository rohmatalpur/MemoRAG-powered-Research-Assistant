"use client";
import { useEffect, useState } from "react";
import type { GraphData, GraphNode, Cluster } from "@/lib/types";
import { getGraph, getClusters, getPaperNeighbors, getConceptPapers, redetectClusters } from "@/lib/api";
import KnowledgeGraph from "@/components/KnowledgeGraph";

export default function GraphPage() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [nodeDetail, setNodeDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"graph" | "clusters">("graph");
  const [redetecting, setRedetecting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [g, c] = await Promise.all([getGraph(), getClusters()]);
        setGraphData(g);
        setClusters(c);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleRedetect = async () => {
    setRedetecting(true);
    try {
      const result = await redetectClusters();
      setClusters(result.clusters);
      // Refresh full graph so cluster nodes appear
      const g = await getGraph();
      setGraphData(g);
    } catch (e: any) {
      alert(`Re-detection failed: ${e.message}`);
    } finally {
      setRedetecting(false);
    }
  };

  const handleNodeClick = async (node: GraphNode) => {
    setSelectedNode(node);
    setNodeDetail(null);
    setDetailLoading(true);
    try {
      if (node.type === "paper") {
        const neighbors = await getPaperNeighbors(node.id);
        setNodeDetail({ neighbors });
      } else if (node.type === "concept") {
        const papers = await getConceptPapers(node.id);
        setNodeDetail({ papers });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setDetailLoading(false);
    }
  };

  const stats = {
    papers: graphData.nodes.filter((n) => n.type === "paper").length,
    concepts: graphData.nodes.filter((n) => n.type === "concept").length,
    edges: graphData.edges.length,
    clusters: clusters.length,
  };

  return (
    <div className="h-full flex gap-4">
      {/* Main graph area */}
      <div className="flex-1 flex flex-col gap-3">
        {/* Stats bar */}
        <div className="flex gap-4 bg-white border border-gray-200 rounded-xl p-3">
          <Stat label="Papers" value={stats.papers} color="blue" />
          <Stat label="Concepts" value={stats.concepts} color="amber" />
          <Stat label="Links" value={stats.edges} color="gray" />
          <Stat label="Clusters" value={stats.clusters} color="purple" />
        </div>

        {/* Graph canvas */}
        <div className="flex-1 bg-white border border-gray-200 rounded-xl overflow-hidden relative">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              Loading knowledge graph…
            </div>
          ) : graphData.nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm">
              <p className="text-4xl mb-2">🕸️</p>
              <p>No graph yet. Upload papers to build your knowledge graph.</p>
            </div>
          ) : (
            <KnowledgeGraph data={graphData} onNodeClick={handleNodeClick} />
          )}
        </div>
      </div>

      {/* Sidebar: node detail + clusters */}
      <div className="w-72 flex flex-col gap-3">
        {/* Tab switcher */}
        <div className="flex border border-gray-200 rounded-lg overflow-hidden text-sm">
          {(["graph", "clusters"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 capitalize transition-colors ${
                activeTab === tab
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === "graph" ? (
          <div className="flex-1 bg-white border border-gray-200 rounded-xl p-4 overflow-y-auto">
            {selectedNode ? (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className={`w-3 h-3 rounded-full ${
                      selectedNode.type === "paper"
                        ? "bg-blue-500"
                        : selectedNode.type === "concept"
                        ? "bg-amber-400"
                        : "bg-purple-500"
                    }`}
                  />
                  <span className="text-xs text-gray-500 capitalize">
                    {selectedNode.type}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 text-sm mb-2 leading-snug">
                  {selectedNode.label}
                </h3>
                {selectedNode.year && (
                  <p className="text-xs text-gray-400 mb-2">{selectedNode.year}</p>
                )}
                {(selectedNode.pagerank_score ?? 0) > 0 && (
                  <p className="text-xs text-gray-400 mb-3">
                    Importance: {((selectedNode.pagerank_score ?? 0) * 100).toFixed(1)}%
                  </p>
                )}

                {detailLoading && (
                  <p className="text-xs text-gray-400">Loading…</p>
                )}

                {nodeDetail?.neighbors && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                      Connected Papers
                    </p>
                    <ul className="space-y-1">
                      {nodeDetail.neighbors.map((n: any) => (
                        <li key={n.id} className="text-xs text-gray-700">
                          · {n.label}
                          {n.edge_types?.length > 0 && (
                            <span className="text-gray-400 ml-1">
                              ({n.edge_types[0]})
                            </span>
                          )}
                        </li>
                      ))}
                      {nodeDetail.neighbors.length === 0 && (
                        <li className="text-xs text-gray-400">No connections yet</li>
                      )}
                    </ul>
                  </div>
                )}

                {nodeDetail?.papers && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                      Papers Discussing This
                    </p>
                    <ul className="space-y-1">
                      {nodeDetail.papers.map((p: any) => (
                        <li key={p.paper_id} className="text-xs text-gray-700">
                          · {p.title}
                          {p.introduces && (
                            <span className="text-green-600 ml-1">(introduces)</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center mt-8">
                Click a node to see details
              </p>
            )}
          </div>
        ) : (
          <div className="flex-1 bg-white border border-gray-200 rounded-xl p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-gray-500 uppercase">
                Concept Clusters ({clusters.length})
              </h3>
              <button
                onClick={handleRedetect}
                disabled={redetecting}
                className="text-xs px-2 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-40"
              >
                {redetecting ? "Detecting…" : "↺ Re-detect"}
              </button>
            </div>
            {clusters.length === 0 ? (
              <p className="text-xs text-gray-400">
                Clusters form when ≥3 papers share at least 1 concept. Click ↺ Re-detect to scan now.
              </p>
            ) : (
              <div className="space-y-3">
                {clusters.map((c) => (
                  <div
                    key={String(c.cluster_id)}
                    className="border border-purple-100 bg-purple-50 rounded-lg p-2"
                  >
                    <p className="text-xs font-semibold text-purple-800">
                      {c.label}
                    </p>
                    <p className="text-xs text-purple-500">
                      {c.paper_count} papers
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    blue: "text-blue-600",
    amber: "text-amber-600",
    gray: "text-gray-600",
    purple: "text-purple-600",
  };
  return (
    <div className="text-center">
      <p className={`text-xl font-bold ${colorMap[color]}`}>{value}</p>
      <p className="text-xs text-gray-400">{label}</p>
    </div>
  );
}
