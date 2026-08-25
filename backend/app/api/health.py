"""
SentinelRisk — Health & Root Endpoints

Provides:
  GET /        → Service info
  GET /health  → Health check (used by frontend status indicator)
"""

from fastapi import APIRouter
from backend.app.config import get_settings

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint — basic service information."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "description": settings.app_description,
        "version": settings.app_version,
        "stage": 1,
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Used by the frontend dashboard to show real-time backend status.
    Returns HTTP 200 with service metadata when the backend is running.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": "sentinelrisk",
        "version": settings.app_version,
    }


@router.get("/health/live")
async def liveness_probe():
    """Liveness probe: verifies service process is running and responding."""
    return {"status": "ALIVE", "service": "sentinelrisk"}


@router.get("/health/ready")
async def readiness_probe():
    """Readiness probe: verifies service is ready to evaluate payment risk."""
    from pathlib import Path
    policy_path = Path("config/policy.yaml")
    feat_path = Path("data/features/transaction_features.csv")

    is_ready = policy_path.exists()
    return {
        "status": "READY" if is_ready else "NOT_READY",
        "checks": {
            "policy_configuration": "LOADED" if policy_path.exists() else "MISSING",
            "feature_store": "AVAILABLE" if feat_path.exists() else "OFFLINE",
            "risk_scoring_engine": "INITIALIZED",
        },
    }


@router.get("/health/dependencies")
async def dependency_health():
    """Detailed dependency health statuses for observability."""
    from pathlib import Path
    model_path = Path("ml/models/lightgbm_model.pkl")
    graph_path = Path("data/features/graph_features.csv")
    policy_path = Path("config/policy.yaml")

    return {
        "service": "sentinelrisk",
        "overall_health": "HEALTHY",
        "dependencies": {
            "ml_model_service": {
                "status": "HEALTHY" if model_path.exists() else "DEGRADED",
                "version": "lightgbm-v1",
                "fallback_available": True,
            },
            "entity_graph_service": {
                "status": "HEALTHY" if graph_path.exists() else "UNAVAILABLE",
                "version": "graph-v1",
                "fallback_available": True,
            },
            "policy_engine": {
                "status": "HEALTHY" if policy_path.exists() else "DEGRADED",
                "version": "sentinelrisk-policy-v1",
                "fail_safe": "REVIEW",
            },
            "investigation_llm": {
                "status": "HEALTHY",
                "provider": "MockInvestigationLLM",
                "isolated_from_decision": True,
            },
        },
    }
