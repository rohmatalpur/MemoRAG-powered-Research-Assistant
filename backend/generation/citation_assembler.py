from __future__ import annotations
from backend.models import Citation
from backend.session.session_manager import SessionManager


def assemble_citations(
    citations: list[Citation],
    session_manager: SessionManager,
) -> list[Citation]:
    """Attach deep links to citations by looking up paper metadata."""
    assembled: list[Citation] = []
    for c in citations:
        paper_id = _find_paper_id_by_title(c.paper, session_manager)
        deep_link = f"/papers/{paper_id}?page={c.page}" if paper_id else ""
        assembled.append(Citation(
            ref_id=c.ref_id,
            paper=c.paper,
            section=c.section,
            page=c.page,
            quote=c.quote,
            deep_link=deep_link,
        ))
    return assembled


def _find_paper_id_by_title(title: str, session_manager: SessionManager) -> str | None:
    if not title:
        return None
    papers = session_manager.list_papers()
    title_lower = title.lower().strip()
    for p in papers:
        stored_title = (p.get("title") or "").lower().strip()
        if stored_title and _overlap(title_lower, stored_title) > 0.5:
            return p["paper_id"]
    return None


def _overlap(a: str, b: str) -> float:
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))
