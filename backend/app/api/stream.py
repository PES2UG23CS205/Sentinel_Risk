"""
SentinelRisk — Real-Time Ingestion & Streaming API

Provides endpoints for:
  - CSV/JSON upload, preview, and schema mapping
  - External dataset (Fraud Detection Handbook) metadata & chunked loading
  - Live session lifecycle (Start, Pause, Resume, Stop, Speed, Clear)
  - Single transaction interactive evaluation
  - Live state polling and Server-Sent Events (SSE) streaming
"""

import asyncio
import json
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.ingestion.schema import NormalizedTransaction, SchemaMapping, infer_schema_mapping
from backend.app.ingestion.validator import DatasetValidator, ValidationReport
from backend.app.ingestion.session_manager import LiveSessionManager
from backend.app.external_data.fraud_handbook_loader import FraudHandbookLoader
from backend.app.api.cases import case_manager

router = APIRouter(prefix="/stream", tags=["Streaming & Ingestion"])

# Global session manager instance sharing the central case_manager
live_session_manager = LiveSessionManager(case_manager=case_manager)
fraud_handbook_loader = FraudHandbookLoader()


class UploadPayload(BaseModel):
    content: str = Field(..., description="Raw CSV or JSON text content")
    file_type: str = Field("csv", description="File format ('csv', 'json', 'jsonl')")
    source_name: Optional[str] = Field("Uploaded Data", description="Display name for data source")


class ValidatePayload(BaseModel):
    content: str = Field(..., description="Raw CSV or JSON text content")
    file_type: str = Field("csv", description="File format")
    mapping: Optional[dict[str, Optional[str]]] = Field(None, description="Custom column mapping")


class SessionStartPayload(BaseModel):
    content: str = Field(..., description="Raw CSV or JSON text content")
    file_type: str = Field("csv", description="File format")
    source_name: Optional[str] = Field("User Transactions", description="Session data source name")
    mapping: Optional[dict[str, Optional[str]]] = Field(None, description="Custom column mapping")


class ExternalDatasetLoadPayload(BaseModel):
    limit: Optional[int] = Field(1000, ge=1, le=50000, description="Max records to load for replay (e.g., 1000, 5000, 10000)")
    start_date: Optional[str] = Field(None, description="Optional start date filter (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Optional end date filter (YYYY-MM-DD)")


class SpeedPayload(BaseModel):
    speed: float = Field(1.0, ge=0.5, le=10.0, description="Playback speed multiplier")


@router.get("/external/fraud-handbook/metadata")
@router.get("/external/fraud-handbook/stats")
async def get_fraud_handbook_metadata():
    """
    Return complete metadata, file counts, date ranges, and schema compatibility
    for the Fraud Detection Handbook simulated transaction dataset.
    """
    metadata = fraud_handbook_loader.get_dataset_metadata()
    return metadata


