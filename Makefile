.PHONY: install dev api web build test lint evals gen-api

install:            ## install backend + frontend deps
	uv sync --directory apps/api
	pnpm --dir apps/web install

dev:                ## run API (:8000) and web (:5173) together
	$(MAKE) -j2 api web

api:
	uv run --directory apps/api ai-demo

web:
	pnpm --dir apps/web dev

build:              ## build the UI; FastAPI then serves it on :8000
	pnpm --dir apps/web build

test:
	uv run --directory apps/api pytest -q

lint:
	uv run --directory apps/api ruff check
	uv run --directory apps/api mypy
	pnpm --dir apps/web lint

evals:              ## needs Ollama running
	uv run --directory apps/api python evals/run_evals.py

gen-api:            ## regenerate TS types from FastAPI's OpenAPI schema
	pnpm --dir apps/web gen:api
