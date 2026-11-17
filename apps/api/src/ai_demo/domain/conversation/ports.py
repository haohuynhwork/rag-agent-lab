"""Ports for the Assistant context."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol

from .model import Message, ToolCall


@dataclass(frozen=True, slots=True)
class ChatChunk:
    """One streamed piece of a model response."""

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


class ChatModel(Protocol):
    def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> Iterator[ChatChunk]: ...


class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema

    def run(self, **kwargs: Any) -> str: ...
