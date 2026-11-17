"""Assistant context: messages, citations, tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


class AnswerMode(StrEnum):
    PLAIN = "plain"  # LLM only
    RAG = "rag"  # retrieve then answer with citations
    AGENT = "agent"  # LLM decides which tools to call


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_name: str | None = None


@dataclass(frozen=True, slots=True)
class Citation:
    n: int
    document_id: str
    filename: str
    chunk_index: int
    snippet: str
    score: float


@dataclass(slots=True)
class Conversation:
    """Aggregate root for one chat thread (kept in-memory by the client for now)."""

    messages: list[Message] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self.messages.append(message)
