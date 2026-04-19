from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4


@dataclass
class ChunkRecord:
    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    paper_id: str = ""
    section_type: str = ""       # abstract | introduction | methods | results | ...
    section_heading: str = ""
    content: str = ""
    token_count: int = 0
    page_start: int = 0
    page_end: int = 0
    embedding: Optional[list[float]] = None


@dataclass
class ParsedSection:
    heading: str
    type: str
    content: str
    page_start: int
    page_end: int


@dataclass
class ParsedReference:
    title: str
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    context: str = ""            # sentence(s) from body where this is cited


@dataclass
class ParsedPaper:
    paper_id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    sections: list[ParsedSection] = field(default_factory=list)
    references: list[ParsedReference] = field(default_factory=list)
    source_path: str = ""
    source_type: str = ""        # pdf | docx | url


@dataclass
class PaperMemory:
    paper_id: str
    core_claim: str
    methodology: str
    key_results: list[str]
    limitations: str
    novelty: str
    target_domain: str


@dataclass
class ConceptMemory:
    concept: str
    definition: str
    introduced_here: bool
    related_concepts: list[str] = field(default_factory=list)


@dataclass
class RelationalMemory:
    references: list[dict]       # [{ref_title, rel_type, reason}]


@dataclass
class MemoryClue:
    text: str
    mentioned_papers: list[str] = field(default_factory=list)
    suggested_terms: list[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class Citation:
    ref_id: int
    paper: str
    section: str
    page: int
    quote: str
    deep_link: str = ""


@dataclass
class CitedAnswer:
    answer: str
    citations: list[Citation]
    memory_trace: list[str]


@dataclass
class SessionDelta:
    session_id: str
    papers_added: int
    new_concepts: int
    new_edges: int
    new_clusters: int
    new_cross_links: int
