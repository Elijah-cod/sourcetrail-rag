import socket

import pytest

from app.ingest import ExtractionError
from app.ingest import web

ARTICLE = """
<html><head><title>Ignored tab title</title><meta name="date" content="2024-03-01"></head>
<body>
  <nav>Home | About | Contact</nav>
  <article>
    <h1>Postgres Full-Text Search</h1>
    <p>{intro}</p>
    <h2>Ranking</h2>
    <p>{ranking}</p>
  </article>
  <footer>Copyright footer</footer>
</body></html>
""".format(
    intro="Full-text search finds documents that contain the words you typed. " * 4,
    ranking="ts_rank_cd scores documents by how often and how close the words appear. " * 4,
)


def fake_dns(ip):
    """Pretend every hostname resolves to `ip`, so tests never touch the network."""
    return lambda host, port, *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


@pytest.mark.parametrize("url", ["ftp://example.com/file", "file:///etc/passwd", "javascript:alert(1)", "http://"])
def test_rejects_non_http_urls(url):
    with pytest.raises(ExtractionError, match="Only http"):
        web.validate_url(url)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.10", "169.254.169.254", "::1"])
def test_rejects_private_and_local_addresses(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", fake_dns(ip))
    with pytest.raises(ExtractionError, match="private or local"):
        web.validate_url("http://sneaky.example.com/")


def test_accepts_public_address(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", fake_dns("93.184.216.34"))
    web.validate_url("https://example.com/page")   # no exception


def test_extract_html_keeps_article_and_headings_drops_navigation():
    doc = web.extract_html("https://example.com/fts", ARTICLE)
    assert doc.source_type == "url"
    assert doc.published_year == 2024
    assert [s.heading for s in doc.sections] == ["Postgres Full-Text Search", "Ranking"]
    all_text = " ".join(s.text for s in doc.sections)
    assert "ts_rank_cd" in all_text
    assert "Home | About" not in all_text and "Copyright footer" not in all_text


def test_extract_html_with_no_content_is_rejected():
    with pytest.raises(ExtractionError, match="readable"):
        web.extract_html("https://example.com/empty", "<html><body><nav>menu</nav></body></html>")


def test_extract_url_wires_fetch_and_extract(monkeypatch):
    monkeypatch.setattr(web, "fetch_html", lambda url: ("https://example.com/final", ARTICLE))
    doc = web.extract_url("  https://example.com/start  ")
    assert doc.title == "Postgres Full-Text Search"
