# One image for the whole app: FastAPI serves the API under /api and the static
# Next.js export at "/". Build from the repository root:  docker build -t sourcetrail .

# 1. The frontend, exported as plain HTML/CSS/JS (frontend/out).
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. The backend, with the embedding and reranker models baked in, so the first
#    request doesn't wait for a ~150 MB download.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
ENV PATH=/app/backend/.venv/bin:$PATH
RUN python -c "from app.embed import get_embedder; from app.rerank import get_reranker; get_embedder(); get_reranker()"
COPY --from=frontend /app/frontend/out /app/frontend/out

# Run as an ordinary user (uid 1000, as Hugging Face Spaces expects), never downloading
# models at runtime: they are already in .cache/models.
RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app
ENV HF_HUB_OFFLINE=1 PRELOAD_MODELS=true

# At start: apply new migrations, index the demo collection if its files changed, serve.
EXPOSE 8000
CMD ["sh", "-c", "python -m app.migrate && python -m app.seed_demo --if-needed && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
