# ai-demo — chat with your docs (RAG + agent), fully local

Upload PDFs, Markdown or text, then ask questions in three modes so you can compare them:

| Mode | What happens |
|---|---|
| **Plain** | The LLM answers from its own knowledge |
| **RAG** | Embed the question → top-k chunks from Chroma → answer **only** from them, with `[n]` citations |
| **Agent** | The LLM decides when to call `search_docs`, `list_docs` and `calculator`; the tool trace is shown in the UI |

It covers these parts of [roadmap.sh/ai-engineer](https://roadmap.sh/ai-engineer): LLM APIs, prompt engineering, embeddings, vector DBs, RAG, agents and tool calling, streaming, guardrails, and evals.

## Stack
- **Backend:** Python 3.12, [uv](https://docs.astral.sh/uv/), FastAPI (SSE streaming), Chroma (embedded), SQLite, Ollama
- **Frontend:** React 19, TanStack Router (file-based), TanStack Query, Tailwind v4, Vite, pnpm
- **Quality:** pytest, ruff, mypy `--strict`, oxlint, an eval harness

## Layout
```
ai-demo/
  apps/
    api/      Python backend: uv project (pyproject.toml, src/ai_demo, tests, evals)
    web/      React frontend: pnpm project
  Makefile    one entry point for both
```

## Run it
```bash
ollama pull nomic-embed-text          # embeddings
ollama pull gemma4:e4b                # chat model (any tool-capable model works)

make install
make dev                              # API :8000 + UI http://localhost:5173 (proxies /api)
```
Production-style: `make build && make api`. FastAPI serves `apps/web/dist` at http://localhost:8000.

Settings (env or `apps/api/.env`, prefix `AI_DEMO_`): `CHAT_MODEL`, `EMBED_MODEL`, `OLLAMA_HOST`, `TOP_K`, `MIN_RELEVANCE`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `AGENT_MAX_STEPS`, … see `apps/api/src/ai_demo/config.py`.

## Backend architecture (DDD, dependencies point inward)
```
apps/api/src/ai_demo/
  domain/            pure Python: aggregates, value objects, policies, ports (Protocols)
    documents/       Knowledge context — Document, Chunk, ChunkingPolicy
    conversation/    Assistant context — Message, Citation, ToolCall, guardrail policies
  application/       use cases: KnowledgeService (ingest/search), AskQuestion (plain|rag|agent), AgentLoop, prompts
  infrastructure/    driven adapters: Ollama chat + embedder, Chroma index, SQLite repo, PDF/MD/TXT extractor
  interfaces/api/    driving adapter: FastAPI routes + deps.py (composition root)
apps/web/src/
  routes/            TanStack file routes: /chat?mode=…, /documents
  features/          chat (SSE stream → messages, citations, trace), documents (query/mutations)
  lib/api-types.ts   generated from FastAPI's OpenAPI (`make gen-api`)
```
The domain imports nothing from the outer layers, and the application layer imports only the domain. FastAPI is one driving adapter; a CLI or worker would sit beside it in `interfaces/`. Tests swap in fakes for every port (`apps/api/tests/fakes.py`), so the unit tests never need Ollama.

## Guardrails
- Input policy: length cap; prompt-injection phrases raise a warning event
- Grounding policy: if no chunk scores ≥ `MIN_RELEVANCE`, RAG refuses without calling the LLM
- The prompts treat retrieved and tool text as data, not instructions
- Citation check: the app warns if the answer cites a passage number it was never given
- Calculator runs on an AST whitelist (no `eval`); the agent has a step limit

## Checks
```bash
make test     # 37 tests (unit with fakes + API integration with real Chroma/SQLite)
make lint     # ruff + mypy --strict + oxlint
make build    # vite build + tsc
make evals    # needs Ollama; hit@k, keyword match, refusals, LLM-judge faithfulness
```

See [IDEAS.md](IDEAS.md) for the follow-up projects.
