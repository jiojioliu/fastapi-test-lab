from __future__ import annotations

import math
import threading
import time
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Any


class TrafficStore:
    """Thread-safe, intentionally in-memory traffic metrics for load testing."""

    def __init__(self, capacity: int = 1500):
        self._entries: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._total_requests = 0
        self._total_errors = 0
        self._active_requests = 0

    def request_started(self) -> None:
        with self._lock:
            self._active_requests += 1

    def record(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        response_size: int,
    ) -> None:
        now = time.time()
        entry = {
            "request_id": request_id,
            "timestamp": datetime.fromtimestamp(
                now, timezone.utc
            ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "epoch": now,
            "method": method,
            "path": path,
            "status": status_code,
            "duration_ms": round(duration_ms, 2),
            "response_size": response_size,
        }
        with self._lock:
            self._entries.append(entry)
            self._total_requests += 1
            if status_code >= 400:
                self._total_errors += 1
            self._active_requests = max(0, self._active_requests - 1)

    def request_failed(self) -> None:
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._total_requests = 0
            self._total_errors = 0
            self._active_requests = 0

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = max(0, math.ceil(percentile / 100 * len(ordered)) - 1)
        return round(ordered[index], 2)

    def snapshot(self, recent_limit: int = 40) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            entries = list(self._entries)
            total = self._total_requests
            errors = self._total_errors
            active = self._active_requests

        last_minute = [entry for entry in entries if entry["epoch"] >= now - 60]
        durations = [float(entry["duration_ms"]) for entry in last_minute]
        status_counts = Counter(str(entry["status"]) for entry in last_minute)
        method_counts = Counter(entry["method"] for entry in last_minute)
        endpoint_counts = Counter(entry["path"] for entry in last_minute)

        bins = []
        bin_count = 15
        bin_seconds = 4
        current_bucket = int(now // bin_seconds)
        for offset in range(bin_count - 1, -1, -1):
            bucket = current_bucket - offset
            start = bucket * bin_seconds
            label = datetime.fromtimestamp(
                start + bin_seconds, timezone.utc
            ).strftime("%H:%M:%S")
            count = sum(
                1
                for entry in entries
                if start <= entry["epoch"] < start + bin_seconds
            )
            bin_errors = sum(
                1
                for entry in entries
                if start <= entry["epoch"] < start + bin_seconds
                and int(entry["status"]) >= 400
            )
            bins.append({"label": label, "count": count, "errors": bin_errors})

        error_rate = (errors / total * 100) if total else 0.0
        return {
            "generated_at": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "summary": {
                "total_requests": total,
                "requests_last_minute": len(last_minute),
                "requests_per_second": round(len(last_minute) / 60, 2),
                "error_rate": round(error_rate, 2),
                "active_requests": active,
                "avg_latency_ms": round(
                    sum(durations) / len(durations), 2
                ) if durations else 0.0,
                "p50_latency_ms": self._percentile(durations, 50),
                "p95_latency_ms": self._percentile(durations, 95),
                "p99_latency_ms": self._percentile(durations, 99),
            },
            "timeline": bins,
            "status_distribution": dict(
                sorted(status_counts.items(), key=lambda item: item[0])
            ),
            "method_distribution": dict(method_counts),
            "top_endpoints": [
                {"path": path, "count": count}
                for path, count in endpoint_counts.most_common(6)
            ],
            "recent": list(reversed(entries[-recent_limit:])),
        }


traffic_store = TrafficStore()

