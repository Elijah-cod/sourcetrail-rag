import psycopg
import pytest

from app.config import get_settings
from app.migrate import apply_migrations, migration_files


def test_migration_files_are_numbered_and_sorted():
    names = [p.name for p in migration_files()]
    assert names, "expected at least one migration file"
    assert names == sorted(names)
    assert all(name[:3].isdigit() for name in names)


def _connect_or_skip():
    try:
        return psycopg.connect(get_settings().database_url, autocommit=True, connect_timeout=2)
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable — run `docker compose up -d db` to include this test")


@pytest.mark.integration
def test_migrations_create_schema_and_are_idempotent():
    with _connect_or_skip() as conn:
        apply_migrations(conn)
        # Running again must do nothing (each file is applied only once).
        assert apply_migrations(conn) == []

        tables = {r[0] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )}
        assert {"workspaces", "documents", "chunks", "schema_migrations"} <= tables

        assert conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'").fetchone()
        demo = conn.execute("SELECT is_demo FROM workspaces WHERE id = '00000000-0000-0000-0000-000000000001'").fetchone()
        assert demo == (True,)
