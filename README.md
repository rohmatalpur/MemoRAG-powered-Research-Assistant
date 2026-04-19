# MemoRAG-powered Research Assistant 

A MemoRAG-powered research assistant that accumulates knowledge across reading sessions, links papers through concept and citation graphs, and drafts cited literature reviews from persistent memory.

---

## What It Does

Most RAG systems treat every query as if you have never read anything before. You paste in a document, ask a question, and get an answer grounded only in that document. The moment the conversation ends, everything is forgotten.

This system works differently. Every paper you upload is permanently processed into three types of memory — what it claims, what concepts it introduces, and how it relates to other papers. These memories accumulate across sessions into a growing knowledge graph. When you ask a question, the system does not start from scratch: it first reads its own memory of everything you have ever uploaded, drafts a preliminary answer from that memory alone, then uses that draft to guide retrieval of the most relevant passages. The final answer is grounded in both long-term memory and precise retrieved evidence, with every claim linked back to the exact paper, section, and page it came from.

---

## The RAG Technique: MemoRAG


**MemoRAG** adds a memory layer that runs before retrieval:

```
Standard RAG:   Query → Embed → Retrieve chunks → Generate answer

MemoRAG:        Query → Memory LLM reads all past sessions
                      → Generates a "clue" (preliminary draft answer)
                      → Clue + Query → Embed → Retrieve chunks
                      → Generation LLM produces final cited answer
```

The "clue" is a 150–300 token preliminary answer generated purely from compressed memory — no retrieval yet. It names the specific papers and key claims the system already knows are relevant. This clue is concatenated with the original query before embedding, so the retrieval vector already knows *which papers matter* before it searches the vector database. The result is that retrieval is guided by accumulated knowledge rather than just keyword overlap.

This system extends core MemoRAG with two additional signals layered on top:

- **Knowledge graph proximity scoring** — chunks from papers that are graph-neighbors of the papers named in the clue get a score boost during reranking
- **Cross-encoder semantic reranking** — retrieved candidates are re-scored by a fine-tuned cross-encoder before final selection

---

## What the User Can Do

### Library View
Upload research papers as PDF, DOCX, or URL (arXiv, blog posts, preprints). Each paper is automatically processed in the background. The library shows title, authors, year, processing status, and up to 10 concept tags auto-extracted by the Memory LLM. 

### Knowledge Graph View
An interactive force-directed graph that grows with every paper you add:
- **Blue circles** — paper nodes
- **Amber squares** — concept nodes (shared technical concepts extracted across papers)
- **Purple circles** — cluster nodes (research theme groups auto-detected by the Louvain algorithm)
- **Edges** — citation links, extension links, contradiction links, concept similarity links


### Chat Interface
Ask anything about your library in natural language:
- *"What did Vaswani et al. say about positional encoding?"*
- *"Which papers in my library disagree on sparse attention efficiency?"*
- *"Draft a related work section on RLHF for my paper"*

Every answer includes clickable citations linking to the exact paper and page, a memory trace showing which sessions contributed to the answer, and an expandable memory clue showing what the system recalled before retrieval.

**Draft mode** produces full academic-style writing with subheadings, structured paragraphs, and an outline — designed for generating literature review sections directly.

### Session Timeline
A chronological view of every reading session showing how many papers were added, how many new concepts were extracted, how many new graph edges were formed, and how many new research clusters emerged. Each session is a snapshot of how your knowledge graph grew.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│        Library · Knowledge Graph · Chat · Session Timeline      │
└──────────────┬──────────────────────────────┬───────────────────┘
               │ upload                       │ query
               ▼                             ▼
┌──────────────────────────┐   ┌─────────────────────────────────┐
│    INGESTION PIPELINE    │   │         QUERY PIPELINE          │
│  Parser → Chunker →      │   │  Classify → Compress Memory →   │
│  Memory LLM → Graph →    │   │  Clue → Retrieve → Rerank →     │
│  Vector Index            │   │  Generate → Cite                │
└──────────────────────────┘   └─────────────────────────────────┘
               │                             │
               ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         MEMORY STORE                            │
