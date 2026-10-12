"""Fetch a web page safely and extract its main content.

Safety matters here: on a public site, anyone can make our server fetch any URL.
Without checks, someone could point it at internal addresses (127.0.0.1, 10.x.x.x,
cloud metadata at 169.254.169.254, ...). This is called SSRF
(Server-Side Request Forgery), and validate_url() blocks it.
"""

import ipaddress
import re
import socket
import time
from urllib.parse import urljoin, urlparse

import httpx
import lxml.html
import trafilatura

from app.ingest.files import split_markdown
from app.ingest.models import ExtractedDocument, ExtractionError, guess_year

MAX_BYTES = 5 * 1024 * 1024      # refuse pages bigger than 5 MB
TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 5
MAX_SECONDS = 20                 # for the whole download: a server dripping bytes can't hold us
USER_AGENT = "sourcetrail-rag/0.1 (+https://github.com/Elijah-cod/sourcetrail-rag)"
MIN_WORDS = 20                   # less than this isn't a real article (e.g. just a menu)
MIN_COVERAGE = 0.5               # trafilatura must keep at least half the main content's words...
MIN_BLOCK_COVERAGE = 0.6         # ...and most of every <pre>/<table>/<dl> block, or we fall back

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
    return _fetch(url, accept=("html",), what="an HTML page")


def _fetch(url: str, accept: tuple[str, ...], what: str, headers: dict | None = None) -> tuple[str, str]:
    """GET `url` as text: public addresses only (checked again on every redirect), at most
    MAX_BYTES, and only a content type containing one of `accept`."""
    started = time.monotonic()
    with httpx.Client(timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT, **(headers or {})}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            validate_url(url)
            with client.stream("GET", url) as response:
                # The name was checked above, but DNS can answer differently a moment later
                # ("DNS rebinding"): check the address actually connected to as well.
                _check_peer(response)
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                if response.status_code == 404:
                    raise ExtractionError("That page wasn't found (HTTP 404).")
                if response.status_code >= 400:
                    raise ExtractionError(f"The page returned HTTP {response.status_code}.")
                content_type = response.headers.get("content-type", "")
                if not any(kind in content_type for kind in accept):
                    raise ExtractionError(f"Expected {what} but got '{content_type or 'unknown'}'.")

                body = bytearray()
                for piece in response.iter_bytes():
                    body.extend(piece)
                    if len(body) > MAX_BYTES:
                        raise ExtractionError("The page is larger than 5 MB.")
                    if time.monotonic() - started > MAX_SECONDS:
                        raise ExtractionError(f"The page took more than {MAX_SECONDS} seconds to download.")
                return url, body.decode(response.encoding or "utf-8", errors="replace")
    raise ExtractionError("Too many redirects.")


def _check_peer(response: httpx.Response) -> None:
    stream = response.extensions.get("network_stream")
    peer = stream.get_extra_info("server_addr") if stream is not None else None
    if peer and not ipaddress.ip_address(peer[0]).is_global:
        raise ExtractionError("That URL points to a private or local address, which isn't allowed.")


# ---------- GitHub ----------
# A repository's page is mostly GitHub's own interface; the README is rendered into it, but the
# generic extractor kept the description and lost most of the README, code blocks included
# ("uv run python -m app.migrate" couldn't be found). So GitHub links are read as Markdown
# straight from GitHub: the README for a repository or folder, the raw file for a .md file.

_GITHUB = re.compile(r"^/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?"
                     r"(?:/(?P<kind>tree|blob)/(?P<ref>[^/]+)(?:/(?P<path>.*))?)?/?$")
_MARKDOWN_FILE = re.compile(r"\.(?:md|markdown|mdx|txt|rst)$", re.IGNORECASE)


def github_source(url: str) -> tuple[str, str] | None:
    """For a github.com repository, folder or Markdown file link: (URL of its raw Markdown, file
    name), else None (issues, pull requests, other files: read as ordinary pages)."""
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() not in ("github.com", "www.github.com"):
        return None
    match = _GITHUB.match(parsed.path)
    if not match or match["owner"] in ("orgs", "settings", "topics", "search", "marketplace"):
        return None
    owner, repo, kind, ref, path = match["owner"], match["repo"], match["kind"], match["ref"], match["path"]
    api = f"https://api.github.com/repos/{owner}/{repo}"
    if kind is None:
        return f"{api}/readme", "README.md"
    if kind == "tree":
        folder = f"/{path.strip('/')}" if path and path.strip("/") else ""
        return f"{api}/readme{folder}?ref={ref}", "README.md"
    if path and _MARKDOWN_FILE.search(path):
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}", path.rsplit("/", 1)[-1]
    return None


