"""Guardrail policies. Pure rules, no IO."""

from __future__ import annotations

import re
from dataclasses import dataclass

_INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (the )?(system|previous) (prompt|instructions)",
    r"you are now (?!going)",
    r"reveal (your|the) (system )?prompt",
]


class GuardrailViolation(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class InputPolicy:
    max_chars: int = 4000

    def check(self, question: str) -> list[str]:
        """Raise on hard violations; return soft warnings."""
        q = question.strip()
        if not q:
            raise GuardrailViolation("question is empty")
        if len(q) > self.max_chars:
            raise GuardrailViolation(f"question longer than {self.max_chars} characters")
        warnings: list[str] = []
        lowered = q.lower()
        if any(re.search(p, lowered) for p in _INJECTION_PATTERNS):
            warnings.append("possible prompt-injection attempt detected")
        return warnings


@dataclass(frozen=True, slots=True)
class GroundingPolicy:
    """Answer only when retrieval found something relevant enough."""

    min_score: float = 0.3

    def is_grounded(self, scores: list[float]) -> bool:
        return any(s >= self.min_score for s in scores)


def cited_numbers(answer: str) -> set[int]:
    return {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
