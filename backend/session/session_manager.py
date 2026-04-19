from __future__ import annotations
from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.config import SQLITE_URL


class SessionManager:
    def __init__(self, db_url: str = SQLITE_URL):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    paper_count INTEGER DEFAULT 0,
                    new_concepts_count INTEGER DEFAULT 0,
                    new_edges_count INTEGER DEFAULT 0,
                    new_clusters_count INTEGER DEFAULT 0
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    title TEXT,
                    authors TEXT,
                    year INTEGER,
                    status TEXT DEFAULT 'processing',
                    file_path TEXT,
                    source_type TEXT,
                    concept_tags TEXT,
                    created_at TEXT NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL,
                    text TEXT,
                    page INTEGER,
                    created_at TEXT NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS reading_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL,
                    event_type TEXT,
                    timestamp TEXT NOT NULL
                )
            """))
            conn.commit()

    def create_session(self) -> str:
        session_id = str(uuid4())
        with self.engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO sessions (session_id, created_at) VALUES (:sid, :ts)"
            ), {"sid": session_id, "ts": datetime.utcnow().isoformat()})
            conn.commit()
        return session_id

    def get_or_create_active_session(self) -> str:
        with self.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT 1"
            )).fetchone()
        if row:
            return row[0]
        return self.create_session()

    def insert_paper(self, paper_id: str, session_id: str, title: str,
                     authors: list[str], year: int | None,
                     file_path: str, source_type: str) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO papers
                (paper_id, session_id, title, authors, year, status, file_path, source_type, created_at)
                VALUES (:pid, :sid, :title, :authors, :year, 'processing', :fp, :st, :ts)
            """), {
                "pid": paper_id,
                "sid": session_id,
                "title": title,
                "authors": ", ".join(authors) if authors else "",
                "year": year,
                "fp": file_path,
                "st": source_type,
                "ts": datetime.utcnow().isoformat(),
            })
            conn.execute(text(
                "UPDATE sessions SET paper_count = paper_count + 1 WHERE session_id = :sid"
            ), {"sid": session_id})
            conn.commit()

    def set_paper_status(self, paper_id: str, status: str,
                         concept_tags: list[str] | None = None) -> None:
        with self.engine.connect() as conn:
            tags_str = ", ".join(concept_tags) if concept_tags else ""
            conn.execute(text(
                "UPDATE papers SET status = :status, concept_tags = :tags WHERE paper_id = :pid"
            ), {"status": status, "tags": tags_str, "pid": paper_id})
            conn.commit()

    def update_session_delta(self, session_id: str, delta: dict) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE sessions SET
                    new_concepts_count = new_concepts_count + :nc,
                    new_edges_count = new_edges_count + :ne,
                    new_clusters_count = new_clusters_count + :nk
                WHERE session_id = :sid
            """), {
                "nc": delta.get("new_concepts", 0),
                "ne": delta.get("new_edges", 0),
                "nk": delta.get("new_clusters", 0),
                "sid": session_id,
            })
            conn.commit()

    def list_papers(self) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT paper_id, session_id, title, authors, year, status, file_path, concept_tags, created_at FROM papers ORDER BY created_at DESC"
            )).fetchall()
        return [
            {
                "paper_id": r[0],
                "session_id": r[1],
                "title": r[2],
                "authors": r[3],
                "year": r[4],
                "status": r[5],
                "file_path": r[6],
                "concept_tags": (r[7] or "").split(", ") if r[7] else [],
                "created_at": r[8],
            }
            for r in rows
        ]

    def get_paper(self, paper_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT paper_id, session_id, title, authors, year, status, file_path, concept_tags, created_at FROM papers WHERE paper_id = :pid"
            ), {"pid": paper_id}).fetchone()
        if not row:
            return None
        return {
            "paper_id": row[0],
            "session_id": row[1],
            "title": row[2],
            "authors": row[3],
            "year": row[4],
            "status": row[5],
            "file_path": row[6],
            "concept_tags": (row[7] or "").split(", ") if row[7] else [],
            "created_at": row[8],
        }

    def delete_paper(self, paper_id: str) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM papers WHERE paper_id = :pid"), {"pid": paper_id})
            conn.execute(text("DELETE FROM annotations WHERE paper_id = :pid"), {"pid": paper_id})
            conn.execute(text("DELETE FROM reading_events WHERE paper_id = :pid"), {"pid": paper_id})
            conn.commit()

    def list_sessions(self) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT session_id, created_at, paper_count, new_concepts_count, new_edges_count, new_clusters_count FROM sessions ORDER BY created_at DESC"
            )).fetchall()
        return [
            {
                "session_id": r[0],
                "created_at": r[1],
                "paper_count": r[2],
                "new_concepts": r[3],
                "new_edges": r[4],
                "new_clusters": r[5],
            }
            for r in rows
        ]

    def get_session_papers(self, session_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT paper_id, title, authors, year, status, concept_tags FROM papers WHERE session_id = :sid"
            ), {"sid": session_id}).fetchall()
        return [
            {
                "paper_id": r[0],
                "title": r[1],
                "authors": r[2],
                "year": r[3],
                "status": r[4],
                "concept_tags": (r[5] or "").split(", ") if r[5] else [],
            }
            for r in rows
        ]

    def add_annotation(self, paper_id: str, text: str, page: int) -> None:
        with self.engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO annotations (paper_id, text, page, created_at) VALUES (:pid, :text, :page, :ts)"
            ), {"pid": paper_id, "text": text, "page": page, "ts": datetime.utcnow().isoformat()})
            conn.commit()

    def get_annotations(self, paper_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, text, page, created_at FROM annotations WHERE paper_id = :pid"
            ), {"pid": paper_id}).fetchall()
        return [{"id": r[0], "text": r[1], "page": r[2], "created_at": r[3]} for r in rows]
