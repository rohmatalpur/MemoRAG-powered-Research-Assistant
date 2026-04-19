"use client";
import { useState, useRef, useEffect } from "react";
import type { ChatResponse } from "@/lib/types";
import { sendChat, sendDraft } from "@/lib/api";
import CitationPanel from "./CitationPanel";

interface Message {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

const STORAGE_KEY = "research_chat_history";

function loadMessages(): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMessages(msgs: Message[]) {
  try {
    // Strip embeddings/heavy data before saving — keep last 50 messages
    const toSave = msgs.slice(-50);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  } catch {
    // localStorage full — silently ignore
  }
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [draftMode, setDraftMode] = useState(false);
  const [expandedMsg, setExpandedMsg] = useState<number | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load from localStorage once on mount
  useEffect(() => {
    setMessages(loadMessages());
    setHydrated(true);
  }, []);

  // Persist on every change
  useEffect(() => {
    if (hydrated) saveMessages(messages);
  }, [messages, hydrated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Cancel in-flight request on unmount
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const send = async () => {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");

    const userMsg: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const res = draftMode ? await sendDraft(query) : await sendChat(query, draftMode);
      const assistantMsg: Message = {
        role: "assistant",
        content: res.answer,
        response: res,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      if (err.name === "AbortError") return;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const clearHistory = () => {
    if (!confirm("Clear all chat history?")) return;
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h2 className="font-semibold text-gray-800">Research Chat</h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={draftMode}
              onChange={(e) => setDraftMode(e.target.checked)}
              className="rounded"
            />
            Draft mode
          </label>
          {messages.length > 0 && (
            <button
              onClick={clearHistory}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!hydrated ? null : messages.length === 0 ? (
          <div className="text-center text-gray-400 text-sm mt-12">
            <p className="text-2xl mb-2">🔬</p>
            <p>Ask anything about your research library.</p>
            <div className="mt-4 space-y-1.5">
              {[
                "Which papers disagree on sparse attention efficiency?",
                "Summarize the key findings on RLHF from my library",
                "Draft a related work section on transformer efficiency",
              ].map((eg) => (
                <button
                  key={eg}
                  className="block mx-auto text-xs text-blue-500 hover:text-blue-700 hover:underline"
                  onClick={() => setInput(eg)}
                >
                  {eg}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2"
                  : "bg-gray-50 border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap leading-relaxed">
                {msg.content}
              </p>

              {msg.response && (
                <div className="mt-3">
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full mr-2">
                    {msg.response.intent}
                  </span>
                  {msg.response.draft_mode && (
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                      draft
                    </span>
                  )}

                  {msg.response.outline?.sections && (
                    <div className="mt-3 space-y-2">
                      {msg.response.outline.sections.map((sec, si) => (
                        <div key={si} className="bg-white border border-gray-200 rounded-lg p-2">
                          <p className="text-xs font-semibold text-gray-700">{sec.title}</p>
                          <p className="text-xs text-gray-500">{sec.theme}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    className="mt-2 text-xs text-gray-400 hover:text-gray-600"
                    onClick={() => setExpandedMsg(expandedMsg === i ? null : i)}
                  >
                    {expandedMsg === i
                      ? "▲ Hide sources"
                      : `▼ ${msg.response.citations.length} source(s)`}
                  </button>

                  {expandedMsg === i && (
                    <div className="mt-2 border-t border-gray-200 pt-2">
                      <CitationPanel
                        citations={msg.response.citations}
                        memoryTrace={msg.response.memory_trace}
                        clue={msg.response.clue}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-50 border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-100 p-3 flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder={draftMode ? "Describe what to draft…" : "Ask about your library…"}
          rows={2}
          className="flex-1 resize-none rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed self-end"
        >
          Send
        </button>
      </div>
    </div>
  );
}
