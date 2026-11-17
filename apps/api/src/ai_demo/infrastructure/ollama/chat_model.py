"""ChatModel adapter backed by a local Ollama server."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ollama import Client

from ai_demo.domain.conversation.model import Message, ToolCall
from ai_demo.domain.conversation.ports import ChatChunk


def to_ollama(m: Message) -> dict[str, Any]:
    out: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        out["tool_calls"] = [{"function": {"name": c.name, "arguments": c.arguments}} for c in m.tool_calls]
    if m.tool_name:
        out["tool_name"] = m.tool_name
    return out


class OllamaChatModel:
    def __init__(self, client: Client, model: str, temperature: float = 0.2) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature

    def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> Iterator[ChatChunk]:
        resp = self.client.chat(
            model=self.model,
            messages=[to_ollama(m) for m in messages],
            tools=tools or None,
            stream=True,
            think=False,
            options={"temperature": self.temperature},
        )
        for part in resp:
            msg = part.message
            calls = tuple(
                ToolCall(c.function.name, dict(c.function.arguments or {})) for c in (msg.tool_calls or [])
            )
            if msg.content or calls:
                yield ChatChunk(text=msg.content or "", tool_calls=calls)
