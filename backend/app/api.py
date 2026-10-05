"""HTTP routes. Each route is thin: validate input, call the pipeline, shape the output."""

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status

from app import store
from app.config import get_settings
from app.deps import get_conn, optional_workspace, require_workspace, searchable_workspaces
from app.embed import Embedder, get_embedder
from app.indexing import index_document
from app.ingest import ExtractionError, extract_file, extract_url
from app.llm import LLMClient, get_llm
from app.qa import ask
from app.rerank import Reranker, get_reranker
from app.schemas import (ChunkOut, DocumentOut, IngestResponse, QueryRequest, QueryResponse,
                         UrlRequest)

router = APIRouter()


@router.post("/documents", response_model=IngestResponse, status_code=status.HTTP_201_CREATED,
             summary="Upload a file (PDF, DOCX, MD, TXT, CSV)")
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
    try:
        doc = extract_file(filename, data)
    except ExtractionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    result = index_document(conn, embedder, workspace_id, doc, source_uri=filename)
    return IngestResponse(document_id=result.document_id, title=doc.title, slug=result.slug,
                          chunk_count=result.chunk_count)


@router.post("/sources/url", response_model=IngestResponse, status_code=status.HTTP_201_CREATED,
             summary="Add a web page")
def add_url(body: UrlRequest,
            workspace_id: UUID = Depends(require_workspace),
            conn: psycopg.Connection = Depends(get_conn),
            embedder: Embedder = Depends(get_embedder)):
    url = str(body.url)
    try:
        doc = extract_url(url)
    except ExtractionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    result = index_document(conn, embedder, workspace_id, doc, source_uri=url)
    return IngestResponse(document_id=result.document_id, title=doc.title, slug=result.slug,
                          chunk_count=result.chunk_count)


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
             summary="Ask a question; get a cited answer")
def query(body: QueryRequest,
          workspace_id: UUID | None = Depends(optional_workspace),
          conn: psycopg.Connection = Depends(get_conn),
          embedder: Embedder = Depends(get_embedder),
          reranker: Reranker = Depends(get_reranker),
          llm: LLMClient = Depends(get_llm)):
    result = ask(conn, embedder, reranker, llm, body.question,
                 searchable_workspaces(workspace_id), mode=body.mode)
    return QueryResponse.model_validate(result)


@router.get("/documents/{document_id}/chunks/{chunk_id}", response_model=ChunkOut,
            summary="Inspect the exact chunk behind a citation")
def get_chunk(document_id: UUID, chunk_id: str,
              workspace_id: UUID | None = Depends(optional_workspace),
              conn: psycopg.Connection = Depends(get_conn)):
    chunk = store.get_chunk(conn, searchable_workspaces(workspace_id), document_id, chunk_id)
    if chunk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chunk not found.")
    return chunk
