"""The shapes of API requests and responses.

Pydantic checks incoming data (wrong type or too long -> automatic 422 error) and these
classes also generate the interactive docs at /docs.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Out(BaseModel):
    # Allows building responses straight from our dataclasses (SearchHit, Citation, ...).
    model_config = ConfigDict(from_attributes=True)


# ---------- requests ----------

class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000, examples=["Why did revenue decline in 2024?"])
    mode: Literal["vector", "keyword", "hybrid", "hybrid_rerank"] = "hybrid_rerank"


class UrlRequest(BaseModel):
    url: HttpUrl = Field(examples=["https://fastapi.tiangolo.com/tutorial/first-steps/"])


# ---------- responses ----------

class DocumentOut(Out):
    id: UUID
    title: str
    source_type: str
    source_uri: str | None
    published_year: int | None
    created_at: datetime
    is_demo: bool
    chunk_count: int


class IngestResponse(Out):
    document_id: UUID
    title: str
    slug: str
    chunk_count: int


class CitationOut(Out):
    n: int
    chunk_id: str
    document_id: UUID
    document_title: str
    source_type: str
    source_uri: str | None
    page: int | None
    section: str | None
    snippet: str


class SourceOut(Out):
    chunk_id: str
    document_id: UUID
    document_title: str
    page: int | None
    section: str | None
    score: float
    ranks: dict[str, int]
    text: str


class QueryResponse(Out):
    status: Literal["answered", "not_found", "llm_unavailable"]
    answer: str
    citations: list[CitationOut]
    sources: list[SourceOut]


class ChunkOut(Out):
    chunk_id: str
    document_id: UUID
    document_title: str
    source_type: str
    source_uri: str | None
    ord: int
    page: int | None
    section: str | None
    text: str
