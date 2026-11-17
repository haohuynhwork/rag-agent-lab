"""Use cases for the Knowledge context: ingest, list, delete, search."""

from __future__ import annotations

from dataclasses import dataclass

from ai_demo.domain.documents.chunking import ChunkingPolicy
from ai_demo.domain.documents.model import Document, DocumentId, ScoredChunk
from ai_demo.domain.documents.ports import DocumentRepository, Embedder, TextExtractor, VectorIndex

from .dto import DocumentView

EMBED_BATCH = 32


def to_view(doc: Document) -> DocumentView:
    return DocumentView(
        id=str(doc.id),
        filename=doc.filename,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat(),
    )


@dataclass(slots=True)
class KnowledgeService:
    repo: DocumentRepository
    index: VectorIndex
    embedder: Embedder
    extractor: TextExtractor
    chunking: ChunkingPolicy

    def ingest(self, filename: str, data: bytes) -> DocumentView:
        text = self.extractor.extract(filename, data)
        doc = Document.create(filename)
        chunks = doc.attach_chunks(self.chunking.split(text))
        vectors: list[list[float]] = []
        for i in range(0, len(chunks), EMBED_BATCH):
            vectors.extend(self.embedder.embed([c.text for c in chunks[i : i + EMBED_BATCH]]))
        self.index.upsert(chunks, vectors)
        self.repo.add(doc)
        return to_view(doc)

    def list_documents(self) -> list[DocumentView]:
        return [to_view(d) for d in self.repo.list()]

    def delete(self, document_id: str) -> bool:
        did = DocumentId(document_id)
        if self.repo.get(did) is None:
            return False
        self.index.delete_document(did)
        self.repo.delete(did)
        return True

    def search(self, query: str, k: int = 4) -> list[ScoredChunk]:
        [vector] = self.embedder.embed([query])
        return self.index.search(vector, k)