def extract_github(url: str) -> ExtractedDocument | None:
    """A GitHub repository/folder/Markdown link read as its Markdown, or None if it isn't one."""
    source = github_source(url)
    if source is None:
        return None
    raw_url, filename = source
    try:
        _, text = _fetch(raw_url, accept=("text", "json", "markdown", "octet-stream", "vnd.github"),
                         what="a README", headers={"Accept": "application/vnd.github.raw+json"})
    except ExtractionError as exc:
        if "404" in str(exc):
            raise ExtractionError("That GitHub repository or folder has no README that can be read "
                                  "(private repositories can't be added).") from exc
        raise
    from app.ingest.files import extract_markdown
    doc = extract_markdown(filename, text.encode())
    parsed = urlparse(url)
    owner_repo = "/".join(parsed.path.strip("/").split("/")[:2])
    if doc.title in (None, "", filename, filename.rsplit(".", 1)[0]):
        doc.title = f"{owner_repo} ({filename})"
    doc.source_type = "url"
    doc.diagnostics = {"extractor": "github", "raw_url": raw_url, "retained_chars": len(text)}
    return doc


# ---------- extraction quality ----------
# trafilatura is good at dropping menus and footers, but it can also drop the main content when
# that content is in <pre>, <table> or <dl> markup (PEP 20's aphorisms are one <pre> block): the
# page was then "added" with only its title and metadata indexed. So we measure the page's main
# content ourselves, check trafilatura kept it, and if not, convert the main content directly.

_CHROME_TAGS = ["script", "style", "noscript", "template", "svg", "nav", "header", "footer",
                "aside", "form", "button", "iframe"]
_CHROME_ROLES = ("navigation", "banner", "contentinfo", "search", "complementary")
_IMPORTANT_TAGS = ("pre", "table", "dl")
_WORD = re.compile(r"\w+", re.UNICODE)
# Lines that are page furniture, not content, when judging whether anything real was extracted.
_BOILERPLATE = re.compile(r"copyright|©|all rights reserved|last (modified|updated)|^source:|cookie|"
                          r"privacy policy|terms of (use|service)|subscribe|sign (in|up)|log ?in|"
                          r"skip to|table of contents|share this", re.IGNORECASE)


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _main_region(html: str):
    """The page's main content element with navigation, headers, footers and scripts removed."""
    try:
        tree = lxml.html.fromstring(html)
    except (lxml.etree.ParserError, ValueError):
        return None
    for element in tree.xpath("//" + " | //".join(_CHROME_TAGS)):
        element.drop_tree()
    for element in tree.xpath("//*[@role]"):
        if element.get("role") in _CHROME_ROLES:
            element.drop_tree()
    for path in ("//main", "//*[@role='main']", "//article", "//body"):
        found = tree.xpath(path)
        if found:
            return max(found, key=lambda e: len(e.text_content()))
    return tree


def _inline(element) -> str:
    return re.sub(r"\s+", " ", element.text_content()).strip()


def _region_to_markdown(region) -> str:
    """Our own HTML -> Markdown for the main region: headings, paragraphs, lists, <pre>, tables
    and definition lists. Plainer than trafilatura, but it never drops a block."""
    out: list[str] = []

    def walk(element) -> None:
        tag = element.tag if isinstance(element.tag, str) else ""
        if re.fullmatch(r"h[1-6]", tag):
            text = _inline(element)
            if text:
                out.append("#" * int(tag[1]) + " " + text)
        elif tag == "pre":
            text = element.text_content().strip("\n")
            if text.strip():
                out.append("```\n" + text + "\n```")
        elif tag == "table":
            rows = []
            for row in element.xpath(".//tr"):
                cells = [_inline(c) for c in row.xpath("./th|./td")]
                if any(cells):
                    rows.append("| " + " | ".join(cells) + " |")
            if rows:
                out.append("\n".join(rows))
        elif tag == "dl":
            lines, term = [], None
            for child in element:
                if child.tag == "dt":
                    term = _inline(child).rstrip(":").strip()
                elif child.tag == "dd":
                    text = _inline(child)
                    lines.append(f"- {term}: {text}" if term else f"- {text}")
            if lines:
                out.append("\n".join(lines))
        elif tag in ("ul", "ol"):
            items = [_inline(li) for li in element.xpath("./li")]
            items = [i for i in items if i]
            if items:
                out.append("\n".join(f"- {i}" for i in items))
        elif tag in ("p", "blockquote") or (tag in ("div", "section", "article", "main", "body", "td")
                                             and not any(isinstance(c.tag, str) for c in element)):
            text = _inline(element)
            if text:
                out.append(("> " if tag == "blockquote" else "") + text)
        else:
            if element.text and element.text.strip() and tag in ("div", "section", "article", "main", "body"):
                out.append(element.text.strip())
            for child in element:
                walk(child)
                if child.tail and child.tail.strip() and tag in ("div", "section", "article", "main", "body"):
                    out.append(child.tail.strip())

    walk(region)
    return "\n\n".join(out)


