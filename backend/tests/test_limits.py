from types import SimpleNamespace

import pytest

from app import limits
from app.config import get_settings
from app.limits import QuotaLLM, RateLimited, check_rate, client_ip, client_key
from app.llm import LLMUnavailable


def fake_request(host="203.0.113.7", forwarded=None):
    headers = {"x-forwarded-for": forwarded} if forwarded else {}
    return SimpleNamespace(client=SimpleNamespace(host=host), headers=headers)


def test_check_rate_allows_up_to_the_limit(db):
    for _ in range(3):
        check_rate(db, "query", "client-a", limit=3, window_seconds=60)
    with pytest.raises(RateLimited) as caught:
        check_rate(db, "query", "client-a", limit=3, window_seconds=60)
    assert 1 <= caught.value.retry_after <= 60


def test_limits_are_per_client_and_per_kind(db):
    check_rate(db, "query", "client-a", limit=1, window_seconds=60)
    check_rate(db, "query", "client-b", limit=1, window_seconds=60)    # different client: fine
    check_rate(db, "upload", "client-a", limit=1, window_seconds=60)   # different kind: fine


def test_old_events_fall_out_of_the_window(db):
    db.execute("INSERT INTO usage_events (kind, subject, created_at) "
               "VALUES ('query', 'client-c', now() - interval '2 minutes')")
    check_rate(db, "query", "client-c", limit=1, window_seconds=60)      # the old one doesn't count


def test_client_key_is_a_hash_not_the_ip():
    key = client_key(fake_request("203.0.113.7"))
    assert "203.0.113.7" not in key and len(key) == 32
    assert key == client_key(fake_request("203.0.113.7"))                # stable
    assert key != client_key(fake_request("198.51.100.1"))


def test_forwarded_for_only_trusted_when_enabled(monkeypatch):
    request = fake_request(host="10.0.0.1", forwarded="6.6.6.6, 203.0.113.7")
    monkeypatch.setattr(get_settings(), "trust_forwarded_for", False)
    assert client_ip(request) == "10.0.0.1"                 # ignore a header anyone could fake
    monkeypatch.setattr(get_settings(), "trust_forwarded_for", True)
    assert client_ip(request) == "203.0.113.7"              # last hop = added by our proxy


def test_workspace_usage_counts_documents_and_chunks(db, fake_embedder, workspace_id):
    from app.indexing import index_document
    from app.ingest.models import ExtractedDocument, Section

    index_document(db, fake_embedder, workspace_id, ExtractedDocument(
        title="Doc", source_type="md", sections=[Section(text="a"), Section(text="b")]))
    assert limits.workspace_usage(db, workspace_id) == limits.Usage(documents=1, chunks=2)


def test_quota_llm_stops_at_the_daily_cap(db):
    class Inner:
        calls = 0

        def complete(self, messages):
            Inner.calls += 1
            return "ok"

    llm = QuotaLLM(Inner(), db, per_day=2)
    assert llm.complete([]) == "ok" and llm.complete([]) == "ok"
    with pytest.raises(LLMUnavailable, match="daily"):
        llm.complete([])
    assert Inner.calls == 2                                   # the real LLM was not called a 3rd time
