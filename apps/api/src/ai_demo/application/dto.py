"""Events streamed out of use cases (transport-agnostic)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from ai_demo.domain.conversation.model import Citation

EventType = Literal["token", "citations", "tool_call", "tool_result", "warning", "done", "error"]


@dataclass(frozen=True, slots=True)
class AnswerEvent:
    type: EventType
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "data": self.data}

    @staticmethod
    def citations(cs: list[Citation]) -> AnswerEvent:
        return AnswerEvent("citations", [asdict(c) for c in cs])


@dataclass(frozen=True, slots=True)
class DocumentView:
    id: str
    filename: str
    chunk_count: int
    created_at: str


@dataclass(frozen=True, slots=True)
class HistoryItem:
    role: Literal["user", "assistant"]
    content: str


@dataclass(slots=True)
class AskCommand:
    question: str
    mode: str = "rag"
    history: list[HistoryItem] = field(default_factory=list)
