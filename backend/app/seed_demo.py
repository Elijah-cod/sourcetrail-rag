"""Load the demo collection (backend/demo/sources/) into the shared demo workspace.

    uv run python -m app.seed_demo               # always re-index
    uv run python -m app.seed_demo --if-needed   # only if the demo files changed (used at startup)

Safe to re-run: it first removes everything in the demo workspace, then re-indexes
every file, so the demo always matches the files in the repository.
"""

import sys

from pathlib import Path

import psycopg

from app.config import get_settings
from app.embed import Embedder, get_embedder
from app.indexing import index_document
from app.ingest import extract_file
from app.store import DEMO_WORKSPACE_ID

DEMO_SOURCES = Path(__file__).resolve().parent.parent / "demo" / "sources"


def seed(conn: psycopg.Connection, embedder: Embedder, sources: Path = DEMO_SOURCES) -> list[tuple[str, int]]:
    """Replace the demo collection with the files in `sources`. Returns (filename, chunks) pairs."""
    files = sorted(p for p in sources.iterdir() if p.is_file() and not p.name.startswith("."))
    loaded = []
    with conn.transaction():          # all-or-nothing: a failure leaves the old demo in place
        conn.execute("DELETE FROM documents WHERE workspace_id = %s", (DEMO_WORKSPACE_ID,))
        for path in files:
            doc = extract_file(path.name, path.read_bytes())
            result = index_document(conn, embedder, DEMO_WORKSPACE_ID, doc, source_uri=path.name)
            loaded.append((path.name, result.chunk_count))
    return loaded


def up_to_date(conn: psycopg.Connection, sources: Path = DEMO_SOURCES) -> bool:
    """Whether the demo workspace already holds exactly the files in `sources` (by name)."""
    on_disk = {p.name for p in sources.iterdir() if p.is_file() and not p.name.startswith(".")}
    stored = {row[0] for row in conn.execute(
        "SELECT source_uri FROM documents WHERE workspace_id = %s", (DEMO_WORKSPACE_ID,))}
    return on_disk == stored


def main() -> None:
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        if "--if-needed" in sys.argv and up_to_date(conn):
            print("Demo collection already up to date.")
            return
        loaded = seed(conn, get_embedder())
    for name, chunks in loaded:
        print(f"{chunks:5} chunks  {name}")
    print(f"Demo collection: {len(loaded)} documents, {sum(c for _, c in loaded)} chunks.")


if __name__ == "__main__":
    main()