│   Qdrant (vectors) · NetworkX (graph) · SQLite (sessions)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Components

### 1. Ingestion Module (`backend/ingestion/`)



**How it works:**

**Parser (`parser.py`)** detects the source type and routes accordingly:
- *Academic PDF* → sends to the Grobid REST API which returns TEI XML containing all sections.
- *DOCX* → python-docx walks paragraph styles, using Heading styles to detect section boundaries.
- *URL* → trafilatura fetches the HTML and strips boilerplate. BeautifulSoup then walks the DOM, grouping content between `<h1>`–`<h4>` tags into named sections. Outbound links to arXiv, DOI, ACL, OpenReview, Semantic Scholar, NeurIPS, and ICML are harvested as pseudo-references. Numbered reference list items are extracted via regex. This means even a blog post that links to papers can create citation edges in the knowledge graph.

**Chunker (`chunker.py`)** splits each section at paragraph boundaries:
- Sections under 512 tokens → single chunk
- Sections 512–1024 tokens → split at paragraph breaks
- Sections over 1024 tokens → sliding window with 64-token overlap between adjacent chunks

Each chunk retains its parent section heading, section type, and page range as metadata. 

---

### 2. Memory LLM Module 

Every paper is automatically understood — not just indexed. The system knows what each paper claims, what concepts it introduces, and how it relates to other papers in your library.

**How it works:**

On ingestion, three separate LLM calls run against the paper's chunks using LLM:

**Paper Memory** — extracts a structured JSON summary:
```
core_claim, methodology, key_results[], limitations, novelty, target_domain
```


**Concept Memory** — extracts all named technical concepts:
```
concept name, definition in context, introduced_here (bool), related_concepts[]
```
Each concept becomes a node candidate for the knowledge graph.

**Relational Memory** — classifies each reference in the paper's bibliography:
```
foundational | extends | critiques | uses_as_baseline | agrees_with
```
These classifications become typed edges in the knowledge graph.

At query time, the Memory LLM also generates the **memory clue** — it receives a compressed block of the top-20 most relevant paper memory digests (ranked by query similarity + PageRank score) plus the top-10 relevant concept cluster summaries, and produces a 150–300 token preliminary answer naming specific papers and key tensions before any retrieval happens.

---

### 3. Knowledge Graph Module

The system discovers connections between papers automatically.

**How it works:**

The graph is a NetworkX `MultiDiGraph` persisted to disk as a pickle file after every ingestion. It contains three node types:

- **PaperNode** — paper_id, title, authors, year, session_added, memory_digest, pagerank_score
- **ConceptNode** — label, definition, paper_count (how many papers discuss this concept)
- **ClusterNode** — LLM-generated theme label, member list, paper_count

And six edge types:

| Edge | Meaning |
|------|---------|
| `CITES` | Paper A references Paper B |
| `EXTENDS` | Paper A builds directly on Paper B |
| `CRITIQUES` | Paper A challenges Paper B |
| `DISCUSSES` | Paper A uses a concept |
| `SIMILAR_TO` | Two concepts are semantically close (cosine > 0.75) |
| `CONTRADICTS` | Two papers make opposing claims about the same concept |

**Concept deduplication** When a new concept arrives, its embedding is compared against all existing concept nodes in Qdrant. If similarity > 0.92 → merge into existing node (increment paper_count). If 0.75–0.92 → create new node and add a `SIMILAR_TO` edge. If < 0.75 → isolated new node. This prevents the graph from filling with duplicate nodes for the same idea phrased differently across papers.

**Contradiction detection:** For every concept a new paper discusses, the system fetches all other papers discussing the same concept and runs a targeted Memory LLM prompt: *"Do these two papers make opposing claims about [concept]?"*. If yes, a `CONTRADICTS` edge is added with the evidence quoted.

**PageRank:** After every ingestion batch, PageRank runs on the paper-only subgraph (edges = CITES + EXTENDS). Well-cited papers within your library get higher scores, which determines their priority in the memory compression step at query time.

