"""
SentinelRisk — Data Lab Isolated Storage & Assessment Persistence Manager

Guarantees:
  - Complete isolation from benchmark and training datasets.
  - Safe file size limits and filename sanitization.
  - Full CRUD operations on user assessments.
  - Clean deletion of user-uploaded data.
"""

import os
import re
import json
import uuid
import shutil
import csv
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from backend.app.utils.timezone import utc_now_iso, parse_and_standardize_utc
from backend.app.data_lab.models import (
    AssessmentMetadata,
    AssessmentStatus,
    AssessmentAnalytics,
    ScoredTransactionRecord,
    ValidationSummary,
    SignalMatrixReport,
)

# Base isolated directory for user assessments
USER_ASSESSMENTS_DIR = Path("data/user_assessments")
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def sanitize_filename(filename: str) -> str:
    """Sanitize user-provided filename to prevent path traversal or special character injection."""
    clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    clean = re.sub(r"\.\.+", ".", clean)  # prevent ..
    return clean[:100] or "user_dataset.csv"


class AssessmentStorage:
    """Manages filesystem persistence and isolation for Data Lab user assessments."""

    @classmethod
    def _ensure_base_dir(cls) -> Path:
        USER_ASSESSMENTS_DIR.mkdir(parents=True, exist_ok=True)
        return USER_ASSESSMENTS_DIR

    @classmethod
    def create_assessment(
        cls,
        dataset_name: str,
        content: str,
        headers: list[str],
        raw_rows: list[dict[str, Any]],
        file_size_bytes: int,
    ) -> AssessmentMetadata:
        """
        Create a new isolated assessment workspace directory and persist raw dataset.
        """
        cls._ensure_base_dir()
        assessment_id = f"ASM-{uuid.uuid4().hex[:8].upper()}"
        asm_dir = USER_ASSESSMENTS_DIR / assessment_id
        asm_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename(dataset_name)

        # Save raw content
        raw_path = asm_dir / "raw_dataset.csv"
        with open(raw_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

        meta = AssessmentMetadata(
            assessment_id=assessment_id,
            dataset_name=safe_name,
            file_size_bytes=file_size_bytes,
            total_rows=len(raw_rows),
            uploaded_at=utc_now_iso(),
            status=AssessmentStatus.UPLOADED,
        )

        cls.save_metadata(meta)
        return meta

    @classmethod
    def get_assessment_dir(cls, assessment_id: str) -> Optional[Path]:
        """Return path to assessment directory if it exists and is safe."""
        safe_id = sanitize_filename(assessment_id)
        target = USER_ASSESSMENTS_DIR / safe_id
        if target.exists() and target.is_dir():
            return target
        return None

    @classmethod
    def save_metadata(cls, meta: AssessmentMetadata) -> None:
        """Save assessment metadata JSON."""
        asm_dir = cls.get_assessment_dir(meta.assessment_id)
        if not asm_dir:
            return
        meta_file = asm_dir / "metadata.json"
        # Ensure uploaded_at is in standard UTC ISO-8601 format
        if meta.uploaded_at:
            meta.uploaded_at = parse_and_standardize_utc(meta.uploaded_at) or meta.uploaded_at
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(meta.model_dump_json(indent=2))

    @classmethod
    def get_metadata(cls, assessment_id: str) -> Optional[AssessmentMetadata]:
        """Load assessment metadata JSON with legacy naive timestamp auto-migration."""
        asm_dir = cls.get_assessment_dir(assessment_id)
        if not asm_dir:
            return None
        meta_file = asm_dir / "metadata.json"
        if not meta_file.exists():
            return None
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Auto-migrate legacy naive UTC timestamps to ISO-8601 UTC
                if "uploaded_at" in data and data["uploaded_at"]:
                    data["uploaded_at"] = parse_and_standardize_utc(data["uploaded_at"])
                return AssessmentMetadata(**data)
        except Exception:
            return None

    @classmethod
    def load_raw_rows(cls, assessment_id: str) -> list[dict[str, Any]]:
        """Load raw rows from the assessment's saved raw CSV."""
        asm_dir = cls.get_assessment_dir(assessment_id)
        if not asm_dir:
            return []
        raw_path = asm_dir / "raw_dataset.csv"
        if not raw_path.exists():
            return []
        rows = []
        with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows

    @classmethod
    def save_results(
        cls,
        assessment_id: str,
        analytics: AssessmentAnalytics,
        scored_txns: list[ScoredTransactionRecord],
    ) -> None:
        """Save scored transactions CSV and assessment analytics JSON."""
        asm_dir = cls.get_assessment_dir(assessment_id)
        if not asm_dir:
            return

        # 1. Save Analytics
        analytics_file = asm_dir / "analytics.json"
        with open(analytics_file, "w", encoding="utf-8") as f:
            f.write(analytics.model_dump_json(indent=2))

        # 2. Save Scored Transactions CSV
        csv_file = asm_dir / "scored_transactions.csv"
        if scored_txns:
            fieldnames = [
                "row_index", "transaction_id", "timestamp", "amount", "currency",
                "customer_id", "merchant_id", "device_id", "payment_instrument_id",
                "risk_score", "decision", "primary_trigger", "challenge_type",
                "decision_reason", "available_signals", "ground_truth_fraud"
            ]
            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for st in scored_txns:
                    row_dict = st.model_dump()
                    row_dict["available_signals"] = "; ".join(st.available_signals)
                    writer.writerow(row_dict)

        # 3. Update metadata
        meta = cls.get_metadata(assessment_id)
        if meta:
            meta.status = AssessmentStatus.COMPLETED
            meta.analytics = analytics
            cls.save_metadata(meta)

    @classmethod
    def load_scored_transactions(
        cls,
        assessment_id: str,
        limit: int = 100,
        offset: int = 0,
        decision_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Load, filter, and paginate scored transactions."""
        asm_dir = cls.get_assessment_dir(assessment_id)
        if not asm_dir:
            return [], 0
        csv_file = asm_dir / "scored_transactions.csv"
        if not csv_file.exists():
            return [], 0

        filtered = []
        with open(csv_file, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if decision_filter and decision_filter.upper() != "ALL":
                    if row.get("decision", "").upper() != decision_filter.upper():
                        continue
                if search_query:
                    q = search_query.lower()
                    txn_id = str(row.get("transaction_id", "")).lower()
                    cust_id = str(row.get("customer_id", "")).lower()
                    merch_id = str(row.get("merchant_id", "")).lower()
                    reason = str(row.get("decision_reason", "")).lower()
                    if q not in txn_id and q not in cust_id and q not in merch_id and q not in reason:
                        continue
                filtered.append(row)

        total_matching = len(filtered)
        paginated = filtered[offset : offset + limit]
        return paginated, total_matching

    @classmethod
    def list_history(cls) -> list[AssessmentMetadata]:
        """List all previous user assessments ordered by upload timestamp descending."""
        cls._ensure_base_dir()
        history = []
        for p in USER_ASSESSMENTS_DIR.iterdir():
            if p.is_dir():
                meta = cls.get_metadata(p.name)
                if meta:
                    history.append(meta)
        history.sort(key=lambda m: m.uploaded_at, reverse=True)
        return history

    @classmethod
    def delete_assessment(cls, assessment_id: str) -> bool:
        """Permanently delete an assessment directory and its contents."""
        asm_dir = cls.get_assessment_dir(assessment_id)
        if asm_dir and asm_dir.exists():
            shutil.rmtree(asm_dir, ignore_errors=True)
            return True
        return False
