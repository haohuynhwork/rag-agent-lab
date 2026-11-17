"""HTTP interface. Thin: validate, call a use case, serialize."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai_demo.application.dto import AskCommand, HistoryItem
from ai_demo.config import Settings
from ai_demo.infrastructure.loaders.extractor import UnsupportedFileType

from .deps import Container, build_container

# ---------------------------------------------------------------- schemas


class DocumentOut(BaseModel):
    id: str
    filename: str
    chunk_count: int
    created_at: str


class HistoryIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatIn(BaseModel):
    question: str = Field(min_length=1)
    mode: Literal["plain", "rag", "agent"] = "rag"
    history: list[HistoryIn] = []


class HealthOut(BaseModel):
    status: str
    chat_model: str
    embed_model: str


# ---------------------------------------------------------------- app


def create_app(container: Container | None = None) -> FastAPI:
    c = container or build_container(Settings())
    s = c.settings
    app = FastAPI(title="ai-demo", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/health", response_model=HealthOut)
    def health() -> HealthOut:
        return HealthOut(status="ok", chat_model=s.chat_model, embed_model=s.embed_model)

    @app.get("/api/documents", response_model=list[DocumentOut])
    def list_documents() -> list[DocumentOut]:
        return [DocumentOut(**asdict(d)) for d in c.knowledge.list_documents()]

    @app.post("/api/documents", response_model=DocumentOut, status_code=201)
    def upload_document(file: UploadFile) -> DocumentOut:
        data = file.file.read(s.max_upload_mb * 1024 * 1024 + 1)
        if len(data) > s.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"file larger than {s.max_upload_mb} MB")
        try:
            view = c.knowledge.ingest(file.filename or "upload.txt", data)
        except UnsupportedFileType as e:
            raise HTTPException(415, str(e)) from e
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        return DocumentOut(**asdict(view))

    @app.delete("/api/documents/{document_id}", status_code=204)
    def delete_document(document_id: str) -> None:
        if not c.knowledge.delete(document_id):
            raise HTTPException(404, "document not found")

    @app.post("/api/chat")
    def chat(body: ChatIn, request: Request) -> StreamingResponse:
        cmd = AskCommand(body.question, body.mode, [HistoryItem(h.role, h.content) for h in body.history])

        def sse() -> Iterator[str]:
            for ev in c.ask(cmd):
                yield f"data: {json.dumps(ev.to_dict(), ensure_ascii=False)}\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    # Serve the built React app (if present) for everything else.
    if (s.web_dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=s.web_dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            return FileResponse(s.web_dist / "index.html")

    return app


def run() -> None:
    import uvicorn

    uvicorn.run("ai_demo.interfaces.api.main:create_app", factory=True, reload=True, port=8000)