**Cluster detection:** The Louvain community detection algorithm runs on the undirected projection of the full graph. Communities that contain at least 3 papers and 1 shared concept become ClusterNodes. The Memory LLM names each cluster from its member paper titles.

---

### 4. Retrieval Module

Answers grounded in the most relevant passages from your library, not just the nearest embedding matches. 

**How it works:**

**Step 1 — Clue-guided retrieval:** The memory clue text is concatenated with the original query and the suggested search terms the clue extracted, then embedded using `text-embedding-3-large`. This composite vector is used to search Qdrant's `chunks` collection for the top 50 candidate chunks.

**Step 2 — Three-stage reranking (`reranker.py`):**

*Stage 1 — Cross-encoder semantic scoring:* `cross-encoder/ms-marco-MiniLM-L-6-v2` scores every candidate chunk against the original query.

*Stage 2 — Graph proximity boosting:* For each candidate chunk's parent paper, the shortest path length to each paper named in the memory clue is computed on the undirected graph. Score = Σ(1 / (1 + path_length)) / num_anchor_papers. 

*Stage 3 — MMR diversity:* Maximal Marginal Relevance selects the final 10 chunks by balancing relevance against redundancy — prevents five near-identical chunks from the same paper crowding the context window.

**Final score:** `0.5 × cross_encoder + 0.3 × graph_proximity + 0.2 × MMR_diversity`

---

### 5. Generation Module

Cited answers where every claim links back to the exact paper, section, and page it came from. In draft mode, full academic-style literature review sections with subheadings.

**How it works:**

The context window sent to GPT-4o is assembled as:
1. System prompt instructing citation format `[Author et al. YEAR, §Section, p.N]`
2. Memory clue (the preliminary draft from memory)
3. 10 retrieved chunks, each labelled with paper title, section heading, and page number
4. The user's original query

GPT-4o responds in structured JSON: `{answer, citations[], memory_trace[]}`. Each citation includes ref_id, paper name, section, page, and a direct quote.

---

### 6. Session Manager 

A persistent history of every reading session — what was added, what the system learned, and how the knowledge graph changed.

## Storage Layer

| Store | Technology | What it holds |
|-------|------------|---------------|
| Vector DB | Qdrant (Docker) | 4 collections: `chunks` (raw passage embeddings), `papers` (whole-paper embeddings), `memories` (paper memory digest embeddings), `concepts` (concept node embeddings for deduplication) |
| Knowledge Graph | NetworkX pickled to disk | All paper, concept, and cluster nodes with typed edges |
| Session Store | SQLite via SQLAlchemy | Sessions, paper metadata, annotations, reading events |
| File Storage | Docker named volume | Uploaded PDF and DOCX files |
| Task Queue | Redis + Celery | Background ingestion tasks |

All four stores are backed by Docker named volumes and persist across container restarts. Running `docker compose down` without `-v` leaves all data intact.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Python 3.11 |
| Memory & Generation LLM | GPT-4o-mini (memory) + GPT-4o (generation) via LiteLLM |
| Embeddings | OpenAI `text-embedding-3-large` (3072-dim) |
| Cross-encoder reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (HuggingFace, CPU) |
| Vector DB | Qdrant |
| Knowledge graph | NetworkX 3.x |
| Community detection | python-louvain (Louvain algorithm) |
| PDF parsing | Grobid 0.8 + PyMuPDF fallback |
| Task queue | Celery + Redis |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Containerization | Docker Compose |

---

## Setup and Installation

### Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- An OpenAI API key

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd personal_assistant_research
```

### 2. Configure environment variables

Open `.env` and set your OpenAI API key:

```env
OPENAI_API_KEY=sk-...your-key-here...

# Models (defaults are fine)
MEMORY_LLM_MODEL=gpt-4o-mini
GENERATION_LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-large
```

### 3. Build and start all services

```bash
docker compose up --build
```
### 4. Open the application

```
http://localhost:3000
```

---
