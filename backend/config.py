import os
from dotenv import load_dotenv

load_dotenv()

# LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MEMORY_LLM_MODEL = os.getenv("MEMORY_LLM_MODEL", "gpt-4o-mini")   # or "ollama/llama3.1:8b"
GENERATION_LLM_MODEL = os.getenv("GENERATION_LLM_MODEL", "gpt-4o")

# Embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIM = 3072

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Redis / Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Grobid
GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")

# SQLite
SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///./research_assistant.db")

# Graph persistence
GRAPH_PATH = os.getenv("GRAPH_PATH", "./data/knowledge_graph.pickle")

# Upload dir
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data/papers")

# Chunking
MAX_CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64

# Retrieval thresholds
CONCEPT_MERGE_THRESHOLD = 0.92
CONCEPT_SIMILAR_THRESHOLD = 0.75
TOP_MEMORIES_FOR_CLUE = 40
TOP_MEMORIES_CONTEXT = 20
RETRIEVAL_CANDIDATES = 50
FINAL_CHUNKS = 10

# Scoring weights
CROSS_ENCODER_WEIGHT = 0.5
GRAPH_SCORE_WEIGHT = 0.3
MMR_WEIGHT = 0.2
MMR_LAMBDA = 0.7

# Cluster detection — kept low so small libraries still see clusters
MIN_CLUSTER_PAPERS = 3
MIN_CLUSTER_CONCEPTS = 1
