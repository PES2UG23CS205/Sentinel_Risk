"""
SentinelRisk — Analyst Review Queue & Investigation Case API

Provides endpoints for:
  - Listing analyst investigation cases
  - Retrieving detailed case reports, evidence, and audit histories
  - Triggering on-demand LLM investigations
  - Appending analyst notes and updating case lifecycle statuses
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from backend.app.investigation.models import CaseStatus, CasePriority
from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.agent import InvestigationAgent

router = APIRouter(prefix="/cases", tags=["Cases"])

# Global in-memory CaseManager instance for API
case_manager = CaseManager(InvestigationAgent())


class AnalystNoteRequest(BaseModel):
    analyst: str = Field("Analyst_1", json_schema_extra={"example": "Risk_Analyst_Priya"})
    text: str = Field(..., json_schema_extra={"example": "Verified with customer; device recognized."})


class CaseStatusUpdateRequest(BaseModel):
    status: CaseStatus = Field(..., json_schema_extra={"example": "RESOLVED"})
    details: Optional[str] = Field("", json_schema_extra={"example": "Resolved after phone verification."})


class CaseCreationRequest(BaseModel):
    transaction_id: str | int = Field(..., json_schema_extra={"example": 2557})
    timestamp: str = Field(..., json_schema_extra={"example": "2025-01-30 21:41:22"})
    amount: float = Field(..., json_schema_extra={"example": 96.32})
    decision: str = Field("HOLD", json_schema_extra={"example": "HOLD"})
    ml_probability: float = Field(0.9995, json_schema_extra={"example": 0.9995})
    graph_ring_score: float = Field(0.0, json_schema_extra={"example": 0.0})
    transaction_data: dict = Field(default_factory=dict)
    graph_data: dict = Field(default_factory=dict)


@router.get("")
@router.get("/")
async def list_cases(
    status: Optional[CaseStatus] = Query(None, description="Filter by case status"),
    priority: Optional[CasePriority] = Query(None, description="Filter by case priority"),
):
    """List investigation cases with optional status and priority filtering."""
    cases = case_manager.get_cases(status=status, priority=priority)
    return {
        "total_cases": len(cases),
        "cases": [c.to_dict() for c in cases],
    }


@router.post("")
@router.post("/")
async def create_case(req: CaseCreationRequest):
    """Manually create or enqueue a case in the review queue."""
    dec_record = {
        "transaction_id": req.transaction_id,
        "timestamp": req.timestamp,
        "amount": req.amount,
        "decision": req.decision,
        "ml_probability": req.ml_probability,
        "graph_ring_score": req.graph_ring_score,
    }
    case = case_manager.create_case_from_decision(
        decision_record=dec_record,
        transaction_data=req.transaction_data or {"transaction_id": req.transaction_id, "amount": req.amount},
        graph_data=req.graph_data,
    )
    if not case:
        raise HTTPException(status_code=400, detail="Cannot create case for APPROVE decision.")
    return case.to_dict()


class CaseAssignRequest(BaseModel):
    analyst: str = Field("Risk_Analyst_Priya", json_schema_extra={"example": "Risk_Analyst_Priya"})


class CaseResolutionRequest(BaseModel):
    analyst: str = Field("Risk_Analyst_Priya", json_schema_extra={"example": "Risk_Analyst_Priya"})
    resolution: str = Field("CONFIRMED_FRAUD", json_schema_extra={"example": "CONFIRMED_FRAUD"})
    reason: Optional[str] = Field("", json_schema_extra={"example": "Customer confirmed device unauthorized."})


@router.get("/metrics/feedback")
async def get_feedback_metrics():
    """Retrieve aggregate analyst confirmation and false positive metrics."""
    return case_manager.get_feedback_metrics()


@router.get("/{case_id}")
async def get_case_details(case_id: str):
    """Retrieve complete case details, investigation report, notes, and audit history."""
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return case.to_dict()


@router.post("/{case_id}/investigate")
async def run_case_investigation(case_id: str):
    """Trigger on-demand evidence-grounded LLM investigation for a case."""
    try:
        report = case_manager.investigate_case(case_id)
        return report.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(e)}")


@router.post("/{case_id}/assign")
async def assign_case(case_id: str, req: CaseAssignRequest):
    """Assign case to a specific human analyst."""
    try:
        case = case_manager.assign_case(case_id, analyst=req.analyst)
        return case.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")


@router.post("/{case_id}/notes")
async def add_analyst_note(case_id: str, req: AnalystNoteRequest):
    """Append a human analyst note to the case audit log."""
    try:
        note = case_manager.add_note(case_id, analyst=req.analyst, text=req.text)
        return note.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")


@router.post("/{case_id}/confirm-fraud")
async def confirm_fraud_case(case_id: str, req: CaseResolutionRequest):
    """Mark case as confirmed fraud and store feedback."""
    try:
        case = case_manager.confirm_fraud(case_id, analyst=req.analyst, notes=req.reason or "")
        return case.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")


@router.post("/{case_id}/false-positive")
async def mark_false_positive_case(case_id: str, req: CaseResolutionRequest):
    """Mark case as false positive and store feedback."""
    try:
        case = case_manager.mark_false_positive(case_id, analyst=req.analyst, notes=req.reason or "")
        return case.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")


@router.post("/{case_id}/resolve")
async def resolve_case(case_id: str, req: CaseResolutionRequest):
    """Resolve case with custom resolution."""
    try:
        case = case_manager.resolve_case(
            case_id,
            analyst=req.analyst,
            resolution=req.resolution,
            reason=req.reason or "",
        )
        return case.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")


@router.post("/{case_id}/dismiss")
async def dismiss_case(case_id: str, req: CaseResolutionRequest):
    """Dismiss case as benign."""
    try:
        case = case_manager.dismiss_case(case_id, analyst=req.analyst, reason=req.reason or "")
        return case.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")


@router.post("/{case_id}/escalate")
async def escalate_case(case_id: str, req: CaseResolutionRequest):
    """Escalate case for executive / compliance triage."""
    try:
        case = case_manager.escalate_case(case_id, analyst=req.analyst, reason=req.reason or "")
        return case.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")


@router.post("/{case_id}/status")
async def update_case_status(case_id: str, req: CaseStatusUpdateRequest):
    """Update case lifecycle status (e.g., OPEN -> INVESTIGATING -> ESCALATED -> RESOLVED)."""
    try:
        case = case_manager.update_status(case_id, new_status=req.status, details=req.details or "")
        return case.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
