"use client";
import type { Citation, MemoryClue } from "@/lib/types";

interface Props {
  citations: Citation[];
  memoryTrace: string[];
  clue?: MemoryClue;
}

export default function CitationPanel({ citations, memoryTrace, clue }: Props) {
  return (
    <div className="space-y-4">
      {/* Citations */}
      {citations.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Citations
          </h4>
          <ol className="space-y-2">
            {citations.map((c) => (
              <li key={c.ref_id} className="text-xs">
                <span className="font-semibold text-blue-700">[{c.ref_id}]</span>{" "}
                <a
                  href={c.deep_link || "#"}
                  className="font-medium text-gray-800 hover:text-blue-600 underline-offset-2 hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {c.paper}
                </a>
                {c.section && (
                  <span className="text-gray-500"> · {c.section}</span>
                )}
                {c.page > 0 && (
                  <span className="text-gray-500"> · p.{c.page}</span>
                )}
                {c.quote && (
                  <blockquote className="mt-1 pl-2 border-l-2 border-gray-200 text-gray-500 italic line-clamp-2">
                    "{c.quote}"
                  </blockquote>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Memory trace */}
      {memoryTrace.length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Memory Trace ({memoryTrace.length})
          </summary>
          <ul className="mt-1 space-y-0.5 pl-3">
            {memoryTrace.map((t, i) => (
              <li key={i} className="text-gray-500">
                · {t}
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Memory clue */}
      {clue && (
        <details className="text-xs">
          <summary className="cursor-pointer font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Memory Clue (confidence {Math.round((clue.confidence ?? 0) * 100)}%)
          </summary>
          <p className="mt-1 text-gray-600 italic bg-amber-50 p-2 rounded-lg leading-relaxed">
            {clue.text}
          </p>
          {clue.suggested_terms.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {clue.suggested_terms.map((t) => (
                <span
                  key={t}
                  className="bg-gray-100 text-gray-600 rounded px-1.5 py-0.5"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </details>
      )}
    </div>
  );
}
