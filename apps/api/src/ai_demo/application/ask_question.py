"""AskQuestion use case: plain | rag | agent, streamed as AnswerEvents."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ai_demo.domain.conversation.model import AnswerMode, Citation, Message
from ai_demo.domain.conversation.policies import (
    GroundingPolicy,
    GuardrailViolation,
    InputPolicy,
    cited_numbers,
)
from ai_demo.domain.conversation.ports import ChatModel

from .agent_loop import AgentLoop, CalculatorTool, ListDocsTool, SearchDocsTool
from .dto import AnswerEvent, AskCommand
from .ingest_document import KnowledgeService
from .prompts import AGENT_SYSTEM, NO_CONTEXT_ANSWER, PLAIN_SYSTEM, RAG_SYSTEM, rag_user_prompt

MAX_HISTORY = 10


@dataclass(slots=True)
class AskQuestion:
    model: ChatModel
    knowledge: KnowledgeService
    input_policy: InputPolicy
    grounding: GroundingPolicy
    top_k: int = 4
    agent_max_steps: int = 5

    def __call__(self, cmd: AskCommand) -> Iterator[AnswerEvent]:
        try:
            mode = AnswerMode(cmd.mode)
            for w in self.input_policy.check(cmd.question):
                yield AnswerEvent("warning", w)
            if mode is AnswerMode.PLAIN:
                yield from self._plain(cmd)
            elif mode is AnswerMode.RAG:
                yield from self._rag(cmd)
            else:
                yield from self._agent(cmd)
        except (GuardrailViolation, ValueError) as e:
            yield AnswerEvent("error", str(e))
        except Exception as e:  # infra failures (Ollama down, etc.)
            yield AnswerEvent("error", f"{type(e).__name__}: {e}")
        yield AnswerEvent("done")

    # ------------------------------------------------------------ modes

    def _history(self, cmd: AskCommand) -> list[Message]:
        return [Message(h.role, h.content) for h in cmd.history[-MAX_HISTORY:]]

    def _stream_text(self, messages: list[Message]) -> Iterator[AnswerEvent]:
        for chunk in self.model.stream(messages):
            if chunk.text:
                yield AnswerEvent("token", chunk.text)

    def _plain(self, cmd: AskCommand) -> Iterator[AnswerEvent]:
        msgs = [Message("system", PLAIN_SYSTEM), *self._history(cmd), Message("user", cmd.question)]
        yield from self._stream_text(msgs)

    def _rag(self, cmd: AskCommand) -> Iterator[AnswerEvent]:
        hits = self.knowledge.search(cmd.question, self.top_k)
        if not self.grounding.is_grounded([h.score for h in hits]):
            yield AnswerEvent("citations", [])
            yield AnswerEvent("token", NO_CONTEXT_ANSWER)
            return
        citations = [
            Citation(
                i,
                str(h.chunk.source.document_id),
                h.chunk.source.filename,
                h.chunk.source.chunk_index,
                h.chunk.text[:300],
                h.score,
            )
            for i, h in enumerate(hits, start=1)
        ]
        yield AnswerEvent.citations(citations)
        msgs = [
            Message("system", RAG_SYSTEM),
            *self._history(cmd),
            Message("user", rag_user_prompt(cmd.question, hits)),
        ]
        answer: list[str] = []
        for ev in self._stream_text(msgs):
            answer.append(ev.data)
            yield ev
        unknown = cited_numbers("".join(answer)) - {c.n for c in citations}
        if unknown:
            yield AnswerEvent("warning", f"answer cites unknown passages: {sorted(unknown)}")

    def _agent(self, cmd: AskCommand) -> Iterator[AnswerEvent]:
        search = SearchDocsTool(self.knowledge, k=self.top_k)
        loop = AgentLoop(
            self.model,
            [search, ListDocsTool(self.knowledge), CalculatorTool()],
            max_steps=self.agent_max_steps,
        )
        msgs = [Message("system", AGENT_SYSTEM), *self._history(cmd), Message("user", cmd.question)]
        seen = 0
        for ev in loop.run(msgs):
            yield ev
            if ev.type == "tool_result" and len(search.citations) > seen:
                seen = len(search.citations)
                yield AnswerEvent.citations(search.citations)
