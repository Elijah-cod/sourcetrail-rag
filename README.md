# sourcetrail-rag
Multi-source RAG knowledge base with hybrid search (pgvector + full-text), RRF fusion, cross-encoder reranking, and verifiable citations.

## Local development

Requirements: [uv](https://docs.astral.sh/uv/) and Docker.

```bash
cp .env.example .env
docker compose up -d db          # Postgres 17 + pgvector on localhost:5432
uv sync                          # create .venv and install dependencies
uv run uvicorn app.main:app --reload
# open http://localhost:8000/health  and  http://localhost:8000/docs
uv run pytest                    # run tests
```

Design spec: [docs/superpowers/specs/2026-10-02-sourcetrail-rag-design.md](docs/superpowers/specs/2026-10-02-sourcetrail-rag-design.md)
