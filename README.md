# sourcetrail-rag
Multi-source RAG knowledge base with hybrid search (pgvector + full-text), RRF fusion, cross-encoder reranking, and verifiable citations.

## Project layout

- `backend/` — FastAPI service (Python, uv)
- `frontend/` — chat UI
- `docs/` — design spec and architecture diagram
- `docker-compose.yml` — local Postgres + pgvector

## Local development (backend)

Requirements: [uv](https://docs.astral.sh/uv/) and Docker.

```bash
docker compose up -d db          # Postgres 17 + pgvector on localhost:5432 (run from repo root)
cd backend
cp .env.example .env
uv sync                          # create .venv and install dependencies
uv run python -m app.migrate     # create/update database tables
uv run uvicorn app.main:app --reload
# open http://localhost:8000/health  and  http://localhost:8000/docs
uv run pytest                    # run tests
```

Design spec: [docs/superpowers/specs/2026-10-02-sourcetrail-rag-design.md](docs/superpowers/specs/2026-10-02-sourcetrail-rag-design.md)
