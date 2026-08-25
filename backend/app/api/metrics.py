"""
SentinelRisk — Operational Observability & Metrics API

Provides real-time system performance, throughput, latency percentiles,
decision rate distributions, and active alert statuses.
"""

from fastapi import APIRouter
from backend.app.api.risk import risk_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/operations")
async def get_operational_metrics():
    """Retrieve live operational performance and alert metrics."""
    return risk_service.metrics.get_summary()


@router.post("/operations/reset")
async def reset_operational_metrics():
    """Reset live metrics tracker counters."""
    risk_service.metrics.reset()
    return {"status": "RESET", "message": "Operational metrics reset successfully."}