@router.post("/external/fraud-handbook/load")
async def load_fraud_handbook_stream(payload: ExternalDatasetLoadPayload):
    """
    Load a chronological slice of the Fraud Detection Handbook dataset into the live streaming session.
    """
    records = fraud_handbook_loader.load_transactions(
        limit=payload.limit or 1000,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    if not records:
        raise HTTPException(
            status_code=404,
            detail="No records found in external dataset matching the criteria.",
        )

    source_label = f"Fraud Detection Handbook ({len(records):,} txns)"
    live_session_manager.load_dataset(records, source_name=source_label)

    return {
        "status": "LOADED",
        "session_id": live_session_manager.session_id,
        "source_name": live_session_manager.source_name,
        "rows_loaded": len(records),
        "state": live_session_manager.get_state(),
    }


@router.post("/upload/preview")
async def preview_upload(payload: UploadPayload):
    """
    Parse uploaded content and return detected schema, columns, and initial preview rows.
    """
    headers, raw_rows = DatasetValidator.parse_raw_records(payload.content, payload.file_type)
    if not raw_rows:
        raise HTTPException(status_code=400, detail="Empty or unparsable dataset content.")

    inferred_mapping = infer_schema_mapping(headers)
    
    return {
        "source_name": payload.source_name,
        "total_rows": len(raw_rows),
        "columns": headers,
        "inferred_mapping": inferred_mapping.model_dump(),
        "preview_raw_rows": raw_rows[:10],
    }


@router.post("/validate")
async def validate_dataset(payload: ValidatePayload):
    """
    Validate dataset rows against column mapping and return comprehensive validation report.
    """
    headers, raw_rows = DatasetValidator.parse_raw_records(payload.content, payload.file_type)
    if not raw_rows:
        raise HTTPException(status_code=400, detail="Empty dataset.")

    mapping_obj = None
    if payload.mapping:
        mapping_obj = SchemaMapping(**payload.mapping)

    report = DatasetValidator.validate_and_normalize(raw_rows, mapping=mapping_obj, headers=headers)
    return report.model_dump()


@router.post("/session/start")
async def start_session(payload: SessionStartPayload):
    """
    Validate rows and load into active live streaming session.
    """
    headers, raw_rows = DatasetValidator.parse_raw_records(payload.content, payload.file_type)
    if not raw_rows:
        raise HTTPException(status_code=400, detail="Cannot start session with empty data.")

    mapping_obj = SchemaMapping(**payload.mapping) if payload.mapping else None
    report = DatasetValidator.validate_and_normalize(raw_rows, mapping=mapping_obj, headers=headers)

    if report.valid_rows_count == 0:
        raise HTTPException(status_code=422, detail="No valid rows could be parsed from data.")

    live_session_manager.load_dataset(report.valid_rows, source_name=payload.source_name or "Uploaded Dataset")
    
    return {
        "status": "LOADED",
        "session_id": live_session_manager.session_id,
        "valid_rows_loaded": report.valid_rows_count,
        "invalid_rows_skipped": report.invalid_rows_count,
        "state": live_session_manager.get_state(),
    }


@router.post("/start")
async def stream_start():
    """Start streaming playback."""
    live_session_manager.status = "STREAMING"
    return {"status": "STREAMING", "session_id": live_session_manager.session_id}


@router.post("/pause")
async def stream_pause():
    """Pause streaming playback."""
    live_session_manager.status = "PAUSED"
    return {"status": "PAUSED", "session_id": live_session_manager.session_id}


@router.post("/resume")
async def stream_resume():
    """Resume streaming playback."""
    live_session_manager.status = "STREAMING"
    return {"status": "STREAMING", "session_id": live_session_manager.session_id}


@router.post("/stop")
async def stream_stop():
    """Stop streaming playback."""
    live_session_manager.status = "STOPPED"
    return {"status": "STOPPED", "session_id": live_session_manager.session_id}


@router.post("/speed")
async def set_stream_speed(payload: SpeedPayload):
    """Set streaming speed multiplier."""
    live_session_manager.speed = payload.speed
    return {"speed": live_session_manager.speed}


@router.post("/step")
async def step_stream_event():
    """
    Process and return the next single event in the loaded dataset stream.
    """
    event = live_session_manager.step_stream()
    return {
        "event": event,
        "state": live_session_manager.get_state(),
    }


@router.post("/evaluate-single")
async def evaluate_single_transaction(txn: NormalizedTransaction):
    """
    Evaluate an ad-hoc single transaction through the live pipeline.
    """
    event = live_session_manager.evaluate_normalized_transaction(txn)
    return {
        "event": event,
        "state": live_session_manager.get_state(),
    }


@router.get("/live-state")
async def get_live_state():
    """Retrieve current live session state and counters."""
    return live_session_manager.get_state()


@router.post("/clear")
async def clear_session_data():
    """Clear all session transaction state for data privacy."""
    live_session_manager.clear_session()
    return {"status": "CLEARED", "session_id": live_session_manager.session_id}


@router.get("/events")
async def stream_events_sse():
    """
    Server-Sent Events (SSE) stream endpoint for live real-time web delivery.
    """
    async def event_generator():
        while True:
            if live_session_manager.status == "STREAMING":
                event = live_session_manager.step_stream()
                if event:
                    state = live_session_manager.get_state()
                    msg = {"type": "TRANSACTION_EVENT", "event": event, "state": state}
                    yield f"data: {json.dumps(msg)}\n\n"
                else:
                    msg = {"type": "STREAM_FINISHED", "state": live_session_manager.get_state()}
                    yield f"data: {json.dumps(msg)}\n\n"
                    break
            
            # Respect playback speed (base delay / speed)
            base_delay = 1.0
            delay = max(0.05, base_delay / max(0.1, live_session_manager.speed))
            await asyncio.sleep(delay)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
