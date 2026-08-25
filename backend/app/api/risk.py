"""
SentinelRisk — Real-Time Production Risk Evaluation API

Provides high-throughput, low-latency transaction authorization endpoint:
  POST /risk/evaluate
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Any, Optional

from backend.app.scoring.realtime_service import RealtimeRiskService
from backend.app.scoring.validation import ValidationError
from backend.app.scoring.idempotency import IdempotencyConflictError

router = APIRouter(prefix="/risk", tags=["Risk"])
risk_service = RealtimeRiskService()


class RiskEvaluationRequest(BaseModel):
    transaction_id: str | int = Field(..., json_schema_extra={"example": "TXN-99882"})
    amount: float = Field(..., json_schema_extra={"example": 1450.00})
    timestamp: str = Field(..., json_schema_extra={"example": "2025-06-15 14:30:00"})
    customer_id: Optional[str | int] = Field("UNKNOWN", json_schema_extra={"example": "CUST_1042"})
    device_id: Optional[str | int] = Field("UNKNOWN", json_schema_extra={"example": "DEV_8821"})
    payment_instrument_id: Optional[str | int] = Field("UNKNOWN", json_schema_extra={"example": "PI_3319"})
    merchant_id: Optional[str | int] = Field("UNKNOWN", json_schema_extra={"example": "MERCH_09"})
    currency: Optional[str] = Field("INR", json_schema_extra={"example": "INR"})
    ml_probability: Optional[float] = Field(0.005, json_schema_extra={"example": 0.005})
    graph_ring_score: Optional[float] = Field(0.0, json_schema_extra={"example": 0.0})
    graph_ring_candidate: Optional[int] = Field(0, json_schema_extra={"example": 0})
    features: Optional[dict[str, Any]] = Field(default_factory=dict)
    feature_context: Optional[dict[str, Any]] = None


@router.post("/evaluate")
async def evaluate_transaction_risk(req: RiskEvaluationRequest):
    """
    Evaluate real-time risk for an incoming payment transaction.

    Performs request validation, idempotency caching, latency instrumentation,
    and returns authoritative tri-state decision (APPROVE / REVIEW / HOLD).
    """
    payload = req.model_dump()
    try:
        response = risk_service.evaluate_transaction(payload)
        return response
    except ValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        )
    except IdempotencyConflictError as ice:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(ice),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal risk evaluation error: {str(e)}",
        )