def _coverage(source_words: list[str], kept: set[str]) -> float:
    return sum(w in kept for w in source_words) / len(source_words) if source_words else 1.0


def _missing_blocks(region, kept: set[str]) -> list[str]:
    """Tags of substantial <pre>/<table>/<dl> blocks whose words are mostly missing from `kept`."""
    missing = []
    for element in region.xpath(".//pre | .//table | .//dl"):
        words = _words(element.text_content())
        if len(words) >= 8 and _coverage(words, kept) < MIN_BLOCK_COVERAGE:
            missing.append(element.tag)
    return missing


def substantive_words(markdown: str) -> int:
    """Words of real content: not headings, not short list items or labels (metadata like
    '- Status: Active'), not page furniture like copyright or 'Last modified' lines."""
    count = 0
    for line in markdown.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "```")) or _BOILERPLATE.search(line):
            continue
        words = _words(line)
        if len(words) <= 3 or (line.startswith(("- ", "* ", "|")) and len(words) <= 6):
            continue
        count += len(words)
    return count


def extract_html(url: str, html: str) -> ExtractedDocument:
    """Main content of an HTML page -> ExtractedDocument (no network access)."""
    markdown = trafilatura.extract(html, url=url, output_format="markdown", include_formatting=True,
                                   include_tables=True) or ""
    region = _main_region(html)
    region_words = _words(region.text_content()) if region is not None else []
    diagnostics = {"extractor": "trafilatura", "original_chars": len(html),
                   "main_content_words": len(region_words)}

    if region is not None and region_words:
        kept = set(_words(markdown))
        coverage = _coverage(region_words, kept)
        dropped = _missing_blocks(region, kept)
        diagnostics.update(trafilatura_coverage=round(coverage, 2), dropped_elements=sorted(set(dropped)))
        if dropped or coverage < MIN_COVERAGE:
            fallback = _region_to_markdown(region)
            if substantive_words(fallback) > substantive_words(markdown):
                markdown = fallback
                diagnostics["extractor"] = "main-content fallback"

    if not markdown or len(markdown.split()) < MIN_WORDS:
        raise ExtractionError("Couldn't find readable article text on that page.")
    if substantive_words(markdown) < MIN_WORDS:
        raise ExtractionError("Only the page's title, metadata or navigation could be read, not its "
                              "main text, so it wasn't added. Try a page with the article itself.")
    diagnostics["retained_chars"] = len(markdown)

    heading_title, sections = split_markdown(markdown)
    if diagnostics["extractor"] == "trafilatura":       # only trafilatura escapes its Markdown
        for section in sections:
            section.text = _unescape(section.text)
            section.heading = _unescape(section.heading) if section.heading else None
        heading_title = _unescape(heading_title) if heading_title else None
    metadata = trafilatura.extract_metadata(html, default_url=url)
    title = (metadata.title if metadata else None) or heading_title or _html_title(html) or urlparse(url).hostname or url
    year = guess_year(metadata.date) if metadata and metadata.date else None

    return ExtractedDocument(title=title, source_type="url", sections=sections, published_year=year,
                             diagnostics=diagnostics)


def _html_title(html: str) -> str | None:
    """The page's <title>, else its first <h1>: a name people recognise, unlike the hostname."""
    try:
        tree = lxml.html.fromstring(html)
    except (ValueError, lxml.etree.ParserError):
        return None
    for path in ("//title", "//h1"):
        found = tree.xpath(path)
        text = re.sub(r"\s+", " ", found[0].text_content()).strip() if found else ""
        if text:
            return text
    return None


def extract_url(url: str) -> ExtractedDocument:
    """Fetch + extract. This is what the API will call."""
    url = url.strip()
    github = extract_github(url)
    if github is not None:
        return github
    final_url, html = fetch_html(url)
    return extract_html(final_url, html)
