"""Embedder adapter backed by Ollama (e.g. nomic-embed-text)."""

from __future__ import annotations

from ollama import Client


class OllamaEmbedder:
    def __init__(self, client: Client, model: str) -> None:
        self.client = client
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self.client.embed(model=self.model, input=texts)
        return [list(v) for v in resp.embeddings]
