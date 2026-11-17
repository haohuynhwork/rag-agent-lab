"""API + real Chroma/SQLite/extractor, with fake chat model and embedder."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_demo.config import Settings
from ai_demo.domain.conversation.ports import ChatChunk
from ai_demo.interfaces.api.deps import build_container
from ai_demo.interfaces.api.main import create_app
from tests.fakes import BagOfWordsEmbedder, ScriptedChatModel


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(data_dir=tmp_path, web_dist=tmp_path / "nope", _env_file=None)  # type: ignore[call-arg]
    model = ScriptedChatModel([[ChatChunk("Cats sit "), ChatChunk("[1].")]])
    container = build_container(settings, chat_model=model, embedder=BagOfWordsEmbedder())
    return TestClient(create_app(container))


def sse_events(text: str) -> list[dict]:
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def test_document_lifecycle_and_rag_chat(client: TestClient) -> None:
    r = client.post(
        "/api/documents", files={"file": ("pets.md", b"The cat sat on the mat.", "text/markdown")}
    )
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["chunk_count"] == 1

    assert [d["id"] for d in client.get("/api/documents").json()] == [doc["id"]]

    r = client.post("/api/chat", json={"question": "what did the cat do?", "mode": "rag"})
    events = sse_events(r.text)
    assert [e["type"] for e in events] == ["citations", "token", "token", "done"]
    assert events[0]["data"][0]["filename"] == "pets.md"

    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert client.get("/api/documents").json() == []
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 404


def test_rejects_unsupported_file(client: TestClient) -> None:
    r = client.post("/api/documents", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 415


def test_rejects_empty_file(client: TestClient) -> None:
    r = client.post("/api/documents", files={"file": ("e.txt", b"   ", "text/plain")})
    assert r.status_code == 422


def test_chat_validation(client: TestClient) -> None:
    assert client.post("/api/chat", json={"question": "", "mode": "rag"}).status_code == 422
    assert client.post("/api/chat", json={"question": "x", "mode": "bad"}).status_code == 422
