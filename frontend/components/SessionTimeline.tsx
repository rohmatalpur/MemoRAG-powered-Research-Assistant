"use client";
import type { Session } from "@/lib/types";

interface Props {
  sessions: Session[];
  onSelectSession?: (session: Session) => void;
  selectedId?: string;
}

export default function SessionTimeline({
  sessions,
  onSelectSession,
  selectedId,
}: Props) {
  if (sessions.length === 0) {
    return (
      <div className="text-center text-gray-400 text-sm py-8">
        No reading sessions yet. Upload a paper to get started.
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200" />

      <div className="space-y-4">
        {sessions.map((session, i) => (
          <div
            key={session.session_id}
            className={`relative pl-12 cursor-pointer group`}
            onClick={() => onSelectSession?.(session)}
          >
            {/* Dot */}
            <div
              className={`absolute left-3.5 top-2 w-3 h-3 rounded-full border-2 transition-colors ${
                selectedId === session.session_id
                  ? "bg-blue-600 border-blue-600"
                  : "bg-white border-gray-300 group-hover:border-blue-400"
              }`}
            />

            <div
              className={`bg-white border rounded-lg p-3 transition-shadow ${
                selectedId === session.session_id
                  ? "border-blue-400 shadow-md"
                  : "border-gray-200 hover:border-gray-300 hover:shadow-sm"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-gray-700">
                  Session {sessions.length - i}
                </span>
                <span className="text-xs text-gray-400">
                  {new Date(session.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </span>
              </div>

              {/* Stats row */}
              <div className="flex gap-3 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
                  {session.paper_count} paper{session.paper_count !== 1 ? "s" : ""}
                </span>
                {session.new_concepts > 0 && (
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 bg-amber-400 inline-block" />
                    +{session.new_concepts} concepts
                  </span>
                )}
                {session.new_edges > 0 && (
                  <span>+{session.new_edges} links</span>
                )}
                {session.new_clusters > 0 && (
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-purple-400 inline-block" />
                    {session.new_clusters} cluster{session.new_clusters !== 1 ? "s" : ""}
                  </span>
                )}
              </div>

              {/* Papers in session */}
              {session.papers && session.papers.length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {session.papers.slice(0, 3).map((p) => (
                    <p
                      key={p.paper_id}
                      className="text-xs text-gray-600 line-clamp-1"
                    >
                      · {p.title}
                    </p>
                  ))}
                  {session.papers.length > 3 && (
                    <p className="text-xs text-gray-400">
                      +{session.papers.length - 3} more
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
