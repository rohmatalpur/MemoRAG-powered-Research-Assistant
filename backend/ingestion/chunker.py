from __future__ import annotations
from uuid import uuid4

from backend.models import ChunkRecord, ParsedSection
from backend.config import MAX_CHUNK_TOKENS, OVERLAP_TOKENS


def _get_tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained("bert-base-uncased")  # fast, no remote calls needed


_tokenizer = None


def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = _get_tokenizer()
    return _tokenizer


def _count_tokens(text: str) -> int:
    tok = get_tokenizer()
    return len(tok.encode(text, add_special_tokens=False))


def _encode(text: str) -> list[int]:
    tok = get_tokenizer()
    return tok.encode(text, add_special_tokens=False)


def chunk_section(
    paper_id: str,
    section: ParsedSection,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap: int = OVERLAP_TOKENS,
) -> list[ChunkRecord]:
    content = section.content.strip()
    if not content:
        return []

    token_count = _count_tokens(content)

    if token_count <= max_tokens:
        return [ChunkRecord(
            chunk_id=str(uuid4()),
            paper_id=paper_id,
            section_type=section.type,
            section_heading=section.heading,
            content=content,
            token_count=token_count,
            page_start=section.page_start,
            page_end=section.page_end,
        )]

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    chunks: list[ChunkRecord] = []
    current_paras: list[str] = []
    current_token_count = 0

    for para in paragraphs:
        para_tokens = _count_tokens(para)

        if current_token_count + para_tokens > max_tokens and current_paras:
            chunk_text = "\n\n".join(current_paras)
            chunks.append(ChunkRecord(
                chunk_id=str(uuid4()),
                paper_id=paper_id,
                section_type=section.type,
                section_heading=section.heading,
                content=chunk_text,
                token_count=_count_tokens(chunk_text),
                page_start=section.page_start,
                page_end=section.page_end,
            ))
            # Keep overlap: last few paragraphs that fit within overlap budget
            overlap_paras = _get_overlap_paras(current_paras, overlap)
            current_paras = overlap_paras + [para]
            current_token_count = _count_tokens("\n\n".join(current_paras))
        else:
            current_paras.append(para)
            current_token_count += para_tokens

    if current_paras:
        chunk_text = "\n\n".join(current_paras)
        chunks.append(ChunkRecord(
            chunk_id=str(uuid4()),
            paper_id=paper_id,
            section_type=section.type,
            section_heading=section.heading,
            content=chunk_text,
            token_count=_count_tokens(chunk_text),
            page_start=section.page_start,
            page_end=section.page_end,
        ))

    return chunks


def _get_overlap_paras(paras: list[str], overlap_budget: int) -> list[str]:
    kept: list[str] = []
    token_sum = 0
    for para in reversed(paras):
        t = _count_tokens(para)
        if token_sum + t > overlap_budget:
            break
        kept.insert(0, para)
        token_sum += t
    return kept


def chunk_paper(paper_id: str, sections: list[ParsedSection]) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for section in sections:
        if section.type == "references":
            continue
        chunks.extend(chunk_section(paper_id, section))
    return chunks
