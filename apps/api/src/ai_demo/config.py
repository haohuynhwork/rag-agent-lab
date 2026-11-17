from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/ai_demo/config.py -> apps/
APPS_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """All settings can be overridden with AI_DEMO_* env vars or a .env file."""

    model_config = SettingsConfigDict(env_prefix="AI_DEMO_", env_file=".env", extra="ignore")

    ollama_host: str = "http://localhost:11434"
    chat_model: str = "gemma4:e4b"
    embed_model: str = "nomic-embed-text"
    temperature: float = 0.2

    data_dir: Path = Path("data")
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4
    min_relevance: float = 0.3
    max_question_chars: int = 4000
    agent_max_steps: int = 5
    max_upload_mb: int = 20

    cors_origins: list[str] = ["http://localhost:5173"]
    web_dist: Path = APPS_DIR / "web" / "dist"
