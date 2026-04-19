import type { Paper, Session, GraphData, ChatResponse, Cluster, Annotation } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// Papers
export const getPapers = () => apiFetch<Paper[]>("/api/papers");

export const getPaper = (id: string) => apiFetch<Paper>(`/api/papers/${id}`);

export const deletePaper = (id: string) =>
  apiFetch<{ status: string }>(`/api/papers/${id}`, { method: "DELETE" });

export const uploadPaper = async (
  file?: File,
  url?: string,
  sessionId?: string
): Promise<{ status: string; source: string; session_id: string }> => {
  const form = new FormData();
  if (file) form.append("file", file);
  if (url) form.append("url", url);
  if (sessionId) form.append("session_id", sessionId);

  const res = await fetch(`${BASE_URL}/api/papers/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

export const getAnnotations = (paperId: string) =>
  apiFetch<Annotation[]>(`/api/papers/${paperId}/annotations`);

export const addAnnotation = async (
  paperId: string,
  text: string,
  page: number
) => {
  const form = new FormData();
  form.append("text", text);
  form.append("page", String(page));
  const res = await fetch(`${BASE_URL}/api/papers/${paperId}/annotations`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

// Sessions
export const getSessions = () => apiFetch<Session[]>("/api/sessions");

export const getSession = (id: string) => apiFetch<Session>(`/api/sessions/${id}`);

export const newSession = () =>
  apiFetch<{ session_id: string }>("/api/sessions/new", { method: "POST" });

export const getSessionDelta = (id: string) =>
  apiFetch<Session>(`/api/sessions/${id}/delta`);

// Graph
export const getGraph = () => apiFetch<GraphData>("/api/graph");

export const getClusters = () => apiFetch<Cluster[]>("/api/graph/clusters");

export const redetectClusters = () =>
  apiFetch<{ clusters_found: number; clusters: Cluster[] }>("/api/graph/clusters/redetect", {
    method: "POST",
  });

export const getPaperNeighbors = (paperId: string) =>
  apiFetch<any[]>(`/api/graph/paper/${paperId}/neighbors`);

export const getConceptPapers = (conceptId: string) =>
  apiFetch<Paper[]>(`/api/graph/concepts/${conceptId}/papers`);

// Chat
export const sendChat = (query: string, draftMode = false) =>
  apiFetch<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ query, draft_mode: draftMode }),
  });

export const sendDraft = (query: string) =>
  apiFetch<ChatResponse>("/api/chat/draft", {
    method: "POST",
    body: JSON.stringify({ query, draft_mode: true }),
  });

// Search
export const searchPapers = (q: string) =>
  apiFetch<Paper[]>(`/api/search?q=${encodeURIComponent(q)}`);
