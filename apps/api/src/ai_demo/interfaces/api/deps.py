"""Composition root: the ONLY place adapters are wired into use cases."""

from __future__ import annotations

from dataclasses import dataclass

from ollama import Client

from ai_demo.application.ask_question import AskQuestion
from ai_demo.application.ingest_document import KnowledgeService
from ai_demo.config import Settings
from ai_demo.domain.conversation.policies import GroundingPolicy, InputPolicy
from ai_demo.domain.conversation.ports import ChatModel
from ai_demo.domain.documents.chunking import ChunkingPolicy
from ai_demo.domain.documents.ports import Embedder
from ai_demo.infrastructure.chroma.vector_index import ChromaVectorIndex
from ai_demo.infrastructure.loaders.extractor import FileTextExtractor
from ai_demo.infrastructure.ollama.chat_model import OllamaChatModel
from ai_demo.infrastructure.ollama.embedder import OllamaEmbedder
from ai_demo.infrastructure.persistence.sqlite_repo import SqliteDocumentRepository


@dataclass(slots=True)
class Container:
    settings: Settings
    knowledge: KnowledgeService
    ask: AskQuestion


def build_container(
    settings: Settings,
    *,
    chat_model: ChatModel | None = None,
    embedder: Embedder | None = None,
) -> Container:
    """Build the app graph. Tests pass fake chat_model/embedder to avoid Ollama."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    client = Client(host=settings.ollama_host)

    knowledge = KnowledgeService(
        repo=SqliteDocumentRepository(str(settings.data_dir / "documents.sqlite")),
        index=ChromaVectorIndex(settings.data_dir / "chroma"),
        embedder=embedder or OllamaEmbedder(client, settings.embed_model),
        extractor=FileTextExtractor(),
        chunking=ChunkingPolicy(settings.chunk_size, settings.chunk_overlap),
    )
    ask = AskQuestion(
        model=chat_model or OllamaChatModel(client, settings.chat_model, settings.temperature),
        knowledge=knowledge,
        input_policy=InputPolicy(settings.max_question_chars),
        grounding=GroundingPolicy(settings.min_relevance),
        top_k=settings.top_k,
        agent_max_steps=settings.agent_max_steps,
    )
    return Container(settings, knowledge, ask)
