"""Housekeeping: delete expired visitor data and old usage events.

Runs automatically every hour while the server is up (see main.py), or by hand:
    uv run python -m app.maintenance
"""

import psycopg

from app.config import get_settings


def cleanup(conn: psycopg.Connection, ttl_hours: int) -> tuple[int, int]:
    """Returns (workspaces deleted, usage events deleted)."""
    with conn.transaction():
        # Deleting a workspace deletes its documents and chunks too (ON DELETE CASCADE).
        # The demo workspace is never touched.
        workspaces = conn.execute(
            """
            DELETE FROM workspaces
            WHERE NOT is_demo AND last_seen_at < now() - make_interval(hours => %s)
            """,
            (ttl_hours,),
        ).rowcount
        # Rate limits only look back 24 h; anything older than 2 days is just clutter.
        events = conn.execute(
            "DELETE FROM usage_events WHERE created_at < now() - interval '2 days'"
        ).rowcount
    return workspaces, events


def main() -> None:
    settings = get_settings()
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        workspaces, events = cleanup(conn, settings.workspace_ttl_hours)
    print(f"Deleted {workspaces} expired workspace(s) and {events} old usage event(s).")


if __name__ == "__main__":
    main()
