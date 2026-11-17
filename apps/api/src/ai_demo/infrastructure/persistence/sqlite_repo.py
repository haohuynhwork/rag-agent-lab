"""DocumentRepository adapter backed by SQLite (document metadata only; chunk text lives in Chroma)."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime

from ai_demo.domain.documents.model import Document, DocumentId

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    created_at TEXT NOT NULL,
    chunk_count INTEGER NOT NULL
)
"""


class SqliteDocumentRepository:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(_SCHEMA)
            self._conn.commit()

    def add(self, document: Document) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?)",
                (str(document.id), document.filename, document.created_at.isoformat(), document.chunk_count),
            )
            self._conn.commit()

    def get(self, document_id: DocumentId) -> Document | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, filename, created_at, chunk_count FROM documents WHERE id = ?",
                (str(document_id),),
            ).fetchone()
        return self._row(row) if row else None

    def list(self) -> list[Document]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, filename, created_at, chunk_count FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [self._row(r) for r in rows]

    def delete(self, document_id: DocumentId) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM documents WHERE id = ?", (str(document_id),))
            self._conn.commit()

    @staticmethod
    def _row(row: tuple[str, str, str, int]) -> Document:
        return Document(DocumentId(row[0]), row[1], datetime.fromisoformat(row[2]), chunk_count=row[3])
