"""HTTP routes. Each route is thin: validate input, call the pipeline, shape the output."""

import json
import logging
import queue
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app import store
from app.config import get_settings
from app.deps import (get_conn, get_usage_conn, limit_queries, limit_uploads, optional_workspace,
                      require_workspace, searchable_workspaces)
from app.embed import Embedder, get_embedder
from app.indexing import TooManyChunks, index_document
from app.ingest import ExtractedDocument, ExtractionError, extract_file, extract_url
from app.limits import CapacityExceeded, QuotaLLM, RateLimited, check_can_add_document
from app.llm import LLMClient, get_llm
from app.monitoring import log_query
from app.qa import Answer, ask
from app.rerank import Reranker, get_reranker
from app.schemas import (ChunkOut, DocumentOut, IngestResponse, QueryRequest, QueryResponse,
                         UrlRequest)
from app.telemetry import answering, record_ingest, record_query

router = APIRouter()

# Less text than this (about a paragraph or two) from a PDF or a web page usually means the text
# is in images or loaded by JavaScript. Text, Markdown, CSV and Word files are read in full, so a
# short one is simply short: warning about every small file made successful uploads look broken.
LITTLE_TEXT = 600
MAY_BE_INCOMPLETE = ("pdf", "url")

# Added to a title another document of the workspace already has: two uploads both called
# "source test" (a .txt and a .csv) couldn't be told apart in the sources.
TYPE_NAMES = {"pdf": "PDF", "docx": "Word", "md": "Markdown", "txt": "text", "csv": "CSV", "url": "web page"}

# Reading and embedding a document takes a CPU for seconds; with every visitor uploading at once
# answers would stall for everyone. Beyond this many at a time, uploads are turned away politely.
INGEST_SLOTS = 2
_ingest_slots = threading.BoundedSemaphore(INGEST_SLOTS)


@contextmanager
def ingest_slot():
    if not _ingest_slots.acquire(timeout=5):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The server is busy adding other documents. Please try again in a minute.")
    try:
        yield
    finally:
        _ingest_slots.release()


def _store(conn: psycopg.Connection, embedder: Embedder, workspace_id: UUID,
           doc: ExtractedDocument, source_uri: str) -> IngestResponse:
    """Shared by both ingest routes: enforce the workspace's caps, then index."""
    if conn.execute("SELECT 1 FROM documents WHERE workspace_id = %s AND title = %s",
                    (workspace_id, doc.title)).fetchone():
        doc = replace(doc, title=f"{doc.title} ({TYPE_NAMES.get(doc.source_type, doc.source_type)})")
    try:
        room = check_can_add_document(conn, workspace_id)
        result = index_document(conn, embedder, workspace_id, doc, source_uri=source_uri,
                                chunk_budget=room)
    except (CapacityExceeded, TooManyChunks) as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    characters = sum(len(section.text) for section in doc.sections)
    warning = None
    if characters < LITTLE_TEXT and doc.source_type in MAY_BE_INCOMPLETE:
        where = "this page" if doc.source_type == "url" else "this file"
        warning = (f"Only {characters} characters of text were read from {where}. If you expected more, its text "
                   "may be in images or loaded by JavaScript; questions about the rest won't find anything.")
    return IngestResponse(document_id=result.document_id, title=doc.title, slug=result.slug,
                          chunk_count=result.chunk_count, characters=characters, warning=warning)


@router.post("/documents", response_model=IngestResponse, status_code=status.HTTP_201_CREATED,
             summary="Upload a file (PDF, DOCX, MD, TXT, CSV)",
             dependencies=[Depends(limit_uploads)])
def upload_document(file: UploadFile,
                    workspace_id: UUID = Depends(require_workspace),
                    conn: psycopg.Connection = Depends(get_conn),
                    embedder: Embedder = Depends(get_embedder),
                    usage: psycopg.Connection = Depends(get_usage_conn)):
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)          # read at most one byte past the limit
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                            f"File is larger than {get_settings().max_upload_mb} MB.")
    filename = file.filename or "upload"
    with ingest_slot(), _recorded(usage, Path(filename).suffix.lstrip(".").lower() or "unknown") as outcome:
        try:
            doc = extract_file(filename, data)
        except ExtractionError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        outcome["result"] = _store(conn, embedder, workspace_id, doc, source_uri=filename)
        return outcome["result"]


@router.post("/sources/url", response_model=IngestResponse, status_code=status.HTTP_201_CREATED,
             summary="Add a web page", dependencies=[Depends(limit_uploads)])
def add_url(body: UrlRequest,
            workspace_id: UUID = Depends(require_workspace),
            conn: psycopg.Connection = Depends(get_conn),
            embedder: Embedder = Depends(get_embedder),
            usage: psycopg.Connection = Depends(get_usage_conn)):
    url = str(body.url)
    with ingest_slot(), _recorded(usage, "url") as outcome:
        try:
            doc = extract_url(url)
        except ExtractionError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        outcome["result"] = _store(conn, embedder, workspace_id, doc, source_uri=url)
        return outcome["result"]


@contextmanager
def _recorded(usage: psycopg.Connection, source_type: str) -> Iterator[dict]:
    """Time an ingestion and record how it went for the admin area (no document content)."""
    started, outcome = time.perf_counter(), {}
    elapsed = lambda: (time.perf_counter() - started) * 1000   # noqa: E731
    try:
        yield outcome
    except HTTPException as exc:
        record_ingest(usage, source_type, False, elapsed(), error=f"{exc.status_code}: {str(exc.detail)[:300]}")
        raise
    except Exception:
        record_ingest(usage, source_type, False, elapsed(), error="server error")
        raise
    result: IngestResponse = outcome["result"]
    record_ingest(usage, source_type, True, elapsed(), chunks=result.chunk_count, characters=result.characters,
                  warning=result.warning, document_id=result.document_id)


