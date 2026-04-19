from __future__ import annotations
import json
import re
from typing import Any

import litellm

from backend.models import PaperMemory, ConceptMemory, RelationalMemory, MemoryClue, ParsedSection, ParsedReference
from backend.memory.prompts import (
    PAPER_MEMORY_PROMPT,
    CONCEPT_MEMORY_PROMPT,
    RELATIONAL_MEMORY_PROMPT,
    CLUE_GENERATION_PROMPT,
    CONTRADICT_DETECTION_PROMPT,
    CLUSTER_NAMING_PROMPT,
    QUERY_CLASSIFY_PROMPT,
)
from backend.config import MEMORY_LLM_MODEL


MAX_SECTIONS_TOKENS = 6000  # rough character limit for sections text


def _sections_to_text(sections: list[ParsedSection], limit: int = MAX_SECTIONS_TOKENS) -> str:
    parts: list[str] = []
    total = 0
    for s in sections:
        block = f"[{s.heading}]\n{s.content}"
        if total + len(block) > limit:
            block = block[: limit - total]
            parts.append(block)
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts)


def _call_llm(prompt: str, model: str = MEMORY_LLM_MODEL) -> str:
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


def _extract_json(text: str) -> Any:
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.strip().rstrip("`").strip()
    return json.loads(text)


class MemoryLLM:
    def __init__(self, model: str = MEMORY_LLM_MODEL):
        self.model = model

    def extract_paper_memory(
        self,
        paper_id: str,
        title: str,
        year: int | None,
        authors: list[str],
        sections: list[ParsedSection],
    ) -> PaperMemory:
        prompt = PAPER_MEMORY_PROMPT.format(
            title=title,
            year=year or "unknown",
            authors=", ".join(authors) if authors else "Unknown",
            sections_text=_sections_to_text(sections),
        )
        raw = _call_llm(prompt, self.model)
        try:
            data = _extract_json(raw)
        except Exception:
            data = {}

        return PaperMemory(
            paper_id=paper_id,
            core_claim=data.get("core_claim", ""),
            methodology=data.get("methodology", ""),
            key_results=data.get("key_results", []),
            limitations=data.get("limitations", ""),
            novelty=data.get("novelty", ""),
            target_domain=data.get("target_domain", ""),
        )

    def extract_concept_memories(self, sections: list[ParsedSection]) -> list[ConceptMemory]:
        prompt = CONCEPT_MEMORY_PROMPT.format(
            sections_text=_sections_to_text(sections, limit=8000),
        )
        raw = _call_llm(prompt, self.model)
        try:
            data = _extract_json(raw)
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []

        concepts: list[ConceptMemory] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            concepts.append(ConceptMemory(
                concept=item.get("name", ""),
                definition=item.get("definition", ""),
                introduced_here=bool(item.get("introduced_here", False)),
                related_concepts=item.get("related_concepts", []),
            ))
        return [c for c in concepts if c.concept]

    def extract_relational_memory(
        self,
        paper_title: str,
        references: list[ParsedReference],
    ) -> RelationalMemory:
        if not references:
            return RelationalMemory(references=[])

        refs_text_parts: list[str] = []
        for ref in references[:40]:  # cap to avoid context overflow
            authors_str = ", ".join(ref.authors[:3]) if ref.authors else "Unknown"
            year_str = str(ref.year) if ref.year else "n.d."
            context_str = f" [cited as: {ref.context[:200]}]" if ref.context else ""
            refs_text_parts.append(f"- {ref.title} ({authors_str}, {year_str}){context_str}")

        prompt = RELATIONAL_MEMORY_PROMPT.format(
            paper_title=paper_title,
            references_with_context="\n".join(refs_text_parts),
        )
        raw = _call_llm(prompt, self.model)
        try:
            data = _extract_json(raw)
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []

        return RelationalMemory(references=data)

    def generate_clue(
        self,
        user_query: str,
        compressed_memory_block: str,
        concept_cluster_summary: str,
    ) -> MemoryClue:
        prompt = CLUE_GENERATION_PROMPT.format(
            user_query=user_query,
            compressed_memory_block=compressed_memory_block,
            concept_cluster_summary=concept_cluster_summary,
        )
        raw = _call_llm(prompt, self.model)
        try:
            data = _extract_json(raw)
        except Exception:
            return MemoryClue(text=raw, mentioned_papers=[], suggested_terms=[], confidence=0.5)

        return MemoryClue(
            text=data.get("clue_text", raw),
            mentioned_papers=data.get("mentioned_papers", []),
            suggested_terms=data.get("suggested_terms", []),
            confidence=float(data.get("confidence", 0.8)),
        )

    def detect_contradiction(
        self,
        concept: str,
        paper_a_title: str,
        claim_a: str,
        paper_b_title: str,
        claim_b: str,
    ) -> tuple[bool, str]:
        prompt = CONTRADICT_DETECTION_PROMPT.format(
            concept=concept,
            paper_a_title=paper_a_title,
            claim_a=claim_a,
            paper_b_title=paper_b_title,
            claim_b=claim_b,
        )
        raw = _call_llm(prompt, self.model)
        try:
            data = _extract_json(raw)
            return bool(data.get("contradicts", False)), data.get("reason", "")
        except Exception:
            return False, ""

    def name_cluster(self, paper_titles: list[str]) -> str:
        prompt = CLUSTER_NAMING_PROMPT.format(
            paper_titles="\n".join(f"- {t}" for t in paper_titles[:20]),
        )
        raw = _call_llm(prompt, self.model)
        try:
            data = _extract_json(raw)
            return data.get("label", "Research Cluster")
        except Exception:
            return "Research Cluster"

    def classify_query(self, query: str) -> tuple[str, bool]:
        prompt = QUERY_CLASSIFY_PROMPT.format(query=query)
        raw = _call_llm(prompt, self.model)
        try:
            data = _extract_json(raw)
            return data.get("intent", "factual_lookup"), bool(data.get("draft_mode", False))
        except Exception:
            return "factual_lookup", False
