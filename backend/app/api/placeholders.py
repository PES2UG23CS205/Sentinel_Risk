"""
SentinelRisk — API Routers & Simulation Endpoints

Defines standard API routers. Contains the offline policy evaluation endpoint:
  POST /risk/evaluate -> Simulates policy engine evaluation without Razorpay integration.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.app.policy.engine import PolicyEngine

policy_engine = PolicyEngine()


def _placeholder_router(prefix: str, tag: str) -> APIRouter:
    """Create a placeholder router that returns not_implemented for GET /."""
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("/")
    async def placeholder():
        return {
            "status": "not_implemented",
            "stage": 1,
            "message": f"{tag} endpoints will be available in a future stage.",
        }

    return router


events_router = _placeholder_router("/events", "Events")
risk_router = _placeholder_router("/risk", "Risk")
cases_router = _placeholder_router("/cases", "Cases")
metrics_router = _placeholder_router("/metrics", "Metrics")
incidents_router = _placeholder_router("/incidents", "Incidents")
model_router = _placeholder_router("/model", "Model")


class RiskEvaluationRequest(BaseModel):
    transaction_id: str | int = Field(..., json_schema_extra={"example": 101})
    timestamp: str = Field(..., json_schema_extra={"example": "2025-03-15 14:30:00"})
    amount: float = Field(..., json_schema_extra={"example": 2500.0})
    ml_probability: float = Field(..., json_schema_extra={"example": 0.08})
    graph_ring_score: float = Field(0.0, json_schema_extra={"example": 0.0})
    graph_ring_candidate: int = Field(0, json_schema_extra={"example": 0})
    feature_context: dict = Field(default_factory=dict)
    rule_signals: list[str] = Field(default_factory=list)


@risk_router.post("/evaluate")
async def evaluate_risk(req: RiskEvaluationRequest):
    """
    Offline local simulation endpoint for evaluating transaction risk through the PolicyEngine.
    """
    record = policy_engine.evaluate(
        transaction_id=req.transaction_id,
        timestamp=req.timestamp,
        amount=req.amount,
        ml_probability=req.ml_probability,
        graph_ring_score=req.graph_ring_score,
        graph_ring_candidate=req.graph_ring_candidate,
        feature_context=req.feature_context,
        rule_signals=req.rule_signals,
    )
    return record.to_dict()
