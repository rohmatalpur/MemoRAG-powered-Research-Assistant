from __future__ import annotations
import os
from pathlib import Path

import networkx as nx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.models import ParsedPaper, ChunkRecord
from backend.ingestion.parser import PaperParser
from backend.ingestion.chunker import chunk_paper
from backend.memory.memory_llm import MemoryLLM
from backend.graph.graph_updater import update_graph_for_paper
from backend.graph.graph_store import save_graph, recompute_pagerank
from backend.retrieval.vector_store import (
    upsert_chunk, upsert_paper_memory, upsert_paper_vec, ensure_collections
)
from backend.session.session_manager import SessionManager
from backend.embeddings import embed, embed_batch, average_embeddings
from backend.config import UPLOAD_DIR


class IngestionPipeline:
    def __init__(
        self,
        session_manager: SessionManager,
        qdrant: QdrantClient,
        graph: nx.MultiDiGraph,
        memory_llm: MemoryLLM | None = None,
    ):
        self.session_manager = session_manager
        self.qdrant = qdrant
        self.graph = graph
        self.memory_llm = memory_llm or MemoryLLM()
        self.parser = PaperParser()
        ensure_collections(self.qdrant)

    def ingest(self, source: str | Path, session_id: str | None = None) -> dict:
        """
        Full ingestion pipeline for a single paper.
        Returns a status dict with paper_id, title, delta.
        """
        # Step 1: Session
        if session_id is None:
            session_id = self.session_manager.get_or_create_active_session()

        # Step 2: Parse
        paper = self.parser.parse(source)
        file_path = str(source) if not str(source).startswith("http") else str(source)

        self.session_manager.insert_paper(
            paper_id=paper.paper_id,
            session_id=session_id,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            file_path=file_path,
            source_type=paper.source_type,
        )

        # Step 3: Chunk
        chunks: list[ChunkRecord] = chunk_paper(paper.paper_id, paper.sections)

        # Step 4: Memory LLM — three memory types
        paper_memory = self.memory_llm.extract_paper_memory(
            paper_id=paper.paper_id,
            title=paper.title,
            year=paper.year,
            authors=paper.authors,
            sections=paper.sections,
        )
        concept_memories = self.memory_llm.extract_concept_memories(paper.sections)
        relational_memory = self.memory_llm.extract_relational_memory(
            paper_title=paper.title,
            references=paper.references,
        )

        # Step 5: Graph update
        existing_paper_ids = {
            n for n, d in self.graph.nodes(data=True)
            if d.get("type") == "paper"
        }
        delta = update_graph_for_paper(
            paper=paper,
            paper_memory=paper_memory,
            concept_memories=concept_memories,
            relational_memory=relational_memory,
            graph=self.graph,
            qdrant=self.qdrant,
            embed_fn=embed,
            memory_llm=self.memory_llm,
            session_id=session_id,
            existing_paper_ids=existing_paper_ids,
        )
        recompute_pagerank(self.graph)
        save_graph(self.graph)

        # Step 6: Vector indexing
        # Embed all chunks in batch
        chunk_texts = [c.content for c in chunks]
        chunk_vectors = embed_batch(chunk_texts) if chunk_texts else []

        for i, chunk in enumerate(chunks):
            vec = chunk_vectors[i] if i < len(chunk_vectors) else [0.0] * 3072
            upsert_chunk(
                self.qdrant,
                chunk_id=chunk.chunk_id,
                vector=vec,
                payload={
                    "paper_id": paper.paper_id,
                    "paper_title": paper.title,
                    "section": chunk.section_heading,
                    "section_heading": chunk.section_heading,
                    "section_type": chunk.section_type,
                    "content": chunk.content,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                },
            )

        # Paper-level memory vector
        memory_text = f"{paper_memory.core_claim} {paper_memory.methodology} {' '.join(paper_memory.key_results)}"
        memory_vec = embed(memory_text)
        upsert_paper_memory(
            self.qdrant,
            paper_id=paper.paper_id,
            vector=memory_vec,
            payload={
                "paper_id": paper.paper_id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "core_claim": paper_memory.core_claim,
                "methodology": paper_memory.methodology,
                "key_results": paper_memory.key_results,
                "limitations": paper_memory.limitations,
                "novelty": paper_memory.novelty,
                "target_domain": paper_memory.target_domain,
            },
        )

        # Whole-paper embedding (average of chunks)
        if chunk_vectors:
            paper_vec = average_embeddings(chunk_vectors)
            upsert_paper_vec(
                self.qdrant,
                paper_id=paper.paper_id,
                vector=paper_vec,
                payload={
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "year": paper.year,
                },
            )

        # Step 7: Session finalize
        concept_tags = [cm.concept for cm in concept_memories[:10]]
        self.session_manager.set_paper_status(paper.paper_id, "indexed", concept_tags)
        self.session_manager.update_session_delta(session_id, delta)

        return {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "session_id": session_id,
            "chunks_created": len(chunks),
            "concepts_extracted": len(concept_memories),
            "delta": delta,
        }
