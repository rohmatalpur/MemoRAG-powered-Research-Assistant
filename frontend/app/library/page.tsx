"use client";
import { useState, useEffect, useCallback } from "react";
import type { Paper } from "@/lib/types";
import { getPapers, uploadPaper, searchPapers } from "@/lib/api";
import PaperCard from "@/components/PaperCard";

export default function LibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [filter, setFilter] = useState<"all" | "indexed" | "processing">("all");
  const [dragOver, setDragOver] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getPapers();
      setPapers(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000); // poll for processing updates
    return () => clearInterval(interval);
  }, [load]);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadPaper(file);
      }
      await load();
    } catch (e: any) {
      alert(`Upload failed: ${e.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleUrlUpload = async () => {
    const url = urlInput.trim();
    if (!url) return;
    setUploading(true);
    try {
      await uploadPaper(undefined, url);
      setUrlInput("");
      await load();
    } catch (e: any) {
      alert(`Upload failed: ${e.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async (q: string) => {
    setSearch(q);
    if (!q.trim()) {
      await load();
      return;
    }
    try {
      const results = await searchPapers(q);
      setPapers(results);
    } catch (e) {
      console.error(e);
    }
  };

  const filtered = papers.filter(
    (p) => filter === "all" || p.status === filter
  );

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 mb-6">
        <div className="flex items-center gap-3">
          {/* Search */}
          <input
            type="text"
            placeholder="Search by title, author, or concept…"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />

          {/* Filter */}
          <div className="flex border border-gray-200 rounded-lg overflow-hidden text-sm">
            {(["all", "indexed", "processing"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-2 capitalize transition-colors ${
                  filter === f
                    ? "bg-blue-600 text-white"
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Upload row */}
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Paste URL (arXiv, blog, preprint)…"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleUrlUpload()}
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            onClick={handleUrlUpload}
            disabled={uploading || !urlInput.trim()}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-40"
          >
            Add URL
          </button>
          <label className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 cursor-pointer">
            {uploading ? "Uploading…" : "Upload PDF"}
            <input
              type="file"
              accept=".pdf,.docx"
              multiple
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />
          </label>
        </div>
      </div>

      {/* Drop zone indicator */}
      <div
        className={`relative flex-1 ${
          dragOver ? "ring-2 ring-blue-400 rounded-xl" : ""
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFileUpload(e.dataTransfer.files);
        }}
      >
        {loading ? (
          <div className="flex items-center justify-center h-48 text-gray-400">
            Loading library…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-400 text-sm">
            <p className="text-4xl mb-3">📚</p>
            <p>
              {search
                ? "No papers match your search."
                : "No papers yet. Upload a PDF or paste a URL above."}
            </p>
            <p className="text-xs mt-1 text-gray-300">
              You can also drag & drop PDFs here
            </p>
          </div>
        ) : (
          <>
            <p className="text-xs text-gray-400 mb-3">
              {filtered.length} paper{filtered.length !== 1 ? "s" : ""}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filtered.map((paper) => (
                <PaperCard
                  key={paper.paper_id}
                  paper={paper}
                  onDelete={(id) =>
                    setPapers((prev) => prev.filter((p) => p.paper_id !== id))
                  }
                  onClick={setSelectedPaper}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Paper detail panel */}
      {selectedPaper && (
        <div className="fixed inset-y-0 right-0 w-96 bg-white border-l border-gray-200 shadow-xl z-50 overflow-y-auto p-6">
          <button
            onClick={() => setSelectedPaper(null)}
            className="mb-4 text-gray-400 hover:text-gray-600 text-sm"
          >
            ✕ Close
          </button>
          <h2 className="text-lg font-semibold text-gray-900 mb-1">
            {selectedPaper.title}
          </h2>
          <p className="text-sm text-gray-500 mb-2">{selectedPaper.authors}</p>
          {selectedPaper.year && (
            <p className="text-sm text-gray-400 mb-3">{selectedPaper.year}</p>
          )}

          {selectedPaper.memory_digest && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">
                Memory Digest
              </p>
              <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded-lg">
                {selectedPaper.memory_digest}
              </p>
            </div>
          )}

          {selectedPaper.concept_tags?.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">
                Concepts
              </p>
              <div className="flex flex-wrap gap-1">
                {selectedPaper.concept_tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="mb-2">
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                selectedPaper.status === "indexed"
                  ? "bg-green-100 text-green-800"
                  : selectedPaper.status === "processing"
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-red-100 text-red-800"
              }`}
            >
              {selectedPaper.status}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
