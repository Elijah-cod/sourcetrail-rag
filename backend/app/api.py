"""HTTP routes. Each route is thin: validate input, call the pipeline, shape the output."""

import json
import logging
import queue
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
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
from app.limits import CapacityExceeded, QuotaLLM, check_can_add_document
from app.llm import LLMClient, get_llm
from app.monitoring import log_query
from app.qa import Answer, ask
from app.rerank import Reranker, get_reranker
from app.schemas import (ChunkOut, DocumentOut, IngestResponse, QueryRequest, QueryResponse,
                         UrlRequest)

router = APIRouter()

# Less text than this (about a paragraph or two) usually means extraction missed the content.
LITTLE_TEXT = 600

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
    try:
        room = check_can_add_document(conn, workspace_id)
        result = index_document(conn, embedder, workspace_id, doc, source_uri=source_uri,
                                chunk_budget=room)
    except (CapacityExceeded, TooManyChunks) as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    characters = sum(len(section.text) for section in doc.sections)
    warning = None
    if characters < LITTLE_TEXT:
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
                    embedder: Embedder = Depends(get_embedder)):
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)          # read at most one byte past the limit
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                            f"File is larger than {get_settings().max_upload_mb} MB.")
    filename = file.filename or "upload"
    with ingest_slot():
        try:
            doc = extract_file(filename, data)
        except ExtractionError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        return _store(conn, embedder, workspace_id, doc, source_uri=filename)


@router.post("/sources/url", response_model=IngestResponse, status_code=status.HTTP_201_CREATED,
             summary="Add a web page", dependencies=[Depends(limit_uploads)])
def add_url(body: UrlRequest,
            workspace_id: UUID = Depends(require_workspace),
            conn: psycopg.Connection = Depends(get_conn),
            embedder: Embedder = Depends(get_embedder)):
    url = str(body.url)
    with ingest_slot():
        try:
            doc = extract_url(url)
        except ExtractionError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        return _store(conn, embedder, workspace_id, doc, source_uri=url)


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
    result = ask(conn, embedder, reranker, metered_llm, body.question,
                 searchable_workspaces(workspace_id), mode=body.mode, top_k=body.top_k)
    _log_answer(body.mode, started, result)
    return QueryResponse.model_validate(result)


def _log_answer(mode: str, started: float, result: Answer) -> None:
    log_query(mode, result.status, (time.perf_counter() - started) * 1000, result.timings,
              sources=len(result.sources), citations=len(result.citations))


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
        try:
            started = time.perf_counter()
            result = ask(conn, embedder, reranker, metered_llm, body.question, searchable_workspaces(workspace_id),
                         mode=body.mode, top_k=body.top_k,
                         progress=lambda stage, **details: lines.put({"stage": stage, **details}))
            _log_answer(body.mode, started, result)
            lines.put({"result": QueryResponse.model_validate(result).model_dump(mode="json")})
        except Exception:
            logging.exception("query stream failed")
            lines.put({"error": "Something went wrong while answering. Please try again."})
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


@router.get("/benchmarks", summary="Latest retrieval evaluation and regression benchmark results")
def benchmarks() -> dict:
    return {"retrieval": _read_results(_EVAL / "results.json"),
            "regression": _read_results(_EVAL / "regression" / "results.json")}
