"""
SentinelRisk — Data Lab Pydantic Models & Schemas

Defines schemas for:
  - File upload & preview
  - Automatic column detection & mapping
  - Data quality validation reports
  - Signal Availability Matrix (ensuring zero feature fabrication)
  - Dual-mode Assessment Execution (Quick Assessment vs Historical Replay)
  - Scored transaction results & aggregate analytics
  - Assessment persistence & export
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ColumnConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNMATCHED = "UNMATCHED"


class AssessmentMode(str, Enum):
    QUICK_ASSESSMENT = "QUICK_ASSESSMENT"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"


class AssessmentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DetectedColumn(BaseModel):
    original_name: str = Field(..., description="Original header name in uploaded CSV")
    suggested_field: Optional[str] = Field(None, description="Mapped canonical SentinelRisk field")
    confidence: ColumnConfidence = Field(ColumnConfidence.UNMATCHED, description="Detection confidence")
    detected_type: str = Field("string", description="Inferred data type (string, float, int, datetime, boolean)")
    null_count: int = Field(0, description="Count of empty/null values")
    sample_values: list[Any] = Field(default_factory=list, description="Sample non-null values")


class ColumnMappingRequest(BaseModel):
    mapping: dict[str, Optional[str]] = Field(
        ...,
        description="Dictionary mapping canonical SentinelRisk fields to original CSV column names"
    )


class ValidationIssue(BaseModel):
    severity: str = Field("WARNING", description="Severity: INFO, WARNING, ERROR")
    column: Optional[str] = Field(None, description="Related column name")
    message: str = Field(..., description="Human-readable description of the issue")
    affected_rows: int = Field(0, description="Number of rows affected")
    sample_row_indices: list[int] = Field(default_factory=list, description="Indices of sample rows")


class ValidationSummary(BaseModel):
    is_valid: bool = Field(True, description="True if dataset satisfies minimum requirements for assessment")
    total_rows: int = Field(0, description="Total rows in dataset")
    valid_rows: int = Field(0, description="Rows with valid minimum required fields")
    invalid_rows: int = Field(0, description="Rows with unrecoverable invalid data")
    has_timestamp: bool = Field(False, description="Whether timestamp column is successfully parsed")
    has_amount: bool = Field(False, description="Whether numeric amount column is successfully parsed")
    has_customer_id: bool = Field(False, description="Whether customer identifier is mapped")
    has_merchant_id: bool = Field(False, description="Whether merchant identifier is mapped")
    has_device_id: bool = Field(False, description="Whether device token is mapped")
    has_payment_instrument_id: bool = Field(False, description="Whether card/instrument token is mapped")
    has_ground_truth: bool = Field(False, description="Whether explicit ground truth fraud label is present")
    timestamp_range: Optional[tuple[str, str]] = Field(None, description="Earliest and latest parsed timestamps")
    is_chronological: bool = Field(True, description="Whether records are in strict chronological order")
    duplicate_transaction_ids: int = Field(0, description="Number of duplicate transaction IDs found")
    issues: list[ValidationIssue] = Field(default_factory=list, description="List of detected validation issues")


class SignalAvailabilityItem(BaseModel):
    signal_name: str = Field(..., description="Name of the SentinelRisk risk signal or component")
    category: str = Field(..., description="Category: Velocity, Amount Deviation, Identity, Graph, Merchant, ML")
    is_available: bool = Field(..., description="Whether signal can be legitimately computed from mapped data")
    required_fields: list[str] = Field(default_factory=list, description="Fields required to compute this signal")
    status_label: str = Field("AVAILABLE", description="AVAILABLE, PARTIAL, UNAVAILABLE")
    technical_rationale: str = Field(..., description="Explanation of availability or why it cannot be fabricated")


class SignalMatrixReport(BaseModel):
    available_count: int = Field(..., description="Total count of available signals")
    unavailable_count: int = Field(..., description="Total count of unavailable signals")
    available_signals: list[SignalAvailabilityItem] = Field(default_factory=list)
    unavailable_signals: list[SignalAvailabilityItem] = Field(default_factory=list)
    recommended_mode: AssessmentMode = Field(AssessmentMode.QUICK_ASSESSMENT)
    fabrication_policy_notice: str = Field(
        "SentinelRisk Core Principle: Unavailable signals are never fabricated or substituted with dummy zeros.",
        description="Notice confirming zero feature fabrication"
    )


class AssessmentRunRequest(BaseModel):
    mode: AssessmentMode = Field(AssessmentMode.QUICK_ASSESSMENT, description="Assessment execution mode")
    exclude_invalid_rows: bool = Field(True, description="Whether to exclude unparsable rows or fail")


class GroundTruthMetrics(BaseModel):
    has_ground_truth: bool = Field(False)
    ground_truth_fraud_count: int = Field(0)
    ground_truth_legit_count: int = Field(0)
    true_positives: int = Field(0)
    false_positives: int = Field(0)
    true_negatives: int = Field(0)
    false_negatives: int = Field(0)
    precision: float = Field(0.0)
    recall: float = Field(0.0)
    f1_score: float = Field(0.0)
    accuracy: float = Field(0.0)


class ScoredTransactionRecord(BaseModel):
    row_index: int
    transaction_id: str
    timestamp: str
    amount: float
    currency: str = "INR"
    customer_id: Optional[str] = None
    merchant_id: Optional[str] = None
    device_id: Optional[str] = None
    payment_instrument_id: Optional[str] = None
    risk_score: float = Field(..., description="Calibrated risk probability (0.0 - 1.0)")
    decision: str = Field(..., description="APPROVE, CHALLENGE, REVIEW, HOLD")
    primary_trigger: str = Field("APPROVED_BASELINE")
    challenge_type: Optional[str] = None
    decision_reason: str = Field(..., description="Interpretable explanation based on available signals")
    available_signals: list[str] = Field(default_factory=list)
    unavailable_signals: list[str] = Field(default_factory=list)
    ground_truth_fraud: Optional[int] = None
    features_computed: dict[str, Any] = Field(default_factory=dict)


class AssessmentAnalytics(BaseModel):
    total_transactions: int = Field(0)
    approved_count: int = Field(0)
    challenged_count: int = Field(0)
    review_count: int = Field(0)
    hold_count: int = Field(0)
    approval_rate_pct: float = Field(0.0)
    challenge_rate_pct: float = Field(0.0)
    review_rate_pct: float = Field(0.0)
    hold_rate_pct: float = Field(0.0)
    risk_flag_rate_pct: float = Field(0.0)
    total_volume: float = Field(0.0)
    amount_at_risk: float = Field(0.0)
    avg_risk_score: float = Field(0.0)
    max_risk_score: float = Field(0.0)
    score_distribution: dict[str, int] = Field(
        default_factory=lambda: {"0.0-0.1": 0, "0.1-0.25": 0, "0.25-0.5": 0, "0.5-0.75": 0, "0.75-1.0": 0}
    )
    decision_distribution: dict[str, int] = Field(
        default_factory=lambda: {"APPROVE": 0, "CHALLENGE": 0, "REVIEW": 0, "HOLD": 0}
    )
    top_risky_merchants: list[dict[str, Any]] = Field(default_factory=list)
    top_risky_customers: list[dict[str, Any]] = Field(default_factory=list)
    ground_truth_metrics: Optional[GroundTruthMetrics] = None


class AssessmentMetadata(BaseModel):
    assessment_id: str
    dataset_name: str
    file_size_bytes: int
    total_rows: int
    uploaded_at: str
    status: AssessmentStatus
    mode: Optional[AssessmentMode] = None
    column_mapping: dict[str, Optional[str]] = Field(default_factory=dict)
    validation_summary: Optional[ValidationSummary] = None
    signal_report: Optional[SignalMatrixReport] = None
    analytics: Optional[AssessmentAnalytics] = None
