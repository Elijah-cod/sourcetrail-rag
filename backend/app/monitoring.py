"""One structured log line per question, so the stage times and outcomes can be charted.

Cloud Run sends each JSON line printed to stdout to Cloud Logging as a structured entry: its
fields (status, total_ms, rerank_ms...) can be filtered on and turned into log-based metrics.
The question itself is never logged: visitors' questions may be about their own documents.
"""

import json
import logging
import sys

_log = logging.getLogger("sourcetrail.queries")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))   # the line must be bare JSON
_log.addHandler(_handler)
_log.setLevel(logging.INFO)
_log.propagate = False


def log_query(mode: str, status: str, total_ms: float, timings: dict[str, float], sources: int,
              citations: int) -> None:
    _log.info(json.dumps({
        "severity": "INFO",
        "message": f"query {status} in {total_ms:.0f} ms",
        "event": "query",
        "mode": mode,
        "status": status,
        "total_ms": round(total_ms),
        **{stage: round(ms) for stage, ms in timings.items()},
        "sources": sources,
        "citations": citations,
    }))


def log_event(event: str, **fields) -> None:
    """Anything else worth charting, e.g. log_event("startup", embedder_ms=1830)."""
    _log.info(json.dumps({"severity": "INFO", "message": event, "event": event, **fields}))
