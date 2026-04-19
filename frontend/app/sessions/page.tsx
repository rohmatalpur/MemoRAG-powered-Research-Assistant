"use client";
import { useEffect, useState } from "react";
import type { Session } from "@/lib/types";
import { getSessions, getSession, newSession } from "@/lib/api";
import SessionTimeline from "@/components/SessionTimeline";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await getSessions();
        setSessions(data);
        if (data.length > 0 && !selectedSession) {
          const detail = await getSession(data[0].session_id);
          setSelectedSession(detail);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleSelectSession = async (session: Session) => {
    try {
      const detail = await getSession(session.session_id);
      setSelectedSession(detail);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNewSession = async () => {
    setCreating(true);
    try {
      const { session_id } = await newSession();
      const data = await getSessions();
      setSessions(data);
      alert(`New session created: ${session_id.slice(0, 8)}…`);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="h-full flex gap-6">
      {/* Timeline sidebar */}
      <div className="w-80 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Reading Sessions</h2>
          <button
            onClick={handleNewSession}
            disabled={creating}
            className="text-xs px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40"
          >
            {creating ? "…" : "+ New"}
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <SessionTimeline
              sessions={sessions}
              selectedId={selectedSession?.session_id}
              onSelectSession={handleSelectSession}
            />
          </div>
        )}
      </div>

      {/* Session detail */}
      <div className="flex-1 bg-white border border-gray-200 rounded-xl p-6 overflow-y-auto">
        {selectedSession ? (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Session Detail
              </h2>
              <span className="text-xs text-gray-400">
                {new Date(selectedSession.created_at).toLocaleString()}
              </span>
            </div>

            {/* Delta stats */}
            <div className="grid grid-cols-4 gap-3 mb-6">
              {[
                { label: "Papers", value: selectedSession.paper_count, color: "blue" },
                { label: "New Concepts", value: selectedSession.new_concepts, color: "amber" },
                { label: "New Links", value: selectedSession.new_edges, color: "gray" },
                { label: "New Clusters", value: selectedSession.new_clusters, color: "purple" },
              ].map((s) => (
                <div
                  key={s.label}
                  className="bg-gray-50 border border-gray-100 rounded-xl p-3 text-center"
                >
                  <p
                    className={`text-2xl font-bold ${
                      s.color === "blue"
                        ? "text-blue-600"
                        : s.color === "amber"
                        ? "text-amber-500"
                        : s.color === "purple"
                        ? "text-purple-600"
                        : "text-gray-700"
                    }`}
                  >
                    {s.value ?? 0}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>

            {/* Papers in session */}
            {selectedSession.papers && selectedSession.papers.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  Papers Added
                </h3>
                <div className="space-y-2">
                  {selectedSession.papers.map((p) => (
                    <div
                      key={p.paper_id}
                      className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">
                          {p.title}
                        </p>
                        <p className="text-xs text-gray-500">{p.authors}</p>
                        {p.concept_tags?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {p.concept_tags.slice(0, 4).map((t) => (
                              <span
                                key={t}
                                className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded-full"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${
                          p.status === "indexed"
                            ? "bg-green-100 text-green-700"
                            : p.status === "processing"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {p.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Select a session to view details
          </div>
        )}
      </div>
    </div>
  );
}
