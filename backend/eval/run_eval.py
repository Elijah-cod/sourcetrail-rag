"""Evaluate retrieval on the demo collection: vector vs keyword vs hybrid vs hybrid + reranker.

    uv run python -m app.seed_demo          # once, to load the demo collection
    uv run python -m eval.run_eval          # prints a table and writes eval/results.md

A retrieved chunk is *relevant* if it comes from the expected source file and contains the
expected phrase (see questions.jsonl). Phrases survive re-chunking; chunk IDs wouldn't.
"""

import json
import re
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from app.config import get_settings
from app.query import parse_query
from app.retrieve import MODES, retrieve
from app.search import SearchHit
from app.store import DEMO_WORKSPACE_ID

HERE = Path(__file__).parent
K = 10          # retrieve this many results per question


@dataclass
class Question:
    id: str
    question: str
    relevant: list[dict]          # [{"source": "file.md", "contains": "phrase"}, ...]; [] = unanswerable

    @property
    def answerable(self) -> bool:
        return bool(self.relevant)


def load_questions(path: Path = HERE / "questions.jsonl") -> list[Question]:
    with path.open() as f:
        return [Question(**json.loads(line)) for line in f if line.strip()]


def normalize(text: str) -> str:
    """Compare text ignoring line breaks and repeated spaces (PDF text wraps unpredictably)."""
    return re.sub(r"\s+", " ", text).strip().lower()


def is_relevant(hit: SearchHit, question: Question) -> bool:
    return any(hit.source_uri == r["source"] and normalize(r["contains"]) in normalize(hit.text)
               for r in question.relevant)


def first_relevant_rank(hits: list[SearchHit], question: Question) -> int | None:
    """1-based position of the first relevant hit, or None if there isn't one."""
    for rank, hit in enumerate(hits, start=1):
        if is_relevant(hit, question):
            return rank
    return None


@dataclass
class ModeResult:
    mode: str
    ranks: list[int | None] = field(default_factory=list)       # one per answerable question
    precision_at_5: list[float] = field(default_factory=list)
    seconds: list[float] = field(default_factory=list)

    def recall_at(self, k: int) -> float:
        """Share of questions with a relevant chunk in the top k (a.k.a. hit rate)."""
        return sum(1 for r in self.ranks if r is not None and r <= k) / len(self.ranks)

    @property
    def mrr(self) -> float:
        """Mean Reciprocal Rank: 1 if the answer is always 1st, 0.5 if always 2nd, ..."""
        return sum(1 / r for r in self.ranks if r is not None) / len(self.ranks)

    @property
    def precision5(self) -> float:
        return statistics.mean(self.precision_at_5)

    @property
    def avg_ms(self) -> float:
        return 1000 * statistics.mean(self.seconds)


def evaluate(conn, embedder, reranker, questions: list[Question]) -> tuple[list[ModeResult], dict]:
    results = []
    top_scores = {"answerable": [], "unanswerable": []}     # reranker's best score per question
    for mode in MODES:
        result = ModeResult(mode)
        for q in questions:
            start = time.perf_counter()
            parsed = parse_query(q.question)          # same query processing as the real app
            hits = retrieve(conn, embedder, parsed.text, [DEMO_WORKSPACE_ID], mode=mode,
                            reranker=reranker, limit=30, top_k=K, year=parsed.year)[:K]
            elapsed = time.perf_counter() - start
            if mode == "hybrid_rerank":
                top_scores["answerable" if q.answerable else "unanswerable"].append(
                    hits[0].score if hits else 0.0)
            if not q.answerable:
                continue
            result.ranks.append(first_relevant_rank(hits, q))
            result.precision_at_5.append(sum(is_relevant(h, q) for h in hits[:5]) / 5)
            result.seconds.append(elapsed)
        results.append(result)
    return results, top_scores


def report(results: list[ModeResult], top_scores: dict, n_answerable: int, n_unanswerable: int) -> str:
    threshold = get_settings().min_relevance
    lines = [
        "# Retrieval evaluation",
        "",
        f"{n_answerable} answerable questions over the demo collection "
        f"(+{n_unanswerable} unanswerable ones for the relevance threshold).",
        "",
        "| Mode | Recall@1 | Recall@5 | Recall@10 | MRR | Precision@5 | Avg latency |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.mode} | {r.recall_at(1):.2f} | {r.recall_at(5):.2f} | {r.recall_at(10):.2f} "
                     f"| {r.mrr:.3f} | {r.precision5:.2f} | {r.avg_ms:.0f} ms |")

    ans, unans = top_scores["answerable"], top_scores["unanswerable"]
    if ans and unans:
        lines += [
            "",
            "## Relevance threshold (reranker top score)",
            "",
            f"- Answerable questions: min {min(ans):.4f}, median {statistics.median(ans):.4f}",
            f"- Unanswerable questions: max {max(unans):.4f}, median {statistics.median(unans):.4f}",
            f"- Current `MIN_RELEVANCE` = {threshold}: would wrongly refuse "
            f"{sum(s < threshold for s in ans)}/{len(ans)} answerable and correctly refuse "
            f"{sum(s < threshold for s in unans)}/{len(unans)} unanswerable questions.",
        ]
    lines += ["", "Recall@k: share of questions with a correct chunk in the top k. "
              "MRR: average of 1/rank of the first correct chunk. "
              "Precision@5: share of the top 5 that are correct."]
    return "\n".join(lines) + "\n"


def main() -> None:
    from app.embed import get_embedder
    from app.rerank import get_reranker

    questions = load_questions()
    embedder, reranker = get_embedder(), get_reranker()
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        demo_docs = conn.execute("SELECT count(*) FROM documents WHERE workspace_id = %s",
                                 (DEMO_WORKSPACE_ID,)).fetchone()[0]
        if demo_docs == 0:
            raise SystemExit("The demo collection is empty. Run: uv run python -m app.seed_demo")
        results, top_scores = evaluate(conn, embedder, reranker, questions)

    answerable, unanswerable = sum(q.answerable for q in questions), sum(not q.answerable for q in questions)
    text = report(results, top_scores, answerable, unanswerable)
    print(text)
    (HERE / "results.md").write_text(text)
    # The same numbers for the app's Benchmarks page (GET /benchmarks).
    (HERE / "results.json").write_text(json.dumps(
        as_json(results, top_scores, answerable, unanswerable, get_settings().min_relevance), indent=1) + "\n")
    print(f"Saved to {HERE / 'results.md'} and results.json")


def as_json(results, top_scores: dict, answerable: int, unanswerable: int, threshold: float) -> dict:
    from datetime import datetime, timezone
    ans, unans = top_scores["answerable"], top_scores["unanswerable"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "answerable": answerable, "unanswerable": unanswerable,
        "modes": [{"mode": r.mode, "recall_at_1": round(r.recall_at(1), 3), "recall_at_5": round(r.recall_at(5), 3),
                   "recall_at_10": round(r.recall_at(10), 3), "mrr": round(r.mrr, 3),
                   "precision_at_5": round(r.precision5, 3), "avg_ms": round(r.avg_ms)} for r in results],
        "threshold": None if not (ans and unans) else {
            "value": threshold,
            "answerable_refused": sum(s < threshold for s in ans), "answerable": len(ans),
            "unanswerable_refused": sum(s < threshold for s in unans), "unanswerable": len(unans),
        },
    }


if __name__ == "__main__":
    main()
