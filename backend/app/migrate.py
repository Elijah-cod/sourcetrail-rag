"""Apply SQL migration files from backend/migrations/ in order, each exactly once.

Run it with:  uv run python -m app.migrate
"""

from pathlib import Path

import psycopg

from app.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def migration_files(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """All .sql files, sorted by name (001_..., 002_..., ...)."""
    return sorted(directory.glob("*.sql"))


def apply_migrations(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply any migrations not yet recorded in schema_migrations. Returns their names."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename   text PRIMARY KEY,
            applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    already_applied = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}

    newly_applied = []
    for path in migration_files(directory):
        if path.name in already_applied:
            continue
        # One transaction per file: either the whole file applies, or none of it does.
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
        newly_applied.append(path.name)
    return newly_applied


def main() -> None:
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        applied = apply_migrations(conn)
    if applied:
        print("Applied:", ", ".join(applied))
    else:
        print("Database already up to date.")


if __name__ == "__main__":
    main()
