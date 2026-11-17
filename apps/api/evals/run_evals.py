"""Evaluate retrieval + answer quality against a small labelled QA set.

Metrics
- hit@k        : expected source document appears in the top-k retrieved chunks
- keyword      : answer contains every expected keyword (cheap correctness proxy)
- refusal      : for unanswerable questions (source=null), the model declines
- faithfulness : LLM-as-judge — is every claim in the answer supported by the context? (1-5)

Usage: uv run python evals/run_evals.py [--k 4] [--no-judge]
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path

from ai_demo.application.dto import AskCommand
from ai_demo.application.prompts import NO_CONTEXT_ANSWER, format_context
from ai_demo.config import Settings
from ai_demo.domain.conversation.model import Message
from ai_demo.interfaces.api.deps import Container, build_container

HERE = Path(__file__).parent

JUDGE_PROMPT = """You are grading whether an ANSWER is faithful to the CONTEXT.
Score 5 if every claim in the answer is supported by the context, 1 if it is mostly unsupported.
Reply with only a single digit 1-5.

CONTEXT:
{context}

QUESTION: {question}
ANSWER: {answer}
SCORE:"""


def ask(c: Container, question: str) -> str:
    out = []
    for ev in c.ask(AskCommand(question, "rag")):
        if ev.type == "token":
            out.append(ev.data)
        elif ev.type == "error":
            raise RuntimeError(ev.data)
    return "".join(out)


def judge(c: Container, question: str, answer: str, context: str) -> int | None:
    prompt = JUDGE_PROMPT.format(context=context, question=question, answer=answer)
    reply = "".join(ch.text for ch in c.ask.model.stream([Message("user", prompt)]))
    m = re.search(r"[1-5]", reply)
    return int(m.group()) if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(data_dir=Path(tmp), top_k=args.k)
        c = build_container(settings)
        for f in sorted((HERE / "corpus").iterdir()):
            c.knowledge.ingest(f.name, f.read_bytes())

        rows = [json.loads(line) for line in (HERE / "qa.jsonl").read_text().splitlines() if line.strip()]
        hits = kw = refusals = answerable = unanswerable = 0
        faith: list[int] = []

        print(f"model={settings.chat_model} embed={settings.embed_model} k={args.k}\n")
        for row in rows:
            q, src = row["question"], row["source"]
            retrieved = c.knowledge.search(q, args.k)
            answer = ask(c, q)
            refused = NO_CONTEXT_ANSWER.lower().rstrip(".") in answer.lower()

            if src is None:
                unanswerable += 1
                refusals += refused
                status = "refused ✓" if refused else "ANSWERED ✗"
            else:
                answerable += 1
                hit = any(h.chunk.source.filename == src for h in retrieved)
                ok = all(k.lower() in answer.lower() for k in row["keywords"])
                hits += hit
                kw += ok
                status = f"hit={'✓' if hit else '✗'} keywords={'✓' if ok else '✗'}"
                if not args.no_judge and not refused:
                    score = judge(c, q, answer, format_context(retrieved))
                    if score is not None:
                        faith.append(score)
                        status += f" faith={score}"
            print(f"- {q}\n    {status}\n    → {answer.strip()[:160]!r}")

        print("\n=== summary ===")
        print(f"hit@{args.k}:       {hits}/{answerable}")
        print(f"keyword match: {kw}/{answerable}")
        print(f"refusals:      {refusals}/{unanswerable}")
        if faith:
            print(f"faithfulness:  {sum(faith) / len(faith):.2f} / 5 (n={len(faith)})")


if __name__ == "__main__":
    main()
