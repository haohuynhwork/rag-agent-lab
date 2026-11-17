"""Tool-calling agent loop plus the built-in tools."""

from __future__ import annotations

import ast
import json
import operator
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from ai_demo.domain.conversation.model import Citation, Message, ToolCall
from ai_demo.domain.conversation.ports import ChatModel, Tool

from .dto import AnswerEvent
from .ingest_document import KnowledgeService
from .prompts import format_context

# ---------------------------------------------------------------- tools


@dataclass
class SearchDocsTool:
    knowledge: KnowledgeService
    k: int = 4
    citations: list[Citation] = field(default_factory=list)  # accumulated across calls
    name: str = "search_docs"
    description: str = "Semantic search over the user's uploaded documents. Returns numbered passages."
    parameters: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look for"}},
            "required": ["query"],
        }
    )

    def run(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return "error: query is required"
        hits = self.knowledge.search(query, self.k)
        if not hits:
            return "No documents indexed yet."
        start = len(self.citations) + 1
        for i, h in enumerate(hits, start=start):
            s = h.chunk.source
            self.citations.append(
                Citation(i, str(s.document_id), s.filename, s.chunk_index, h.chunk.text[:300], h.score)
            )
        return format_context(hits, start=start)


@dataclass
class ListDocsTool:
    knowledge: KnowledgeService
    name: str = "list_docs"
    description: str = "List the documents in the user's library."
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})

    def run(self, **kwargs: Any) -> str:
        docs = self.knowledge.list_documents()
        if not docs:
            return "The library is empty."
        return "\n".join(f"- {d.filename} ({d.chunk_count} chunks)" for d in docs)


_OPS: dict[type, Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval(expr: str) -> float:
    def ev(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            if isinstance(node.op, ast.Pow) and abs(ev(node.right)) > 100:
                raise ValueError("exponent too large")
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("unsupported expression")

    return float(ev(ast.parse(expr, mode="eval")))


@dataclass
class CalculatorTool:
    name: str = "calculator"
    description: str = "Evaluate an arithmetic expression, e.g. '(12.5 * 4) / 3'."
    parameters: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        }
    )

    def run(self, **kwargs: Any) -> str:
        try:
            result = safe_eval(str(kwargs.get("expression", "")))
        except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as e:
            return f"error: {e}"
        return f"{result:g}"


def tool_schema(tool: Tool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters},
    }


# ---------------------------------------------------------------- loop


@dataclass(slots=True)
class AgentLoop:
    model: ChatModel
    tools: list[Tool]
    max_steps: int = 5

    def run(self, messages: list[Message]) -> Iterator[AnswerEvent]:
        by_name = {t.name: t for t in self.tools}
        schemas = [tool_schema(t) for t in self.tools]
        msgs = list(messages)

        for _ in range(self.max_steps):
            text_parts: list[str] = []
            calls: list[ToolCall] = []
            for chunk in self.model.stream(msgs, tools=schemas):
                if chunk.text:
                    text_parts.append(chunk.text)
                    yield AnswerEvent("token", chunk.text)
                calls.extend(chunk.tool_calls)

            msgs.append(Message("assistant", "".join(text_parts), tool_calls=tuple(calls)))
            if not calls:
                return

            for call in calls:
                yield AnswerEvent("tool_call", {"name": call.name, "arguments": call.arguments})
                tool = by_name.get(call.name)
                if tool is None:
                    result = f"error: unknown tool {call.name!r}"
                else:
                    try:
                        result = tool.run(**call.arguments)
                    except Exception as e:  # tool failures go back to the model
                        result = f"error: {e}"
                yield AnswerEvent("tool_result", {"name": call.name, "result": result[:2000]})
                msgs.append(Message("tool", result, tool_name=call.name))

        yield AnswerEvent("warning", f"agent stopped after {self.max_steps} steps")


def dumps_args(args: dict[str, Any]) -> str:
    return json.dumps(args, ensure_ascii=False)
