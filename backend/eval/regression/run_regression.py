"""Regression benchmark: the six fixtures from the 8 October 2026 report and their questions.

    uv run python -m eval.regression.run_regression            # retrieval only (no LLM calls)
    uv run python -m eval.regression.run_regression --answers  # also grade answers (uses the LLM quota)

All fixtures are indexed into one temporary workspace with the real embedding and reranker
models and searched together with the demo collection, as the live app does; the workspace is
removed afterwards. Per question (see cases.jsonl) it measures:

- facet coverage: every part of the question ("facets") must have a passage containing one of
  its phrases among the sources handed to the LLM. Compound questions fail here first;
- refusal: unanswerable questions must not reach the LLM (or, with --answers, must be refused);
- uncovered parts: a part of an answerable question reported as having no passage (the answer
  would then say the passages "don't cover" it);
- with --answers: expected facts present, forbidden claims absent, exact modal words (MUST,
  SHOULD NOT...) quoted, and no list item rendered twice; plus how many answers contain a figure
  or code found in no source (the citation check's `unverified`, see app/verify.py).

Retrieval recall and answer correctness are reported separately, so a miss can be blamed on
the right stage. Results are written to eval/regression/results.md, and with --answers the
full answers to eval/regression/answers.jsonl.
"""

import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from app.config import get_settings
from app.embed import get_embedder
from app.indexing import index_document
from app.ingest import extract_file
from app.ingest.models import ExtractionError
from app.ingest.web import extract_html
from app.qa import ask, gather_sources
from app.rerank import get_reranker
from app.seed_demo import seed
from app.store import DEMO_WORKSPACE_ID

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"


@dataclass
class Case:
    id: str
    fixture: str
    kind: str = "question"
    question: str = ""
    facets: list[list[str]] = field(default_factory=list)
    answerable: bool = True
    facts: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    exact_words: list[str] = field(default_factory=list)
    no_duplicates: list[str] = field(default_factory=list)
    title: str | None = None
    contains: list[str] = field(default_factory=list)
    reject: str | None = None


def load_cases(path: Path = HERE / "cases.jsonl") -> list[Case]:
    with path.open() as f:
        return [Case(**json.loads(line)) for line in f if line.strip()]


def extract(name: str):
    path = FIXTURES / name
    if path.suffix == ".html":
        return extract_html(f"https://example.org/{path.stem}", path.read_text())
    return extract_file(path.name, path.read_bytes())


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def covered(facet: list[str], texts: list[str]) -> bool:
    return any(norm(phrase) in t for phrase in facet for t in texts)


def check_ingest(case: Case) -> tuple[bool, str]:
    try:
        doc = extract(case.fixture)
    except ExtractionError as exc:
        ok = case.reject is not None and case.reject.lower() in str(exc).lower()
        return ok, f"rejected: {exc}"
    if case.reject is not None:
        return False, "accepted, but should have been rejected"
    problems = []
    if case.title and doc.title != case.title:
        problems.append(f"title {doc.title!r}, expected {case.title!r}")
    text = " ".join(s.text for s in doc.sections)
    problems += [f"missing {c!r}" for c in case.contains if c not in text]
    return not problems, "; ".join(problems) or f"title {doc.title!r}, {len(doc.sections)} sections"


def modal_words(text: str) -> list[str]:
    return re.findall(r"\b(?:MUST NOT|SHOULD NOT|SHALL NOT|MUST|SHOULD|SHALL|MAY|REQUIRED|RECOMMENDED)\b", text)


def grade_answer(case: Case, answer) -> list[str]:
    """Problems with an LLM answer ([] = pass)."""
    text = answer.answer
    if answer.status == "llm_unavailable":
        return ["LLM unavailable (quota or network), not graded"]
    if not case.answerable:
        return [] if answer.status == "not_found" else [f"answered an unanswerable question: {text[:80]!r}"]
    problems = [f"missing fact {f!r}" for f in case.facts if norm(f) not in norm(text)]
    problems += [f"forbidden claim {f!r}" for f in case.forbidden if norm(f) in norm(text)]
    problems += [f"didn't quote {w!r}" for w in case.exact_words if w not in modal_words(text)]
    lines = [line for line in text.splitlines() if re.match(r"\s*([-*•]|\d+[.)])\s", line)]
    for key in case.no_duplicates:
        if sum(key in line for line in lines) > 1:
            problems.append(f"{key} listed more than once")
    if "duplicate" in text.lower() and "removed" in text.lower():
        problems.append("rendered a 'duplicate removed' note")
    return problems


class PatientLLM:
    """Waits out the free tier's per-minute limit instead of failing the rest of the run."""

    def __init__(self, inner, waits=(20, 40, 60)):
        self.inner, self.waits = inner, waits

    def complete(self, messages):
        from app.llm import LLMUnavailable
        for wait in (*self.waits, None):
            try:
                return self.inner.complete(messages)
            except LLMUnavailable as exc:
                if wait is None or "quota" not in str(exc):
                    raise
                print(f"  rate limited, waiting {wait}s", file=sys.stderr)
                time.sleep(wait)


