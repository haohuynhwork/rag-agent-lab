"""In-memory fakes for every port, so domain/application tests need no Ollama or Chroma."""

from __future__ import annotations

import math
from collections.abc import Iterator
from typing import Any

from ai_demo.domain.conversation.model import Message
from ai_demo.domain.conversation.ports import ChatChunk
from ai_demo.domain.documents.model import Chunk, Document, DocumentId, ScoredChunk

VOCAB = ["cat", "dog", "python", "rust", "ollama", "vector", "price", "refund"]


class BagOfWordsEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            low = t.lower()
            v = [float(low.count(w)) for w in VOCAB] + [0.01]
            n = math.sqrt(sum(x * x for x in v))
            out.append([x / n for x in v])
        return out


class MemoryIndex:
    def __init__(self) -> None:
        self.items: dict[str, tuple[Chunk, list[float]]] = {}

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        for c, v in zip(chunks, vectors, strict=True):
            self.items[c.id] = (c, v)

    def search(self, vector: list[float], k: int) -> list[ScoredChunk]:
        scored = [
            ScoredChunk(c, sum(a * b for a, b in zip(vector, v, strict=True))) for c, v in self.items.values()
        ]
        return sorted(scored, key=lambda s: s.score, reverse=True)[:k]

    def delete_document(self, document_id: DocumentId) -> None:
        self.items = {k: v for k, v in self.items.items() if v[0].source.document_id != document_id}


class MemoryRepo:
    def __init__(self) -> None:
        self.docs: dict[DocumentId, Document] = {}

    def add(self, document: Document) -> None:
        self.docs[document.id] = document

    def get(self, document_id: DocumentId) -> Document | None:
        return self.docs.get(document_id)

    def list(self) -> list[Document]:
        return list(self.docs.values())

    def delete(self, document_id: DocumentId) -> None:
        self.docs.pop(document_id, None)


class PlainTextExtractor:
    def extract(self, filename: str, data: bytes) -> str:
        return data.decode()


class ScriptedChatModel:
    """Replays a scripted list of turns; each turn is a list of ChatChunks."""

    def __init__(self, turns: list[list[ChatChunk]]) -> None:
        self.turns = list(turns)
        self.calls: list[tuple[list[Message], list[dict[str, Any]] | None]] = []

    def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> Iterator[ChatChunk]:
        self.calls.append((list(messages), tools))
        turn = self.turns.pop(0) if self.turns else [ChatChunk(text="(no more script)")]
        yield from turn
