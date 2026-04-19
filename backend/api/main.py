from __future__ import annotations
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.api.routes import papers, chat, graph, sessions
from backend.config import UPLOAD_DIR

app = FastAPI(
    title="Personal Research Assistant",
    description="MemoRAG-powered research assistant with persistent memory, knowledge graphs, and cited answers.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(sessions.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/search")
async def search(q: str, limit: int = 20):
    from backend.session.session_manager import SessionManager
    sm = SessionManager()
    all_papers = sm.list_papers()
    q_lower = q.lower()
    results = [
        p for p in all_papers
        if q_lower in (p.get("title") or "").lower()
        or q_lower in (p.get("authors") or "").lower()
        or any(q_lower in tag.lower() for tag in p.get("concept_tags", []))
    ]
    return results[:limit]


# Serve uploaded papers as static files
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/papers-static", StaticFiles(directory=UPLOAD_DIR), name="papers-static")
