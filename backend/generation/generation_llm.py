from __future__ import annotations
import json
import re

import litellm

from backend.models import MemoryClue, CitedAnswer, Citation
from backend.generation.context_assembler import assemble_context, SYSTEM_PROMPT, DRAFT_OUTLINE_PROMPT
from backend.config import GENERATION_LLM_MODEL, MEMORY_LLM_MODEL


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.strip().rstrip("`").strip()
    return json.loads(text)


def _validate_citation_against_chunks(citation: dict, chunks: list[dict]) -> dict:
    """
    Cross-check citation fields against the actual retrieved chunks.
    Clears page/quote fields that don't match any chunk to prevent hallucinated specifics.
    """
    ref_id = citation.get("ref_id", 0)
    # Find the chunk this citation claims to reference (by 1-based ref_id index)
    chunk_idx = ref_id - 1
    if 0 <= chunk_idx < len(chunks):
        chunk = chunks[chunk_idx]
        # Validate quote: if claimed quote isn't a substring of the chunk content, clear it
        quote = citation.get("quote", "")
        content = chunk.get("content", "")
        if quote and quote.lower() not in content.lower():
            citation["quote"] = ""
        # Validate page: use the chunk's actual page rather than trusting the model
        actual_page = chunk.get("page_start", chunk.get("page", 0))
        if actual_page:
            citation["page"] = actual_page
    return citation


class GenerationLLM:
    def __init__(self, model: str = GENERATION_LLM_MODEL):
        self.model = model

    def generate_answer(
        self,
        query: str,
        clue: MemoryClue,
        chunks: list[dict],
        draft_mode: bool = False,
    ) -> CitedAnswer:
        context = assemble_context(query, clue, chunks, draft_mode)

        response = litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        try:
            data = _extract_json(raw)
        except Exception:
            return CitedAnswer(
                answer=raw,
                citations=[],
                memory_trace=[],
            )

        citations: list[Citation] = []
        for c in data.get("citations", []):
            c = _validate_citation_against_chunks(c, chunks)
            citations.append(Citation(
                ref_id=c.get("ref_id", 0),
                paper=c.get("paper", ""),
                section=c.get("section", ""),
                page=c.get("page", 0),
                quote=c.get("quote", ""),
                deep_link="",  # assembled later
            ))

        return CitedAnswer(
            answer=data.get("answer", raw),
            citations=citations,
            memory_trace=data.get("memory_trace", []),
        )

    def generate_draft_outline(self, query: str, clue: MemoryClue) -> dict:
        prompt = DRAFT_OUTLINE_PROMPT.format(
            clue_text=clue.text,
            query=query,
        )
        response = litellm.completion(
            model=MEMORY_LLM_MODEL,  # outline generation is lighter
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return _extract_json(raw)
        except Exception:
            return {"sections": []}
