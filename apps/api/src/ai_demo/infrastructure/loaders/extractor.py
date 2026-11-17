"""TextExtractor adapter: .pdf via pypdf, .md/.txt as UTF-8."""

from __future__ import annotations

import io
from pathlib import PurePath

from pypdf import PdfReader

SUPPORTED = {".pdf", ".md", ".markdown", ".txt"}


class UnsupportedFileType(ValueError):
    pass


class FileTextExtractor:
    def extract(self, filename: str, data: bytes) -> str:
        ext = PurePath(filename).suffix.lower()
        if ext not in SUPPORTED:
            raise UnsupportedFileType(f"unsupported file type {ext or '(none)'}; use {sorted(SUPPORTED)}")
        if ext == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return data.decode("utf-8", errors="replace")
