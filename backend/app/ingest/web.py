"""Fetch a web page safely and extract its main content.

Safety matters here: on a public site, anyone can make our server fetch any URL.
Without checks, someone could point it at internal addresses (127.0.0.1, 10.x.x.x,
cloud metadata at 169.254.169.254, ...). This is called SSRF
(Server-Side Request Forgery), and validate_url() blocks it.
"""

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

from app.ingest.files import split_markdown
from app.ingest.models import ExtractedDocument, ExtractionError, guess_year

MAX_BYTES = 5 * 1024 * 1024      # refuse pages bigger than 5 MB
TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 5
USER_AGENT = "sourcetrail-rag/0.1 (+https://github.com/Elijah-cod/sourcetrail-rag)"
MIN_WORDS = 20                   # less than this isn't a real article (e.g. just a menu)

# Markdown output escapes special characters: "ts_rank_cd" becomes "ts\_rank\_cd".
# We want the plain text back so keyword search matches what people type.
_MD_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~])")


def _unescape(text: str) -> str:
    return _MD_ESCAPE.sub(r"\1", text)


def validate_url(url: str) -> None:
    """Raise ExtractionError unless the URL is http(s) and points only at public IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ExtractionError("Only http:// and https:// URLs are supported.")

    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, None)}
    except socket.gaierror as exc:
        raise ExtractionError(f"Could not resolve host '{parsed.hostname}'.") from exc

    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise ExtractionError("That URL points to a private or local address, which isn't allowed.")


def fetch_html(url: str) -> tuple[str, str]:
    """Download a page. Follows redirects by hand so every hop is re-validated.

    Returns (final_url, html).
    """
    with httpx.Client(timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            validate_url(url)
            with client.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                if response.status_code >= 400:
                    raise ExtractionError(f"The page returned HTTP {response.status_code}.")
                content_type = response.headers.get("content-type", "")
                if "html" not in content_type:
                    raise ExtractionError(f"Expected an HTML page but got '{content_type or 'unknown'}'.")

                body = bytearray()
                for piece in response.iter_bytes():
                    body.extend(piece)
                    if len(body) > MAX_BYTES:
                        raise ExtractionError("The page is larger than 5 MB.")
                return url, body.decode(response.encoding or "utf-8", errors="replace")
    raise ExtractionError("Too many redirects.")


def extract_html(url: str, html: str) -> ExtractedDocument:
    """Main content of an HTML page -> ExtractedDocument (no network access)."""
    markdown = trafilatura.extract(html, url=url, output_format="markdown", include_formatting=True)
    if not markdown or len(markdown.split()) < MIN_WORDS:
        raise ExtractionError("Couldn't find readable article text on that page.")

    heading_title, sections = split_markdown(markdown)
    for section in sections:
        section.text = _unescape(section.text)
        section.heading = _unescape(section.heading) if section.heading else None
    heading_title = _unescape(heading_title) if heading_title else None
    metadata = trafilatura.extract_metadata(html, default_url=url)
    title = (metadata.title if metadata else None) or heading_title or urlparse(url).hostname or url
    year = guess_year(metadata.date) if metadata and metadata.date else None

    return ExtractedDocument(title=title, source_type="url", sections=sections, published_year=year)


def extract_url(url: str) -> ExtractedDocument:
    """Fetch + extract. This is what the API will call."""
    final_url, html = fetch_html(url.strip())
    return extract_html(final_url, html)
