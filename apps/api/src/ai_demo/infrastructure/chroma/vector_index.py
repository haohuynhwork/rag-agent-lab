"""VectorIndex adapter backed by an embedded, persistent Chroma collection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from ai_demo.domain.documents.model import Chunk, DocumentId, ScoredChunk, SourceRef


class ChromaVectorIndex:
    def __init__(self, path: Path | None, collection: str = "chunks") -> None:
        client = chromadb.PersistentClient(path=str(path)) if path else chromadb.EphemeralClient()
        # cosine distance -> similarity = 1 - distance
        self.col = client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        metadatas: list[Any] = [
            {
                "document_id": str(c.source.document_id),
                "filename": c.source.filename,
                "chunk_index": c.source.chunk_index,
            }
            for c in chunks
        ]
        self.col.upsert(
            ids=[c.id for c in chunks],
            embeddings=vectors,  # type: ignore[arg-type]
            documents=[c.text for c in chunks],
            metadatas=metadatas,
        )

    def search(self, vector: list[float], k: int) -> list[ScoredChunk]:
        if self.col.count() == 0:
            return []
        res = self.col.query(
            query_embeddings=[vector],  # type: ignore[arg-type]
            n_results=min(k, self.col.count()),
            include=["documents", "metadatas", "distances"],
        )
        ids = res["ids"][0]
        docs = (res["documents"] or [[]])[0]
        metas = (res["metadatas"] or [[]])[0]
        dists = (res["distances"] or [[]])[0]
        out = []
        for cid, text, meta, dist in zip(ids, docs, metas, dists, strict=True):
            src = SourceRef(
                DocumentId(str(meta["document_id"])),
                str(meta["filename"]),
                int(meta["chunk_index"]),  # type: ignore[arg-type]
            )
            out.append(ScoredChunk(Chunk(cid, src, text or ""), 1.0 - float(dist)))
        return out

    def delete_document(self, document_id: DocumentId) -> None:
        self.col.delete(where={"document_id": str(document_id)})
