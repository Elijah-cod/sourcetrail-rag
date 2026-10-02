"""Database access: one shared connection pool for the whole app."""

from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: ConnectionPool | None = None


def open_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        # open=True with wait=False: start connecting in the background so the
        # app can still boot (and report "database: down") if Postgres is offline.
        _pool = ConnectionPool(get_settings().database_url, min_size=1, max_size=5, open=True)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def ping() -> bool:
    """Return True if we can run a trivial query against Postgres."""
    try:
        with open_pool().connection(timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
