from __future__ import annotations
from celery import Celery
from backend.config import REDIS_URL

celery_app = Celery("research_assistant", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]


@celery_app.task(bind=True, name="tasks.ingest_paper")
def ingest_paper_task(self, source: str, session_id: str | None = None) -> dict:
    """Background task: run full ingestion pipeline for a paper."""
    from qdrant_client import QdrantClient
    from backend.session.session_manager import SessionManager
    from backend.graph.graph_store import load_graph
    from backend.ingestion.pipeline import IngestionPipeline
    from backend.config import QDRANT_HOST, QDRANT_PORT

    session_manager = SessionManager()
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    graph = load_graph()
    pipeline = IngestionPipeline(session_manager, qdrant, graph)

    try:
        result = pipeline.ingest(source, session_id)
        return {"status": "success", **result}
    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise
