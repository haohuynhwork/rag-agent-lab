"""Domain service: split text into overlapping chunks on natural boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkingPolicy:
    max_chars: int = 1000
    overlap: int = 150

    def __post_init__(self) -> None:
        if self.max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if not 0 <= self.overlap < self.max_chars:
            raise ValueError("overlap must be in [0, max_chars)")

    def split(self, text: str) -> list[str]:
        text = re.sub(r"[ \t]+", " ", text).strip()
        if not text:
            return []
        # Paragraphs first, then sentences for oversized paragraphs.
        units: list[str] = []
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if not para:
                continue
            if len(para) <= self.max_chars:
                units.append(para)
            else:
                units.extend(self._split_long(para))

        chunks: list[str] = []
        current = ""
        for unit in units:
            candidate = f"{current}\n\n{unit}" if current else unit
            if len(candidate) <= self.max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
                tail = current[-self.overlap :] if self.overlap else ""
                current = f"{tail} {unit}".strip() if tail else unit
                if len(current) > self.max_chars:
                    current = unit
            else:
                current = unit
        if current:
            chunks.append(current)
        return chunks

    def _split_long(self, para: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", para)
        out: list[str] = []
        for s in sentences:
            while len(s) > self.max_chars:  # hard wrap a pathological sentence
                out.append(s[: self.max_chars])
                s = s[self.max_chars :]
            if s:
                out.append(s)
        return out
