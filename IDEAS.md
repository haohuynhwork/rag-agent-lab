# Follow-up projects (separate repos)

Same stack and layout (`apps/api` + `apps/web` + Makefile): **uv + FastAPI (DDD) + React/TanStack + Ollama**. Each one covers a different part of the [roadmap.sh AI Engineer](https://roadmap.sh/ai-engineer) path.

## ✅ 0. Docs RAG + agent: built in this repo
Chat with your own docs in plain, RAG (with citations) and agent (tool-calling) modes.
- **Roadmap:** LLM APIs, prompt engineering, embeddings, vector DB, RAG, agents/tools, streaming, guardrails, evals
- **Where:** `apps/api` + `apps/web` (see [README](README.md))

## 1. Multimodal assistant
Upload images, audio or PDFs, then extract structured data, transcribe, and answer questions.
- **Roadmap:** multimodal models (vision), speech-to-text, structured outputs (JSON schema), moderation
- **Ollama:** a vision-capable model (e.g. `gemma4`, `llava`) with `format=<json schema>`. Whisper runs locally via `faster-whisper`.
- **Domain:** `Asset` aggregate → `Extraction` (typed fields + confidence); a review queue for low-confidence fields

## 2. Multi-agent research tool
Give it a question; agents plan, search, read sources, and write a cited report.
- **Roadmap:** agents, planning, multi-agent orchestration, MCP, web search tools, evals for agents
- **Shape:** planner → N researcher agents (parallel) → writer → critic loop. Expose the tools over an MCP server.
- **Domain:** `ResearchTask` aggregate with `Finding`s; every claim keeps a link to its `Source`

## 3. Roadmap tutor
An interactive app that teaches each roadmap node with live mini-demos.
- **Roadmap:** prompt engineering, temperature/top-p, tokenization, embeddings, RAG vs no-RAG, fine-tuning concepts
- **Demos:** prompt playground with side-by-side sampling settings, 2-D embedding projection (UMAP), token counter, a RAG on/off toggle
- **Domain:** `Lesson` → `Exercise` → `Attempt`, with progress tracking and LLM-graded answers
