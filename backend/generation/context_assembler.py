from __future__ import annotations
from backend.models import MemoryClue


def assemble_context(
    query: str,
    clue: MemoryClue,
    chunks: list[dict],
    draft_mode: bool = False,
) -> str:
    chunk_blocks: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("paper_title", chunk.get("title", "Unknown"))
        section = chunk.get("section_heading", chunk.get("section", ""))
        page = chunk.get("page_start", chunk.get("page", 0))
        content = chunk.get("content", "")
        block = f"[{i}] {title} | {section} | p.{page}\n{content}"
        chunk_blocks.append(block)

    context = f"""[MEMORY CLUE — from your reading history]
{clue.text}

[RETRIEVED CONTEXT]
{"---".join(chunk_blocks)}

[QUERY]
{query}

{"[DRAFT MODE: Generate a full academic section with subheadings and clear structure]" if draft_mode else ""}

Respond in JSON:
{{
  "answer": "...",
  "citations": [
    {{"ref_id": 1, "paper": "...", "section": "...", "page": 0, "quote": "..."}}
  ],
  "memory_trace": ["session N: paper title", ...]
}}"""
    return context


SYSTEM_PROMPT = """You are a research assistant helping a researcher synthesize their reading library.
Use ONLY the provided context and memory clue to answer. Do not fabricate information.
Every factual claim must be cited using the format [Author et al. YEAR, §Section, p.N].
Respond in valid JSON with keys: answer, citations, memory_trace."""


DRAFT_OUTLINE_PROMPT = """You are a research assistant. Based on the researcher's reading memory and query, generate a structured outline for a literature review section.

MEMORY CLUE:
{clue_text}

REQUEST: {query}

Return JSON:
{{
  "sections": [
    {{
      "title": "Section title",
      "theme": "brief description",
      "papers": ["paper_id_1", "paper_id_2"],
      "sub_points": ["key claim", "tension between papers"]
    }}
  ]
}}"""
