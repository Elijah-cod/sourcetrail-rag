"""Ingestion: turn sources (files, web pages) into ExtractedDocument objects."""

from app.ingest.files import extract_file
from app.ingest.models import ExtractedDocument, ExtractionError, Section

__all__ = ["extract_file", "ExtractedDocument", "ExtractionError", "Section"]
