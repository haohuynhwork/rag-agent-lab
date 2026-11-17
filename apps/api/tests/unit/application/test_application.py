import pytest

from ai_demo.application.agent_loop import CalculatorTool, safe_eval
from ai_demo.application.ask_question import AskQuestion
from ai_demo.application.dto import AskCommand
from ai_demo.application.ingest_document import KnowledgeService
from ai_demo.application.prompts import NO_CONTEXT_ANSWER
from ai_demo.domain.conversation.model import ToolCall
from ai_demo.domain.conversation.policies import GroundingPolicy, InputPolicy
from ai_demo.domain.conversation.ports import ChatChunk
from ai_demo.domain.documents.chunking import ChunkingPolicy
from tests.fakes import (
    BagOfWordsEmbedder,
    MemoryIndex,
    MemoryRepo,
    PlainTextExtractor,
    ScriptedChatModel,
)


@pytest.fixture
def knowledge() -> KnowledgeService:
    return KnowledgeService(
        MemoryRepo(), MemoryIndex(), BagOfWordsEmbedder(), PlainTextExtractor(), ChunkingPolicy(200, 20)
    )


def make_ask(knowledge: KnowledgeService, model: ScriptedChatModel) -> AskQuestion:
    return AskQuestion(model, knowledge, InputPolicy(), GroundingPolicy(0.3), top_k=2)


def types(events: list) -> list[str]:
    return [e.type for e in events]


class TestKnowledge:
    def test_ingest_list_search_delete(self, knowledge: KnowledgeService) -> None:
        view = knowledge.ingest("pets.txt", b"The cat sat.\n\nThe dog barked.")
        assert knowledge.list_documents()[0].filename == "pets.txt"
        assert knowledge.search("cat", 1)[0].chunk.source.filename == "pets.txt"
        assert knowledge.delete(view.id)
        assert knowledge.list_documents() == []
        assert knowledge.search("cat", 1) == []
        assert not knowledge.delete(view.id)


class TestAskRag:
    def test_streams_citations_then_tokens(self, knowledge: KnowledgeService) -> None:
        knowledge.ingest("refunds.md", b"Refund requests are accepted within 30 days.")
        model = ScriptedChatModel([[ChatChunk("Within 30 days "), ChatChunk("[1].")]])
        events = list(make_ask(knowledge, model)(AskCommand("What is the refund window?", "rag")))
        assert types(events) == ["citations", "token", "token", "done"]
        assert events[0].data[0]["filename"] == "refunds.md"
        prompt = model.calls[0][0][-1].content
        assert "[1] (source: refunds.md" in prompt

    def test_ungrounded_short_circuits_without_llm(self, knowledge: KnowledgeService) -> None:
        knowledge.ingest("pets.txt", b"The cat sat.")
        model = ScriptedChatModel([])
        events = list(make_ask(knowledge, model)(AskCommand("rust vector price?", "rag")))
        assert events[1].data == NO_CONTEXT_ANSWER
        assert model.calls == []

    def test_warns_on_hallucinated_citation(self, knowledge: KnowledgeService) -> None:
        knowledge.ingest("r.md", b"refund refund")
        model = ScriptedChatModel([[ChatChunk("yes [7]")]])
        events = list(make_ask(knowledge, model)(AskCommand("refund?", "rag")))
        assert "warning" in types(events)


class TestAskOther:
    def test_plain_mode_includes_history(self, knowledge: KnowledgeService) -> None:
        from ai_demo.application.dto import HistoryItem

        model = ScriptedChatModel([[ChatChunk("hi")]])
        cmd = AskCommand("again?", "plain", [HistoryItem("user", "hello"), HistoryItem("assistant", "hey")])
        events = list(make_ask(knowledge, model)(cmd))
        assert types(events) == ["token", "done"]
        assert [m.role for m in model.calls[0][0]] == ["system", "user", "assistant", "user"]

    def test_empty_question_is_error_event(self, knowledge: KnowledgeService) -> None:
        events = list(make_ask(knowledge, ScriptedChatModel([]))(AskCommand(" ", "rag")))
        assert types(events) == ["error", "done"]

    def test_bad_mode_is_error_event(self, knowledge: KnowledgeService) -> None:
        events = list(make_ask(knowledge, ScriptedChatModel([]))(AskCommand("q", "nope")))
        assert types(events) == ["error", "done"]

    def test_agent_calls_tools_then_answers(self, knowledge: KnowledgeService) -> None:
        knowledge.ingest("refunds.md", b"Refund requests are accepted within 30 days.")
        model = ScriptedChatModel(
            [
                [ChatChunk(tool_calls=(ToolCall("search_docs", {"query": "refund"}),))],
                [ChatChunk(tool_calls=(ToolCall("calculator", {"expression": "30*2"}),))],
                [ChatChunk("30 days [1]; doubled is 60.")],
            ]
        )
        events = list(make_ask(knowledge, model)(AskCommand("refund window x2?", "agent")))
        t = types(events)
        assert t.count("tool_call") == 2
        assert "citations" in t
        assert t[-2:] == ["token", "done"]
        calc_result = [e for e in events if e.type == "tool_result"][1].data["result"]
        assert calc_result == "60"
        # tool results are fed back to the model
        assert model.calls[2][0][-1].role == "tool"

    def test_agent_step_limit(self, knowledge: KnowledgeService) -> None:
        loop_turn = [ChatChunk(tool_calls=(ToolCall("list_docs", {}),))]
        model = ScriptedChatModel([loop_turn] * 10)
        ask = AskQuestion(model, knowledge, InputPolicy(), GroundingPolicy(), agent_max_steps=3)
        events = list(ask(AskCommand("loop", "agent")))
        assert types(events).count("tool_call") == 3
        assert "warning" in types(events)

    def test_agent_unknown_tool_reported_to_model(self, knowledge: KnowledgeService) -> None:
        model = ScriptedChatModel([[ChatChunk(tool_calls=(ToolCall("rm_rf", {}),))], [ChatChunk("ok")]])
        events = list(make_ask(knowledge, model)(AskCommand("x", "agent")))
        assert "unknown tool" in next(e for e in events if e.type == "tool_result").data["result"]


class TestCalculator:
    @pytest.mark.parametrize("expr,expected", [("1+2*3", 7), ("(10-4)/3", 2), ("-2**3", -8)])
    def test_ok(self, expr: str, expected: float) -> None:
        assert safe_eval(expr) == expected

    @pytest.mark.parametrize("expr", ["__import__('os')", "a+1", "2**1000", "1/0"])
    def test_rejects(self, expr: str) -> None:
        assert CalculatorTool().run(expression=expr).startswith("error")
