"""
SentinelRisk — Data Lab REST API Router

Endpoints for self-service user transaction dataset ingestion, schema mapping,
data quality verification, signal matrix generation, dual-mode risk assessment,
transaction exploration, and results export.
"""

import io
import csv
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.app.data_lab.column_detector import ColumnDetector
from backend.app.data_lab.engine import DataLabAssessmentEngine
from backend.app.data_lab.models import (
    AssessmentAnalytics,
    AssessmentMetadata,
    AssessmentMode,
    AssessmentRunRequest,
    AssessmentStatus,
    ColumnMappingRequest,
    DetectedColumn,
    SignalMatrixReport,
    ValidationSummary,
)
from backend.app.data_lab.signal_matrix import generate_signal_matrix
from backend.app.data_lab.storage import (
    MAX_FILE_SIZE_BYTES,
    AssessmentStorage,
    sanitize_filename,
)
from backend.app.data_lab.validator import DataLabValidator

router = APIRouter(prefix="/data-lab", tags=["Data Lab"])

assessment_engine = DataLabAssessmentEngine()


class TextUploadPayload(BaseModel):
    content: str = Field(..., description="Raw CSV or JSON text content")
    dataset_name: Optional[str] = Field("user_transactions.csv", description="Dataset display filename")


def parse_csv_content(content: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse raw text CSV content into headers and list of row dicts."""
    f = io.StringIO(content.strip())
    reader = csv.reader(f)
    try:
        headers = next(reader)
    except StopIteration:
        return [], []

    # Clean headers (strip BOM, whitespace)
    headers = [h.replace("\ufeff", "").strip() for h in headers if h.strip()]
    if not headers:
        return [], []

    # Reset position and read with DictReader
    f.seek(0)
    dict_reader = csv.DictReader(f)
    rows = []
    for r in dict_reader:
        if any(v.strip() for v in r.values() if v is not None):
            rows.append(r)
    return headers, rows


def _process_dataset_content(filename: str, content: str):
    headers, raw_rows = parse_csv_content(content)
    if not headers or not raw_rows:
        raise HTTPException(
            status_code=400,
            detail="Empty or unparsable CSV dataset. Please provide a valid CSV with headers.",
        )

    # 1. Store dataset in isolated directory
    meta = AssessmentStorage.create_assessment(
        dataset_name=filename,
        content=content,
        headers=headers,
        raw_rows=raw_rows,
        file_size_bytes=len(content.encode("utf-8")),
    )

    # 2. Auto-detect columns
    detected_cols = ColumnDetector.detect_columns(headers, raw_rows[:20])
    default_mapping = ColumnDetector.get_default_mapping(detected_cols)

    # 3. Perform initial validation
    val_report = DataLabValidator.validate_dataset(raw_rows, default_mapping)

    # 4. Generate initial signal availability matrix
    signal_report = generate_signal_matrix(val_report, default_mapping)

    # 5. Update and persist metadata
    meta.status = AssessmentStatus.VALIDATED
    meta.column_mapping = default_mapping
    meta.validation_summary = val_report
    meta.signal_report = signal_report
    AssessmentStorage.save_metadata(meta)

    return {
        "assessment_id": meta.assessment_id,
        "dataset_name": meta.dataset_name,
        "total_rows": meta.total_rows,
        "headers": headers,
        "detected_columns": [c.model_dump() for c in detected_cols],
        "inferred_mapping": default_mapping,
        "validation_summary": val_report.model_dump(),
        "signal_report": signal_report.model_dump(),
    }


@router.post("/upload")
async def upload_dataset_file(file: UploadFile = File(...)):
    """Upload a transaction CSV dataset via multipart form-data."""
    filename = file.filename or "uploaded_dataset.csv"
    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed limit ({MAX_FILE_SIZE_BYTES // (1024*1024)} MB).",
        )
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = content_bytes.decode("latin-1", errors="replace")

    return _process_dataset_content(filename, content)


@router.post("/upload-text")
async def upload_dataset_text(payload: TextUploadPayload):
    """Upload a transaction CSV dataset via JSON text content."""
    filename = payload.dataset_name or "user_transactions.csv"
    content = payload.content
    if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Content size exceeds maximum allowed limit ({MAX_FILE_SIZE_BYTES // (1024*1024)} MB).",
        )
    return _process_dataset_content(filename, content)


@router.post("/demo-load")
async def load_demo_example_dataset():
    """
    Load the built-in demo dataset (data/demo/user_upload_example.csv) into a new assessment.
    """
    demo_path = Path("data/demo/user_upload_example.csv")
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="Demo example dataset not found.")

    with open(demo_path, "r", encoding="utf-8") as f:
        content = f.read()

    headers, raw_rows = parse_csv_content(content)
    meta = AssessmentStorage.create_assessment(
        dataset_name="user_upload_example.csv (Demo)",
        content=content,
        headers=headers,
        raw_rows=raw_rows,
        file_size_bytes=len(content.encode("utf-8")),
    )

    detected_cols = ColumnDetector.detect_columns(headers, raw_rows[:20])
    default_mapping = ColumnDetector.get_default_mapping(detected_cols)
    val_report = DataLabValidator.validate_dataset(raw_rows, default_mapping)
    signal_report = generate_signal_matrix(val_report, default_mapping)

    meta.status = AssessmentStatus.VALIDATED
    meta.column_mapping = default_mapping
    meta.validation_summary = val_report
    meta.signal_report = signal_report
    AssessmentStorage.save_metadata(meta)

    return {
        "assessment_id": meta.assessment_id,
        "dataset_name": meta.dataset_name,
        "total_rows": meta.total_rows,
        "file_size_bytes": meta.file_size_bytes,
        "uploaded_at": meta.uploaded_at,
        "headers": headers,
        "preview_rows": raw_rows[:10],
        "detected_columns": [c.model_dump() for c in detected_cols],
        "inferred_mapping": default_mapping,
        "validation_summary": val_report.model_dump(),
        "signal_report": signal_report.model_dump(),
    }


@router.get("/history")
async def list_assessment_history():
    """
    List all previous user assessments ordered by upload timestamp.
    """
    history = AssessmentStorage.list_history()
    return {"assessments": [m.model_dump() for m in history]}


@router.get("/example-dataset")
async def get_example_dataset():
    """
    Download the sample demo CSV for user testing.
    """
    demo_path = Path("data/demo/user_upload_example.csv")
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="Demo dataset not found.")
    return FileResponse(
        demo_path,
        media_type="text/csv",
        filename="sentinelrisk_demo_transactions.csv",
    )


@router.get("/{assessment_id}")
async def get_assessment_details(assessment_id: str):
    """
    Retrieve metadata, column mappings, validation reports, and analytics for an assessment.
    """
    meta = AssessmentStorage.get_metadata(assessment_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found.")

    raw_rows = AssessmentStorage.load_raw_rows(assessment_id)
    headers = list(raw_rows[0].keys()) if raw_rows else []
    detected_cols = ColumnDetector.detect_columns(headers, raw_rows[:20]) if raw_rows else []

    return {
        "metadata": meta.model_dump(),
        "headers": headers,
        "preview_rows": raw_rows[:10],
        "detected_columns": [c.model_dump() for c in detected_cols],
    }


@router.post("/{assessment_id}/mapping")
async def update_column_mapping(assessment_id: str, payload: ColumnMappingRequest):
    """
    Update column mapping overrides and re-evaluate validation & signal matrix.
    """
    meta = AssessmentStorage.get_metadata(assessment_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found.")

    raw_rows = AssessmentStorage.load_raw_rows(assessment_id)
    if not raw_rows:
        raise HTTPException(status_code=400, detail="No raw data found for assessment.")

    # Re-validate with new mapping
    val_report = DataLabValidator.validate_dataset(raw_rows, payload.mapping)
    signal_report = generate_signal_matrix(val_report, payload.mapping)

    meta.column_mapping = payload.mapping
    meta.validation_summary = val_report
    meta.signal_report = signal_report
    AssessmentStorage.save_metadata(meta)

    return {
        "assessment_id": assessment_id,
        "column_mapping": meta.column_mapping,
        "validation_summary": val_report.model_dump(),
        "signal_report": signal_report.model_dump(),
    }


@router.post("/{assessment_id}/run")
async def run_assessment_scoring(assessment_id: str, req: AssessmentRunRequest):
    """
    Execute risk scoring and quad-state policy decisions on the validated dataset.
    """
    meta = AssessmentStorage.get_metadata(assessment_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found.")

    raw_rows = AssessmentStorage.load_raw_rows(assessment_id)
    if not raw_rows:
        raise HTTPException(status_code=400, detail="No dataset rows to score.")

    mapping = meta.column_mapping or {}
    val_report = meta.validation_summary or DataLabValidator.validate_dataset(raw_rows, mapping)

    if not val_report.is_valid:
        raise HTTPException(
            status_code=422,
            detail="Dataset is not valid for assessment. Required fields (amount, timestamp) must be mapped.",
        )

    meta.status = AssessmentStatus.RUNNING
    meta.mode = req.mode
    AssessmentStorage.save_metadata(meta)

    # Run assessment engine
    try:
        analytics, scored_txns = assessment_engine.run_assessment(
            raw_rows=raw_rows,
            mapping=mapping,
            validation=val_report,
            mode=req.mode,
            exclude_invalid_rows=req.exclude_invalid_rows,
        )
        AssessmentStorage.save_results(assessment_id, analytics, scored_txns)
    except Exception as e:
        meta.status = AssessmentStatus.FAILED
        AssessmentStorage.save_metadata(meta)
        raise HTTPException(status_code=500, detail=f"Assessment run error: {str(e)}")

    return {
        "assessment_id": assessment_id,
        "status": "COMPLETED",
        "mode": req.mode,
        "analytics": analytics.model_dump(),
        "scored_transactions_count": len(scored_txns),
        "preview_scored_txns": [t.model_dump() for t in scored_txns[:10]],
    }


@router.get("/{assessment_id}/results")
async def get_assessment_results(assessment_id: str):
    """
    Retrieve executive analytics, decision charts data, and ground-truth metrics.
    """
    meta = AssessmentStorage.get_metadata(assessment_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found.")

    if not meta.analytics:
        raise HTTPException(status_code=400, detail="Assessment has not been run yet.")

    return {
        "metadata": meta.model_dump(),
        "analytics": meta.analytics.model_dump(),
    }


@router.get("/{assessment_id}/transactions")
async def get_assessment_transactions(
    assessment_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    decision: Optional[str] = Query(None, description="Filter: ALL, APPROVE, CHALLENGE, REVIEW, HOLD"),
    search: Optional[str] = Query(None, description="Search transaction_id, customer, merchant, or reason"),
):
    """
    Query paginated and filtered scored transactions.
    """
    records, total_matching = AssessmentStorage.load_scored_transactions(
        assessment_id=assessment_id,
        limit=limit,
        offset=offset,
        decision_filter=decision,
        search_query=search,
    )
    return {
        "assessment_id": assessment_id,
        "total_matching": total_matching,
        "limit": limit,
        "offset": offset,
        "transactions": records,
    }


@router.get("/{assessment_id}/export/csv")
async def export_scored_csv(assessment_id: str):
    """
    Download scored transactions CSV file.
    """
    asm_dir = AssessmentStorage.get_assessment_dir(assessment_id)
    if not asm_dir:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    csv_file = asm_dir / "scored_transactions.csv"
    if not csv_file.exists():
        raise HTTPException(status_code=400, detail="Scored transactions not yet available. Run assessment first.")

    meta = AssessmentStorage.get_metadata(assessment_id)
    out_name = f"sentinelrisk_scored_{meta.dataset_name if meta else assessment_id}.csv"
    return FileResponse(csv_file, media_type="text/csv", filename=sanitize_filename(out_name))


@router.get("/{assessment_id}/export/json")
async def export_summary_json(assessment_id: str):
    """
    Download complete assessment summary as JSON.
    """
    meta = AssessmentStorage.get_metadata(assessment_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    return meta.model_dump()


@router.delete("/{assessment_id}")
async def delete_assessment_dataset(assessment_id: str):
    """
    Permanently delete the user-uploaded dataset and its assessment results.
    """
    success = AssessmentStorage.delete_assessment(assessment_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found.")
    return {"status": "DELETED", "assessment_id": assessment_id}