@router.get("/documents", response_model=list[DocumentOut],
            summary="List your documents and the demo collection")
def list_documents(workspace_id: UUID | None = Depends(optional_workspace),
                   conn: psycopg.Connection = Depends(get_conn)):
    return store.list_documents(conn, searchable_workspaces(workspace_id))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete one of your documents")
def delete_document(document_id: UUID,
                    workspace_id: UUID | None = Depends(optional_workspace),
                    conn: psycopg.Connection = Depends(get_conn)):
    # Demo documents and other visitors' documents are simply "not found" for you.
    if workspace_id is None or not store.delete_document(conn, workspace_id, document_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/query", response_model=QueryResponse,
             summary="Ask a question; get a cited answer", dependencies=[Depends(limit_queries)])
def query(body: QueryRequest,
          workspace_id: UUID | None = Depends(optional_workspace),
          conn: psycopg.Connection = Depends(get_conn),
          embedder: Embedder = Depends(get_embedder),
          reranker: Reranker = Depends(get_reranker),
          llm: LLMClient = Depends(get_llm),
          usage: psycopg.Connection = Depends(get_usage_conn)):
    metered_llm = QuotaLLM(llm, usage, get_settings().llm_calls_per_day)   # counts toward the daily cap
    started = time.perf_counter()
    try:
        with answering():
            result = ask(conn, embedder, reranker, metered_llm, body.question,
                         searchable_workspaces(workspace_id), mode=body.mode, top_k=body.top_k)
    except Exception as exc:
        _record_failure(usage, body.mode, started, exc)
        raise
    _log_answer(usage, body.mode, started, result)
    return QueryResponse.model_validate(result)


def _log_answer(usage: psycopg.Connection, mode: str, started: float, result: Answer) -> None:
    """Timings go to the logs and the admin area only; visitors never receive them."""
    total = (time.perf_counter() - started) * 1000
    log_query(mode, result.status, total, result.timings, sources=len(result.sources),
              citations=len(result.citations))
    record_query(usage, mode, result.status, total, result.timings, parts=result.parts, missing=result.missing,
                 sources=len(result.sources), citations=len(result.citations))


def _record_failure(usage: psycopg.Connection, mode: str, started: float, exc: Exception) -> None:
    category = "rate limited" if isinstance(exc, RateLimited) else type(exc).__name__
    record_query(usage, mode, "error", (time.perf_counter() - started) * 1000, {}, error=category)


@router.post("/query/stream", summary="Ask a question; get progress lines, then the cited answer",
             dependencies=[Depends(limit_queries)])
def query_stream(body: QueryRequest,
                 workspace_id: UUID | None = Depends(optional_workspace),
                 conn: psycopg.Connection = Depends(get_conn),
                 embedder: Embedder = Depends(get_embedder),
                 reranker: Reranker = Depends(get_reranker),
                 llm: LLMClient = Depends(get_llm),
                 usage: psycopg.Connection = Depends(get_usage_conn)) -> StreamingResponse:
    """Same answer as POST /query, as newline-delimited JSON: a line per stage as it starts,
    e.g. {"stage": "parts", "count": 3}, then {"result": {...}} (or {"error": "..."}).

    The answer itself isn't streamed word by word: it is checked (requirement words, figures,
    citations) and sometimes rewritten after the LLM replies, so early text could change."""
    metered_llm = QuotaLLM(llm, usage, get_settings().llm_calls_per_day)
    lines: queue.Queue[dict | None] = queue.Queue()

    def run() -> None:
        started = time.perf_counter()
        try:
            with answering():
                result = ask(conn, embedder, reranker, metered_llm, body.question,
                             searchable_workspaces(workspace_id), mode=body.mode, top_k=body.top_k,
                             progress=lambda stage, **details: lines.put({"stage": stage, **details}))
            _log_answer(usage, body.mode, started, result)
            lines.put({"result": QueryResponse.model_validate(result).model_dump(mode="json")})
        except Exception as exc:
            logging.exception("query stream failed")
            _record_failure(usage, body.mode, started, exc)
            lines.put({"error": "We couldn't complete that answer. Try again."})
        finally:
            lines.put(None)

    def stream() -> Iterator[str]:
        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        try:
            while (line := lines.get()) is not None:
                yield json.dumps(line) + "\n"
        finally:
            worker.join()        # even if the browser left: ask() is still using the connections

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@router.get("/documents/{document_id}/chunks/{chunk_id}", response_model=ChunkOut,
            summary="Inspect the exact chunk behind a citation")
def get_chunk(document_id: UUID, chunk_id: str,
              workspace_id: UUID | None = Depends(optional_workspace),
              conn: psycopg.Connection = Depends(get_conn)):
    chunk = store.get_chunk(conn, searchable_workspaces(workspace_id), document_id, chunk_id)
    if chunk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chunk not found.")
    return chunk


# Written by `python -m eval.run_eval` and `python -m eval.regression.run_regression`.
_EVAL = Path(__file__).resolve().parent.parent / "eval"


def _read_results(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None                     # not run yet (or not shipped with this deployment)


def benchmark_results() -> dict:
    """Latest retrieval evaluation and regression benchmark (shown in the admin area only)."""
    return {"retrieval": _read_results(_EVAL / "results.json"),
            "regression": _read_results(_EVAL / "regression" / "results.json")}
