"use client";
import { useState } from "react";
import type { Paper } from "@/lib/types";
import { deletePaper } from "@/lib/api";

interface Props {
  paper: Paper;
  onDelete?: (id: string) => void;
  onClick?: (paper: Paper) => void;
}

const statusColors: Record<string, string> = {
  processing: "bg-yellow-100 text-yellow-800",
  indexed: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
};

export default function PaperCard({ paper, onDelete, onClick }: Props) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Delete "${paper.title}"?`)) return;
    setDeleting(true);
    try {
      await deletePaper(paper.paper_id);
      onDelete?.(paper.paper_id);
    } finally {
      setDeleting(false);
    }
  };

  const authorList = paper.authors || "";
  const displayAuthors =
    authorList.length > 60 ? authorList.slice(0, 60) + "…" : authorList;

  return (
    <div
      className="group relative bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-400 hover:shadow-md transition-all cursor-pointer"
      onClick={() => onClick?.(paper)}
    >
      {/* Status badge */}
      <span
        className={`absolute top-3 right-3 text-xs px-2 py-0.5 rounded-full font-medium ${
          statusColors[paper.status] ?? "bg-gray-100 text-gray-600"
        }`}
      >
        {paper.status}
      </span>

      {/* Title */}
      <h3 className="text-sm font-semibold text-gray-900 leading-snug pr-20 mb-1 line-clamp-2">
        {paper.title || "Untitled"}
      </h3>

      {/* Authors + year */}
      <p className="text-xs text-gray-500 mb-2">
        {displayAuthors}
        {paper.year ? ` · ${paper.year}` : ""}
      </p>

      {/* Concept tags */}
      {paper.concept_tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {paper.concept_tags.slice(0, 5).map((tag) => (
            <span
              key={tag}
              className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full"
            >
              {tag}
            </span>
          ))}
          {paper.concept_tags.length > 5 && (
            <span className="text-xs text-gray-400">
              +{paper.concept_tags.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Memory digest */}
      {paper.memory_digest && (
        <p className="text-xs text-gray-500 italic line-clamp-2">
          {paper.memory_digest}
        </p>
      )}

      {/* Delete button */}
      <button
        onClick={handleDelete}
        disabled={deleting}
        className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 text-xs text-red-400 hover:text-red-600 transition-opacity"
      >
        {deleting ? "…" : "✕"}
      </button>
    </div>
  );
}
