from __future__ import annotations
from fastapi import APIRouter, HTTPException

from backend.session.session_manager import SessionManager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_session_manager: SessionManager | None = None


def get_sm() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


@router.get("")
async def list_sessions():
    return get_sm().list_sessions()


@router.post("/new")
async def new_session():
    sid = get_sm().create_session()
    return {"session_id": sid}


@router.get("/{session_id}")
async def get_session(session_id: str):
    sm = get_sm()
    sessions = sm.list_sessions()
    session = next((s for s in sessions if s["session_id"] == session_id), None)
    if not session:
        raise HTTPException(404, "Session not found")
    papers = sm.get_session_papers(session_id)
    return {**session, "papers": papers}


@router.get("/{session_id}/delta")
async def get_session_delta(session_id: str):
    sm = get_sm()
    sessions = sm.list_sessions()
    session = next((s for s in sessions if s["session_id"] == session_id), None)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "session_id": session_id,
        "new_concepts": session["new_concepts"],
        "new_edges": session["new_edges"],
        "new_clusters": session["new_clusters"],
        "papers": sm.get_session_papers(session_id),
    }
