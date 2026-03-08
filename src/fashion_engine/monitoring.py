from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from statistics import mean
from threading import Lock

_MAX_RESPONSE_SAMPLES = 100
_MAX_SLOW_QUERIES = 200

_response_times: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=_MAX_RESPONSE_SAMPLES))
_slow_queries: deque[dict] = deque(maxlen=_MAX_SLOW_QUERIES)
_lock = Lock()


def record_response_time(path: str, elapsed_seconds: float) -> None:
    with _lock:
        _response_times[path].append(float(elapsed_seconds))


def record_slow_query(statement: str, elapsed_ms: float) -> None:
    normalized = " ".join((statement or "").split())
    with _lock:
        _slow_queries.appendleft(
            {
                "statement": normalized[:500],
                "elapsed_ms": round(float(elapsed_ms), 2),
                "captured_at": datetime.utcnow().isoformat(),
            }
        )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def get_response_metrics() -> list[dict]:
    with _lock:
        snapshot = {path: list(samples) for path, samples in _response_times.items() if samples}
    rows: list[dict] = []
    for path, samples in snapshot.items():
        rows.append(
            {
                "path": path,
                "count": len(samples),
                "avg_ms": round(mean(samples) * 1000, 2),
                "p50_ms": round(_percentile(samples, 0.50) * 1000, 2),
                "p95_ms": round(_percentile(samples, 0.95) * 1000, 2),
                "p99_ms": round(_percentile(samples, 0.99) * 1000, 2),
            }
        )
    rows.sort(key=lambda item: (-item["p95_ms"], item["path"]))
    return rows


def get_slow_queries(limit: int = 20) -> list[dict]:
    with _lock:
        return list(list(_slow_queries)[:limit])
