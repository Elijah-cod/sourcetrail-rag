"""Download and clean the open-source documentation used in the demo collection.

Run from backend/:  uv run python demo/fetch_sources.py
Writes cleaned Markdown into demo/sources/. Licences and attribution: demo/SOURCES.md.
"""

import re
import urllib.request
from pathlib import Path

FASTAPI_COMMIT = "6e659e84de09"     # pinned so the corpus (and the eval answers) don't drift
PGVECTOR_COMMIT = "f37c13f68b57"

FASTAPI_PAGES = [
    "tutorial/first-steps", "tutorial/path-params", "tutorial/query-params", "tutorial/body",
    "tutorial/dependencies/index", "tutorial/handling-errors", "tutorial/cors", "deployment/concepts",
]

OUT = Path(__file__).parent / "sources"


def clean_mkdocs(markdown: str) -> str:
    """Strip website-only syntax so only readable text and code remain."""
    lines = []
    for line in markdown.splitlines():
        if re.match(r"^\{\*.*\*\}\s*$", line):          # {* ../../docs_src/x.py *}  (code include)
            continue
        admonition = re.match(r"^///\s*(\w+)?", line)     # /// tip   ...   ///
        if admonition:
            if admonition.group(1):
                lines.append(f"{admonition.group(1).capitalize()}:")
            continue
        line = re.sub(r"\s*\{\s*#[\w-]+\s*\}\s*$", "", line)   # "# Title { #title }" -> "# Title"
        line = re.sub(r"</?(font|span|u|b|div|abbr|dfn|img)[^>]*>", "", line)  # HTML styling tags
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for page in FASTAPI_PAGES:
        url = f"https://raw.githubusercontent.com/fastapi/fastapi/{FASTAPI_COMMIT}/docs/en/docs/{page}.md"
        name = "fastapi-" + page.replace("/index", "").replace("/", "-") + ".md"
        (OUT / name).write_text(clean_mkdocs(fetch(url)))
        print("wrote", name)

    url = f"https://raw.githubusercontent.com/pgvector/pgvector/{PGVECTOR_COMMIT}/README.md"
    (OUT / "pgvector-readme.md").write_text(fetch(url))
    print("wrote pgvector-readme.md")


if __name__ == "__main__":
    main()
