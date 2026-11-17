"""Knowledge context: documents and their chunks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class DocumentId:
    value: str

    @classmethod
    def new(cls) -> DocumentId:
        return cls(uuid.uuid4().hex)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class SourceRef:
    """Where a chunk came from — used for citations."""

    document_id: DocumentId
    filename: str
    chunk_index: int


@dataclass(frozen=True, slots=True)
class Chunk:
    id: str
    source: SourceRef
    text: str


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    chunk: Chunk
    score: float  # higher = more similar


@dataclass(slots=True)
class Document:
    """Aggregate root. Owns its chunks."""

    id: DocumentId
    filename: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    chunks: list[Chunk] = field(default_factory=list)
    chunk_count: int = 0  # persisted separately so chunks needn't be loaded

    @classmethod
    def create(cls, filename: str) -> Document:
        if not filename.strip():
            raise ValueError("filename must not be empty")
        return cls(id=DocumentId.new(), filename=filename)

    def attach_chunks(self, texts: list[str]) -> list[Chunk]:
        if not texts:
            raise ValueError(f"document {self.filename!r} produced no text")
        self.chunks = [
            Chunk(
                id=f"{self.id}:{i}",
                source=SourceRef(self.id, self.filename, i),
                text=t,
            )
            for i, t in enumerate(texts)
        ]
        self.chunk_count = len(self.chunks)
        return self.chunks
