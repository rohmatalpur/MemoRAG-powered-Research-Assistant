"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import type { GraphData, GraphNode } from "@/lib/types";

interface Props {
  data: GraphData;
  onNodeClick?: (node: GraphNode) => void;
}

const NODE_COLORS: Record<string, string> = {
  paper: "#3B82F6",
  concept: "#F59E0B",
  cluster: "#8B5CF6",
};

const EDGE_COLORS: Record<string, string> = {
  CITES: "#9CA3AF",
  EXTENDS: "#60A5FA",
  CRITIQUES: "#EF4444",
  CONTRADICTS: "#EF4444",
  DISCUSSES: "#D1D5DB",
  SIMILAR_TO: "#FCD34D",
  default: "#D1D5DB",
};

const NODE_RADIUS: Record<string, number> = {
  paper: 10,
  cluster: 14,
  concept: 7,
};

export default function KnowledgeGraph({ data, onNodeClick }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const positions = useRef<Map<string, { x: number; y: number; vx: number; vy: number }>>(new Map());
  const animRef = useRef<number>(0);
  const sizeRef = useRef({ w: 900, h: 600 });

  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: GraphNode } | null>(null);

  // Resize canvas to match its CSS container — this is what fixes hit detection
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = container;
      if (w === 0 || h === 0) return;
      canvas.width = w;
      canvas.height = h;
      sizeRef.current = { w, h };
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Force simulation + draw loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const getSize = () => sizeRef.current;

    // Seed positions for new nodes
    data.nodes.forEach((node) => {
      if (!positions.current.has(node.id)) {
        const { w, h } = getSize();
        positions.current.set(node.id, {
          x: w / 2 + (Math.random() - 0.5) * 200,
          y: h / 2 + (Math.random() - 0.5) * 200,
          vx: 0,
          vy: 0,
        });
      }
    });

    const simulate = () => {
      const { w, h } = getSize();
      const nodes = data.nodes;
      const edges = data.edges;
      const posMap = positions.current;

      // Repulsion between all node pairs
      for (let i = 0; i < nodes.length; i++) {
        const pi = posMap.get(nodes[i].id);
        if (!pi) continue;
        for (let j = i + 1; j < nodes.length; j++) {
          const pj = posMap.get(nodes[j].id);
          if (!pj) continue;
          const dx = pi.x - pj.x;
          const dy = pi.y - pj.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 2000 / (dist * dist);
          pi.vx += (dx / dist) * force;
          pi.vy += (dy / dist) * force;
          pj.vx -= (dx / dist) * force;
          pj.vy -= (dy / dist) * force;
        }
      }

      // Spring attraction along edges
      for (const edge of edges) {
        const ps = posMap.get(edge.source);
        const pt = posMap.get(edge.target);
        if (!ps || !pt) continue;
        const dx = pt.x - ps.x;
        const dy = pt.y - ps.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 120) * 0.01;
        ps.vx += (dx / dist) * force;
        ps.vy += (dy / dist) * force;
        pt.vx -= (dx / dist) * force;
        pt.vy -= (dy / dist) * force;
      }

      // Gravity toward center
      for (const node of nodes) {
        const p = posMap.get(node.id);
        if (!p) continue;
        p.vx += (w / 2 - p.x) * 0.002;
        p.vy += (h / 2 - p.y) * 0.002;
      }

      // Integrate + dampen + clamp to canvas bounds
      for (const node of nodes) {
        const p = posMap.get(node.id);
        if (!p) continue;
        p.vx *= 0.85;
        p.vy *= 0.85;
        p.x = Math.max(20, Math.min(w - 20, p.x + p.vx));
        p.y = Math.max(20, Math.min(h - 20, p.y + p.vy));
      }

      // ── Draw ──────────────────────────────────────────────
      ctx.clearRect(0, 0, w, h);

      // Edges
      for (const edge of edges) {
        const ps = posMap.get(edge.source);
        const pt = posMap.get(edge.target);
        if (!ps || !pt) continue;
        ctx.beginPath();
        ctx.moveTo(ps.x, ps.y);
        ctx.lineTo(pt.x, pt.y);
        ctx.strokeStyle = EDGE_COLORS[edge.rel] ?? EDGE_COLORS.default;
        ctx.lineWidth = edge.rel === "CONTRADICTS" || edge.rel === "CRITIQUES" ? 2 : 1;
        ctx.setLineDash(
          edge.rel === "SIMILAR_TO" || edge.rel === "DISCUSSES" ? [4, 3] : []
        );
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Nodes
      for (const node of nodes) {
        const p = posMap.get(node.id);
        if (!p) continue;
        const r = NODE_RADIUS[node.type] ?? 10;
        const isSelected = selected?.id === node.id;

        ctx.beginPath();
        if (node.type === "concept") {
          ctx.rect(p.x - r, p.y - r, r * 2, r * 2);
        } else {
          ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        }
        ctx.fillStyle = isSelected ? "#1D4ED8" : NODE_COLORS[node.type] ?? "#6B7280";
        ctx.fill();
        ctx.strokeStyle = isSelected ? "#fff" : "#fff";
        ctx.lineWidth = isSelected ? 2.5 : 1.5;
        ctx.stroke();

        // Label
        ctx.fillStyle = "#111827";
        ctx.font = "10px system-ui";
        ctx.textAlign = "center";
        const label = node.label.length > 22 ? node.label.slice(0, 22) + "…" : node.label;
        ctx.fillText(label, p.x, p.y + r + 13);
      }

      animRef.current = requestAnimationFrame(simulate);
    };

    animRef.current = requestAnimationFrame(simulate);
    return () => cancelAnimationFrame(animRef.current);
  }, [data, selected]);

  // Convert a CSS-space mouse event to canvas-internal coordinates
  const toCanvasCoords = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { mx: 0, my: 0 };
    const rect = canvas.getBoundingClientRect();
    // Since canvas.width now equals rect.width (set by ResizeObserver), scale = 1
    // but keep the formula correct for any edge case
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      mx: (e.clientX - rect.left) * scaleX,
      my: (e.clientY - rect.top) * scaleY,
    };
  }, []);

  const hitTest = useCallback(
    (mx: number, my: number): GraphNode | null => {
      for (const node of data.nodes) {
        const p = positions.current.get(node.id);
        if (!p) continue;
        const r = (NODE_RADIUS[node.type] ?? 10) + 6; // +6px tolerance
        const dx = mx - p.x;
        const dy = my - p.y;
        if (dx * dx + dy * dy <= r * r) return node;
      }
      return null;
    },
    [data.nodes]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const { mx, my } = toCanvasCoords(e);
      const hit = hitTest(mx, my);
      if (hit) {
        setSelected(hit);
        onNodeClick?.(hit);
      } else {
        setSelected(null);
        setTooltip(null);
      }
    },
    [toCanvasCoords, hitTest, onNodeClick]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const { mx, my } = toCanvasCoords(e);
      const hit = hitTest(mx, my);
      if (hit) {
        setTooltip({ x: e.clientX, y: e.clientY, node: hit });
      } else {
        setTooltip(null);
      }
    },
    [toCanvasCoords, hitTest]
  );

  return (
    <div ref={containerRef} className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-pointer"
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
      />

      {/* Legend */}
      <div className="absolute top-3 left-3 bg-white/90 border border-gray-200 rounded-lg p-2 text-xs space-y-1 pointer-events-none">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full inline-block bg-blue-500" /> Paper
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 inline-block bg-amber-400" /> Concept
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full inline-block bg-purple-500" /> Cluster
        </div>
        <div className="flex items-center gap-2">
          <span className="w-5 h-0.5 inline-block bg-red-500" /> Contradicts
        </div>
      </div>

      {/* Tooltip — follows the real mouse position */}
      {tooltip && (
        <div
          className="fixed z-50 bg-white border border-gray-200 shadow-lg rounded-lg p-2 text-xs max-w-xs pointer-events-none"
          style={{ left: tooltip.x + 14, top: tooltip.y - 10 }}
        >
          <p className="font-semibold text-gray-800">{tooltip.node.label}</p>
          <p className="text-gray-500 capitalize">{tooltip.node.type}</p>
          {tooltip.node.year && <p className="text-gray-400">{tooltip.node.year}</p>}
          {(tooltip.node.paper_count ?? 0) > 0 && (
            <p className="text-gray-400">{tooltip.node.paper_count} papers</p>
          )}
          {(tooltip.node.pagerank_score ?? 0) > 0 && (
            <p className="text-gray-400">
              Importance: {((tooltip.node.pagerank_score ?? 0) * 100).toFixed(1)}%
            </p>
          )}
        </div>
      )}
    </div>
  );
}
