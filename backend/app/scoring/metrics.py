"""
SentinelRisk — Observability, Structured Metrics & Operational Alerts

Provides:
  - Request correlation ID generation (CORR-xxxxx)
  - Structured JSON audit logging
  - Real-time operational metrics tracking (p50/p95/p99 latency, decision rates, throughput)
  - Configurable simulated operational alert thresholds
"""

import time
import json
import logging
import uuid
import numpy as np
from datetime import datetime

logger = logging.getLogger("sentinelrisk.scoring")


def generate_correlation_id() -> str:
    """Generate a unique request tracing correlation ID."""
    return f"CORR-{uuid.uuid4().hex[:8].upper()}"


class OperationalMetricsTracker:
    """Tracks live operational metrics for risk evaluations."""

    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.cached_idempotent_requests = 0
        self.decision_counts = {"APPROVE": 0, "REVIEW": 0, "HOLD": 0}
        self.latencies_ms: list[float] = []
        self.dependency_failures = {
            "ml": 0,
            "graph": 0,
            "rules": 0,
            "policy": 0,
            "investigation": 0,
        }
        self.start_time = time.time()

        # Simulated alert thresholds
        self.alert_thresholds = {
            "max_p95_latency_ms": 100.0,
            "max_review_rate_pct": 5.0,
            "max_hold_rate_pct": 3.0,
            "max_error_rate_pct": 1.0,
            "max_dependency_failure_rate_pct": 2.0,
        }

    def record_evaluation(
        self,
        decision: str,
        total_latency_ms: float,
        dependency_statuses: dict[str, str],
        is_cached: bool = False,
        is_error: bool = False,
    ) -> None:
        """Record a completed risk evaluation."""
        self.total_requests += 1

        if is_error:
            self.failed_requests += 1
            return

        self.successful_requests += 1
        if is_cached:
            self.cached_idempotent_requests += 1

        if decision in self.decision_counts:
            self.decision_counts[decision] += 1

        self.latencies_ms.append(total_latency_ms)

        # Track dependency degradations
        for dep, st in dependency_statuses.items():
            if st in ("DEGRADED", "UNAVAILABLE", "FAILED"):
                self.dependency_failures[dep] = self.dependency_failures.get(dep, 0) + 1

    def get_summary(self) -> dict:
        """Compute operational summary and alert evaluation."""
        total = self.total_requests
        succ = self.successful_requests
        lats = self.latencies_ms

        if lats:
            p50 = float(np.percentile(lats, 50))
            p95 = float(np.percentile(lats, 95))
            p99 = float(np.percentile(lats, 99))
            avg_lat = float(np.mean(lats))
            min_lat = float(np.min(lats))
            max_lat = float(np.max(lats))
        else:
            p50 = p95 = p99 = avg_lat = min_lat = max_lat = 0.0

        appr_rate = (self.decision_counts["APPROVE"] / succ * 100.0) if succ > 0 else 0.0
        rev_rate = (self.decision_counts["REVIEW"] / succ * 100.0) if succ > 0 else 0.0
        hold_rate = (self.decision_counts["HOLD"] / succ * 100.0) if succ > 0 else 0.0
        err_rate = (self.failed_requests / total * 100.0) if total > 0 else 0.0

        elapsed_sec = max(0.1, time.time() - self.start_time)
        throughput_rps = round(total / elapsed_sec, 2)

        # Evaluate simulated alerts
        alerts = []
        if p95 > self.alert_thresholds["max_p95_latency_ms"] and len(lats) >= 10:
            alerts.append({
                "alert": "HIGH_P95_LATENCY",
                "severity": "WARNING",
                "message": f"p95 latency ({p95:.2f}ms) exceeds SLA budget ({self.alert_thresholds['max_p95_latency_ms']}ms)",
            })
        if rev_rate > self.alert_thresholds["max_review_rate_pct"] and succ >= 20:
            alerts.append({
                "alert": "ELEVATED_REVIEW_QUEUE",
                "severity": "WARNING",
                "message": f"Review rate ({rev_rate:.2f}%) exceeds operational threshold ({self.alert_thresholds['max_review_rate_pct']}%)",
            })
        if hold_rate > self.alert_thresholds["max_hold_rate_pct"] and succ >= 20:
            alerts.append({
                "alert": "ELEVATED_HOLD_RATE",
                "severity": "CRITICAL",
                "message": f"Hold intervention rate ({hold_rate:.2f}%) indicates potential active fraud surge",
            })
        if err_rate > self.alert_thresholds["max_error_rate_pct"] and total >= 10:
            alerts.append({
                "alert": "HIGH_ERROR_RATE",
                "severity": "CRITICAL",
                "message": f"System error rate ({err_rate:.2f}%) exceeds error budget",
            })

        return {
            "traffic": {
                "total_requests": total,
                "successful_requests": succ,
                "failed_requests": self.failed_requests,
                "cached_idempotent_requests": self.cached_idempotent_requests,
                "throughput_rps": throughput_rps,
            },
            "decisions": {
                "approve_count": self.decision_counts["APPROVE"],
                "review_count": self.decision_counts["REVIEW"],
                "hold_count": self.decision_counts["HOLD"],
                "approve_rate_pct": round(appr_rate, 2),
                "review_rate_pct": round(rev_rate, 2),
                "hold_rate_pct": round(hold_rate, 2),
            },
            "latencies": {
                "p50_ms": round(p50, 3),
                "p95_ms": round(p95, 3),
                "p99_ms": round(p99, 3),
                "mean_ms": round(avg_lat, 3),
                "min_ms": round(min_lat, 3),
                "max_ms": round(max_lat, 3),
            },
            "dependency_failures": self.dependency_failures,
            "active_alerts": alerts,
        }

    def reset(self) -> None:
        """Reset metrics tracker."""
        self.__init__()
