from __future__ import annotations
from pydantic import BaseModel

from fastapi import APIRouter

from backend.graph.graph_store import load_graph
from backend.retrieval.retriever import retrieve_and_rerank, compress_global_memory
from backend.retrieval.vector_store import get_qdrant_client
from backend.generation.generation_llm import GenerationLLM
from backend.generation.citation_assembler import assemble_citations
from backend.memory.memory_llm import MemoryLLM
from backend.session.session_manager import SessionManager
from backend.embeddings import embed

router = APIRouter(prefix="/api/chat", tags=["chat"])

_memory_llm: MemoryLLM | None = None
_generation_llm: GenerationLLM | None = None
_session_manager: SessionManager | None = None


def get_deps():
    global _memory_llm, _generation_llm, _session_manager
    if _memory_llm is None:
        _memory_llm = MemoryLLM()
    if _generation_llm is None:
        _generation_llm = GenerationLLM()
    if _session_manager is None:
        _session_manager = SessionManager()
    return _memory_llm, _generation_llm, _session_manager


class ChatRequest(BaseModel):
    query: str
    draft_mode: bool = False


@router.post("")
async def chat(req: ChatRequest):
    memory_llm, generation_llm, session_manager = get_deps()
    qdrant = get_qdrant_client()
    graph = load_graph()

    # Step 1: Classify query
    intent, auto_draft = memory_llm.classify_query(req.query)
    draft_mode = req.draft_mode or auto_draft

    # Step 2: Compress global memory
    memory_block, cluster_summary = compress_global_memory(req.query, qdrant, graph, embed)

    # Step 3: Generate memory clue
    clue = memory_llm.generate_clue(req.query, memory_block, cluster_summary)

    # Step 4 + 5: Retrieve and rerank
    top_chunks = retrieve_and_rerank(req.query, clue, qdrant, graph, embed)

    # Step 6: Draft outline (if draft mode)
    outline = None
    if draft_mode:
        outline = generation_llm.generate_draft_outline(req.query, clue)

    # Step 7: Generate cited answer
    cited_answer = generation_llm.generate_answer(req.query, clue, top_chunks, draft_mode)

    # Step 8: Assemble citations with deep links
    cited_answer.citations = assemble_citations(cited_answer.citations, session_manager)

    return {
        "intent": intent,
        "draft_mode": draft_mode,
        "clue": {
            "text": clue.text,
            "mentioned_papers": clue.mentioned_papers,
            "suggested_terms": clue.suggested_terms,
            "confidence": clue.confidence,
        },
        "answer": cited_answer.answer,
        "citations": [
            {
                "ref_id": c.ref_id,
                "paper": c.paper,
                "section": c.section,
                "page": c.page,
                "quote": c.quote,
                "deep_link": c.deep_link,
            }
            for c in cited_answer.citations
        ],
        "memory_trace": cited_answer.memory_trace,
        "outline": outline,
    }


@router.post("/draft")
async def chat_draft(req: ChatRequest):
    req.draft_mode = True
    return await chat(req)
