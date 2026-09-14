"""Per-route latency tracking.

Deliberately dependency-free: a bounded deque per route and percentiles
computed on read. In a real deployment these are Prometheus histograms
scraped into Grafana, but the point of carrying it here is that an agent
tool call is a production request like any other, and "the agent felt slow"
is not an engineering statement. P95 and P99 are.
"""

import statistics
import threading
from collections import defaultdict, deque

_MAX_SAMPLES = 1000


class LatencyRegistry:
    def __init__(self) -> None:
        self._samples: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=_MAX_SAMPLES)
        )
        self._errors: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def record(self, route: str, elapsed_ms: float, is_error: bool = False) -> None:
        with self._lock:
            self._samples[route].append(elapsed_ms)
            if is_error:
                self._errors[route] += 1

    def snapshot(self) -> dict:
        with self._lock:
            routes = {}
            for route, samples in self._samples.items():
                if not samples:
                    continue
                ordered = sorted(samples)
                routes[route] = {
                    "count": len(ordered),
                    "errors": self._errors.get(route, 0),
                    "p50_ms": round(_percentile(ordered, 0.50), 2),
                    "p95_ms": round(_percentile(ordered, 0.95), 2),
                    "p99_ms": round(_percentile(ordered, 0.99), 2),
                    "mean_ms": round(statistics.fmean(ordered), 2),
                }
            return {"routes": routes}


def _percentile(ordered: list[float], q: float) -> float:
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    index = min(round(q * (len(ordered) - 1)), len(ordered) - 1)
    return ordered[index]


LATENCY = LatencyRegistry()