def run(with_answers: bool = False) -> str:
    cases = load_cases()
    embedder, reranker = get_embedder(), get_reranker()
    llm = None
    if with_answers:
        from app.llm import get_llm
        llm = PatientLLM(get_llm())

    rows, ingest_rows, answers = [], [], []
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        for case in (c for c in cases if c.kind == "ingest"):
            ok, detail = check_ingest(case)
            ingest_rows.append((case, ok, detail))

        # Like the live app: every fixture in one workspace, searched together with the demo
        # collection. Per-fixture workspaces hid competition between documents (the 8 Oct live
        # check failed questions this benchmark passed that way).
        if not conn.execute("SELECT 1 FROM documents WHERE workspace_id = %s LIMIT 1", (DEMO_WORKSPACE_ID,)).fetchone():
            seed(conn, embedder)
        workspace = conn.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()[0]
        searched = [workspace, DEMO_WORKSPACE_ID]
        try:
            for fixture in dict.fromkeys(c.fixture for c in cases if c.kind == "question"):
                index_document(conn, embedder, workspace, extract(fixture), source_uri=fixture)
            for case in (c for c in cases if c.kind == "question"):
                started = time.perf_counter()
                found = gather_sources(conn, embedder, reranker, case.question, searched)
                ms = (time.perf_counter() - started) * 1000
                sent = [] if found.final is not None else found.hits
                texts = [norm(f"{h.section or ''}\n{h.text}") for h in sent if h.source_uri == case.fixture]
                got = sum(covered(f, texts) for f in case.facets)
                answer_problems, unverified = None, None
                if llm is not None:
                    answer = ask(conn, embedder, reranker, llm, case.question, searched)
                    answer_problems, unverified = grade_answer(case, answer), answer.unverified
                    answers.append({"id": case.id, "question": case.question, "status": answer.status,
                                    "answer": answer.answer, "problems": answer_problems,
                                    "unverified": answer.unverified,
                                    "sources": [f"{h.source_uri} | {h.section}" for h in answer.sources]})
                rows.append((case, got, len(sent), ms, answer_problems, found.uncovered, unverified))
        finally:
            conn.execute("DELETE FROM workspaces WHERE id = %s", (workspace,))

    report = format_report(ingest_rows, rows, with_answers)
    (HERE / "results.md").write_text(report)
    if answers:        # the full answers, to see *why* a check failed
        (HERE / "answers.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in answers))
    return report


def format_report(ingest_rows, rows, with_answers: bool) -> str:
    answerable = [r for r in rows if r[0].answerable]
    unanswerable = [r for r in rows if not r[0].answerable]
    facets = sum(len(r[0].facets) for r in answerable)
    facets_found = sum(r[1] for r in answerable)
    complete = sum(r[1] == len(r[0].facets) for r in answerable)
    compound = [r for r in answerable if len(r[0].facets) > 1]
    refused = sum(r[2] == 0 for r in unanswerable)
    lines = [
        "# Regression benchmark", "",
        "Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).", "",
        "| Metric | Result |", "|---|---|",
        f"| Ingestion (valid accepted, invalid rejected, titles) | {sum(ok for _, ok, _ in ingest_rows)}/{len(ingest_rows)} |",
        f"| Facet coverage (parts of a question with a supporting passage) | {facets_found}/{facets} "
        f"({facets_found / facets:.0%}) |",
        f"| Questions with every facet covered | {complete}/{len(answerable)} |",
        f"| Compound questions fully covered | {sum(r[1] == len(r[0].facets) for r in compound)}/{len(compound)} |",
        f"| Unanswerable questions stopped before the LLM (the rest must be refused by it) | {refused}/{len(unanswerable)} |",
        f"| Answerable questions with a part reported as uncovered | {sum(bool(r[5]) for r in answerable)}"
        f"/{len(answerable)} |",
        f"| Median retrieval latency | {sorted(r[3] for r in rows)[len(rows) // 2]:.0f} ms |",
    ]
    if with_answers:
        graded = [r for r in rows if not (r[4] and r[4][0].startswith("LLM unavailable"))]
        passed = sum(not r[4] for r in graded)
        lines.append(f"| Answers passing every check | {passed}/{len(graded)} graded"
                     f"{f' ({len(rows) - len(graded)} not graded: LLM unavailable)' if len(graded) < len(rows) else ''} |")
        lines.append(f"| Answers with a figure or code found in no source | {sum(bool(r[6]) for r in graded)}"
                     f"/{len(graded)} |")
    lines += ["", "## Ingestion", "", "| Case | Result | Detail |", "|---|---|---|"]
    lines += [f"| {c.id} | {'pass' if ok else 'FAIL'} | {d} |" for c, ok, d in ingest_rows]
    lines += ["", "## Questions", "", "| Case | Facets covered | Sources sent | Latency | Answer |", "|---|---|---|---|---|"]
    for case, got, sent, ms, problems, uncovered, unverified in rows:
        cover = f"{got}/{len(case.facets)}" if case.answerable else ("refused" if sent == 0 else f"reached the LLM ({sent} sent)")
        if case.answerable and uncovered:
            cover += f" (uncovered: {'; '.join(uncovered)})"
        verdict = "-" if problems is None else ("pass" if not problems else "; ".join(problems))
        if unverified:
            verdict += f" (not in any source: {', '.join(unverified)})"
        lines.append(f"| {case.id} | {cover} | {sent} | {ms:.0f} ms | {verdict} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(run(with_answers="--answers" in sys.argv))
