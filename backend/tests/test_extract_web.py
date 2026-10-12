import socket
from pathlib import Path

import pytest

from app.ingest import ExtractionError
from app.ingest import web

FIXTURES = Path(__file__).parent / "fixtures"

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


# ---------- extraction quality (SourceTrail test report, 8 Oct 2026) ----------
# PEP 20 was "added" with only its title and metadata indexed: its aphorisms sit in one <pre>
# block that the article extractor dropped. tests/fixtures/pep20_like.html mirrors that page.

PEP20 = (FIXTURES / "pep20_like.html").read_text(encoding="utf-8")
PEP20_URL = "https://peps.python.org/pep-0020/"
# What the extractor kept of the real page: title + the metadata field list, nothing else.
PEP20_METADATA_ONLY = """# PEP 20 – The Zen of Python

- Author:
- Tim Peters \\<tim.peters at gmail.com>
- Status:
- Active
- Type:
- Informational
- Created:
- 19-Aug-2004

## Table of Contents
"""


def all_text(doc):
    return "\n".join(s.text for s in doc.sections)


def test_pre_block_content_is_indexed():
    doc = web.extract_html(PEP20_URL, PEP20)
    text = all_text(doc)
    assert "Beautiful is better than ugly." in text
    assert "Namespaces are one honking great idea" in text
    assert "The Zen of Python" in [s.heading for s in doc.sections]
    assert doc.diagnostics["dropped_elements"] == []


def test_dropped_pre_block_falls_back_to_main_content(monkeypatch):
    monkeypatch.setattr(web.trafilatura, "extract", lambda *a, **k: PEP20_METADATA_ONLY)
    doc = web.extract_html(PEP20_URL, PEP20)
    text = all_text(doc)
    assert "Errors should never pass silently." in text
    assert "only 19 of which have been written down" in text          # the abstract paragraph too
    assert "Author: Tim Peters" in text                                 # metadata kept, as a list
    assert "Page Source (GitHub)" not in text                           # the sidebar <nav> isn't
    assert doc.diagnostics["extractor"] == "main-content fallback"
    assert doc.diagnostics["dropped_elements"] == ["pre"]
    assert doc.diagnostics["retained_chars"] > 1000


def test_page_with_only_title_and_metadata_is_rejected():
    html = """<html><head><title>PEP 9999 – Placeholder</title></head><body><article>
      <h1>PEP 9999 – Placeholder</h1>
      <dl><dt>Author:</dt><dd>Jane Doe &lt;jane at example.com&gt;</dd><dt>Status:</dt><dd>Draft</dd>
          <dt>Type:</dt><dd>Informational</dd><dt>Created:</dt><dd>01-Jan-2026</dd>
          <dt>Post-History:</dt><dd>02-Jan-2026, 03-Jan-2026</dd></dl>
      <ul><li>Abstract</li><li>Motivation</li><li>Specification</li><li>Copyright</li></ul>
      <p>Last modified: 2026-01-03 10:00:00 GMT</p><p>Copyright 2026 Example Foundation.</p>
    </article></body></html>"""
    with pytest.raises(ExtractionError, match="title, metadata or navigation"):
        web.extract_html("https://example.com/pep-9999", html)


def test_tables_and_definition_lists_survive_fallback(monkeypatch):
    html = """<html><body><nav>Home | Docs</nav><main>
      <h1>Reserved names</h1>
      <p>Short intro.</p>
      <table><tr><th>Name</th><th>Purpose</th></tr>
             <tr><td>.test</td><td>testing of current or new DNS related code</td></tr>
             <tr><td>.example</td><td>documentation and examples in published material</td></tr>
             <tr><td>.invalid</td><td>names that are obviously invalid and must never resolve</td></tr></table>
      <dl><dt>localhost</dt><dd>traditionally refers to the loop back address of the local host machine</dd></dl>
    </main></body></html>"""
    monkeypatch.setattr(web.trafilatura, "extract", lambda *a, **k: "# Reserved names\n\nShort intro.")
    text = all_text(web.extract_html("https://example.com/rfc", html))
    assert "| .example | documentation and examples in published material |" in text
    assert "- localhost: traditionally refers to the loop back address" in text
    assert "Home | Docs" not in text


def test_title_falls_back_to_html_title_not_hostname(monkeypatch):
    html = ("<html><head><title>Special-Use Names</title></head><body><main><p>"
            + "Applications SHOULD NOT treat these names specially. " * 20 + "</p></main></body></html>")
    monkeypatch.setattr(web.trafilatura, "extract_metadata", lambda *a, **k: None)
    doc = web.extract_html("https://www.example.org/rfc/rfc0000.html", html)
    assert doc.title == "Special-Use Names"


@pytest.mark.parametrize("url, expected", [
    ("https://github.com/Elijah-cod/sourcetrail-rag", ("https://api.github.com/repos/Elijah-cod/sourcetrail-rag/readme", "README.md")),
    ("https://github.com/Elijah-cod/sourcetrail-rag/", ("https://api.github.com/repos/Elijah-cod/sourcetrail-rag/readme", "README.md")),
    ("https://github.com/o/r/tree/main/docs", ("https://api.github.com/repos/o/r/readme/docs?ref=main", "README.md")),
    ("https://github.com/o/r/blob/v2/docs/guide.md", ("https://raw.githubusercontent.com/o/r/v2/docs/guide.md", "guide.md")),
    ("https://github.com/o/r/blob/main/app.py", None),          # code files: read as a page
    ("https://github.com/o/r/issues/12", None),
    ("https://gist.github.com/o/abc", None),
    ("https://example.com/o/r", None),
])
def test_github_links_are_read_as_markdown(url, expected):
    assert web.github_source(url) == expected


def test_github_readme_keeps_code_blocks(monkeypatch):
    """The repository page lost the README's commands; read as Markdown they are searchable."""
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()
    calls = []
    monkeypatch.setattr(web, "_fetch", lambda url, **kw: calls.append(url) or (url, readme))
    doc = web.extract_url("https://github.com/Elijah-cod/sourcetrail-rag")
    assert calls == ["https://api.github.com/repos/Elijah-cod/sourcetrail-rag/readme"]
    assert doc.source_type == "url" and doc.diagnostics["extractor"] == "github"
    assert doc.title == "sourcetrail-rag"
    assert any("uv run python -m app.migrate" in s.text for s in doc.sections)


def test_github_repository_without_a_readme(monkeypatch):
    def missing(url, **kw):
        raise ExtractionError("That page wasn't found (HTTP 404).")
    monkeypatch.setattr(web, "_fetch", missing)
    with pytest.raises(ExtractionError, match="no README"):
        web.extract_url("https://github.com/o/private-repo")


def test_connection_to_a_private_address_is_refused_even_after_dns_checks_pass():
    """DNS rebinding: the name resolved to a public address when checked, then to 127.0.0.1."""
    class Stream:
        def get_extra_info(self, key):
            return ("127.0.0.1", 80) if key == "server_addr" else None

    class Response:
        extensions = {"network_stream": Stream()}

    with pytest.raises(ExtractionError, match="private or local"):
        web._check_peer(Response())
    Response.extensions = {"network_stream": type("S", (), {"get_extra_info": lambda self, k: ("93.184.216.34", 443)})()}
    web._check_peer(Response())                       # a public address is fine
