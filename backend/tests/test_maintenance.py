from app.indexing import index_document
from app.ingest.models import ExtractedDocument, Section
from app.maintenance import cleanup
from app.store import DEMO_WORKSPACE_ID


def make_workspace(db, fake_embedder, hours_idle):
    workspace_id = db.execute(
        "INSERT INTO workspaces (last_seen_at) VALUES (now() - make_interval(hours => %s)) RETURNING id",
        (hours_idle,),
    ).fetchone()[0]
    index_document(db, fake_embedder, workspace_id,
                   ExtractedDocument(title="Doc", source_type="md", sections=[Section(text="text")]))
    return workspace_id


def exists(db, workspace_id):
    return db.execute("SELECT count(*) FROM workspaces WHERE id = %s", (workspace_id,)).fetchone()[0] == 1


def test_cleanup_deletes_only_expired_visitor_workspaces(db, fake_embedder):
    expired = make_workspace(db, fake_embedder, hours_idle=30)
    active = make_workspace(db, fake_embedder, hours_idle=1)
    db.execute("UPDATE workspaces SET last_seen_at = now() - interval '1 year' WHERE id = %s",
               (DEMO_WORKSPACE_ID,))                     # demo looks ancient, must survive anyway

    deleted, _ = cleanup(db, ttl_hours=24)

    assert deleted >= 1
    assert not exists(db, expired) and exists(db, active) and exists(db, DEMO_WORKSPACE_ID)
    assert db.execute("SELECT count(*) FROM documents WHERE workspace_id = %s",
                      (expired,)).fetchone()[0] == 0     # its documents went with it


def test_cleanup_removes_old_usage_events(db):
    db.execute("INSERT INTO usage_events (kind, subject, created_at) VALUES "
               "('query', 'x', now() - interval '3 days'), ('query', 'x', now())")
    _, events = cleanup(db, ttl_hours=24)
    assert events >= 1
    assert db.execute("SELECT count(*) FROM usage_events WHERE subject = 'x'").fetchone()[0] == 1


def test_operational_records_are_deleted_after_their_retention(db):
    from app.maintenance import cleanup
    db.execute("INSERT INTO query_events (mode, status, created_at) VALUES ('hybrid', 'answered', now() - interval '8 days')")
    db.execute("INSERT INTO query_events (mode, status) VALUES ('hybrid', 'answered')")
    db.execute("INSERT INTO ingest_events (source_type, ok, created_at) VALUES ('pdf', true, now() - interval '8 days')")
    db.execute("INSERT INTO admin_events (kind, created_at) VALUES ('login', now() - interval '31 days')")
    db.execute("INSERT INTO admin_events (kind, created_at) VALUES ('login', now() - interval '20 days')")
    cleanup(db, ttl_hours=24)
    assert db.execute("SELECT count(*) FROM query_events").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM ingest_events").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM admin_events").fetchone()[0] == 1
