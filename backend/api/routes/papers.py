from __future__ import annotations
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from backend.config import UPLOAD_DIR
from backend.session.session_manager import SessionManager
from backend.graph.graph_store import load_graph, save_graph
from backend.retrieval.vector_store import delete_paper_vectors, get_qdrant_client

router = APIRouter(prefix="/api/papers", tags=["papers"])

_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def _run_ingestion(source: str, session_id: str) -> None:
    from qdrant_client import QdrantClient
    from backend.ingestion.pipeline import IngestionPipeline
    from backend.config import QDRANT_HOST, QDRANT_PORT

    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    graph = load_graph()
    sm = get_session_manager()
    pipeline = IngestionPipeline(sm, qdrant, graph)
    pipeline.ingest(source, session_id)


@router.post("/upload")
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
    session_id: str | None = Form(None),
):
    sm = get_session_manager()
    if session_id is None:
        session_id = sm.get_or_create_active_session()

    if file is not None:
        # Save file to disk
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        dest = Path(UPLOAD_DIR) / file.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        source = str(dest)
    elif url:
        source = url
    else:
        raise HTTPException(400, "Provide a file or URL")

    background_tasks.add_task(_run_ingestion, source, session_id)
    return {"status": "processing", "source": source, "session_id": session_id}


@router.get("")
async def list_papers():
    sm = get_session_manager()
    return sm.list_papers()


@router.get("/{paper_id}")
async def get_paper(paper_id: str):
    sm = get_session_manager()
    paper = sm.get_paper(paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")

    graph = load_graph()
    memory_digest = ""
    if paper_id in graph:
        memory_digest = graph.nodes[paper_id].get("memory_digest", "")

    return {**paper, "memory_digest": memory_digest}


@router.delete("/{paper_id}")
async def delete_paper(paper_id: str):
    sm = get_session_manager()
    paper = sm.get_paper(paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")

    # Remove from vector store
    qdrant = get_qdrant_client()
    delete_paper_vectors(qdrant, paper_id)

    # Remove from graph
    graph = load_graph()
    if paper_id in graph:
        graph.remove_node(paper_id)
        save_graph(graph)

    # Remove from SQLite
    sm.delete_paper(paper_id)

    return {"status": "deleted", "paper_id": paper_id}


@router.post("/{paper_id}/annotations")
async def add_annotation(paper_id: str, text: str = Form(...), page: int = Form(0)):
    sm = get_session_manager()
    sm.add_annotation(paper_id, text, page)
    return {"status": "ok"}


@router.get("/{paper_id}/annotations")
async def get_annotations(paper_id: str):
    sm = get_session_manager()
    return sm.get_annotations(paper_id)
