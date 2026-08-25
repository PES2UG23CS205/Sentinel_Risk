"""
SentinelRisk — Investigation Agent Data Models

Defines the complete domain model for LLM-assisted fraud investigation:
  - Evidence items with unique IDs (EVID-xxx)
  - Structured findings with confidence & evidence grounding
  - Multi-hypothesis generation with supporting/contradicting citations
  - InvestigationContext and InvestigationReport
  - Case management entities (CaseStatus, CasePriority, AnalystNote, CaseHistoryEvent)
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingClassification(str, Enum):
    SUPPORTED = "SUPPORTED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class CasePriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EvidenceItem:
    """Atomic, structured piece of evidence gathered from risk systems."""
    evidence_id: str
    evidence_type: str  # 'transaction', 'ml_score', 'graph_topology', 'velocity', 'device', 'benign'
    source: str         # 'transaction_features', 'lightgbm_model', 'entity_graph', 'policy_engine'
    timestamp: str
    value: Any
    description: str

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source": self.source,
            "timestamp": str(self.timestamp),
            "value": self.value,
            "description": self.description,
        }


@dataclass
class Finding:
    """Specific factual observation or inference grounded in cited evidence."""
    finding_id: str
    statement: str
    evidence_ids: list[str]
    confidence: ConfidenceLevel
    classification: FindingClassification

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "statement": self.statement,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence.value if isinstance(self.confidence, ConfidenceLevel) else str(self.confidence),
            "classification": self.classification.value if isinstance(self.classification, FindingClassification) else str(self.classification),
        }


@dataclass
class Hypothesis:
    """Plausible explanation of observed behavior with evidence citations."""
    hypothesis_id: str
    hypothesis: str
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    confidence: ConfidenceLevel

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "hypothesis": self.hypothesis,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradicting_evidence_ids": self.contradicting_evidence_ids,
            "confidence": self.confidence.value if isinstance(self.confidence, ConfidenceLevel) else str(self.confidence),
        }


@dataclass
class TimelineEvent:
    """Chronological event leading up to the transaction."""
    timestamp: str
    event_type: str
    description: str
    entity_id: str

    def to_dict(self) -> dict:
        return {
            "timestamp": str(self.timestamp),
            "event_type": self.event_type,
            "description": self.description,
            "entity_id": str(self.entity_id),
        }


@dataclass
class InvestigationContext:
    """Controlled, normalized input payload provided to the Investigation LLM."""
    case_id: str
    transaction_id: int | str
    timestamp: str
    amount: float
    customer_id: int | str
    device_id: int | str
    payment_instrument_id: int | str
    merchant_id: int | str
    policy_decision: str
    policy_version: str
    ml_probability: float
    graph_ring_score: float
    graph_ring_candidate: int
    triggered_rules: list[str]
    evidence_items: list[EvidenceItem]
    timeline: list[TimelineEvent]
    related_entities: dict[str, list[str]]
    primary_trigger: str = "UNKNOWN"
    sanitized_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "transaction_id": self.transaction_id,
            "timestamp": str(self.timestamp),
            "amount": self.amount,
            "customer_id": str(self.customer_id),
            "device_id": str(self.device_id),
            "payment_instrument_id": str(self.payment_instrument_id),
            "merchant_id": str(self.merchant_id),
            "policy_decision": self.policy_decision,
            "policy_version": self.policy_version,
            "ml_probability": self.ml_probability,
            "graph_ring_score": self.graph_ring_score,
            "graph_ring_candidate": self.graph_ring_candidate,
            "triggered_rules": self.triggered_rules,
            "primary_trigger": self.primary_trigger,
            "evidence_items": [e.to_dict() for e in self.evidence_items],
            "timeline": [t.to_dict() for t in self.timeline],
            "related_entities": self.related_entities,
            "sanitized_metadata": self.sanitized_metadata,
        }


@dataclass
class InvestigationReport:
    """Strictly structured, validated investigation report output."""
    case_id: str
    policy_decision: str
    policy_version: str
    risk_summary: str
    evidence: list[EvidenceItem]
    findings: list[Finding]
    suspicious_signals: list[str]
    benign_signals: list[str]
    related_entities: dict[str, list[str]]
    timeline: list[TimelineEvent]
    hypotheses: list[Hypothesis]
    uncertainty: str
    recommended_next_steps: list[str]
    analyst_summary: str
    model_metadata: dict
    investigation_status: str = "COMPLETED"  # 'COMPLETED', 'FAILED', 'FALLBACK'

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "policy_decision": self.policy_decision,
            "policy_version": self.policy_version,
            "risk_summary": self.risk_summary,
            "evidence": [e.to_dict() for e in self.evidence],
            "findings": [f.to_dict() for f in self.findings],
            "suspicious_signals": self.suspicious_signals,
            "benign_signals": self.benign_signals,
            "related_entities": self.related_entities,
            "timeline": [t.to_dict() for t in self.timeline],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "uncertainty": self.uncertainty,
            "recommended_next_steps": self.recommended_next_steps,
            "analyst_summary": self.analyst_summary,
            "model_metadata": self.model_metadata,
            "investigation_status": self.investigation_status,
        }


@dataclass
class AnalystNote:
    """Human analyst note attached to a case."""
    note_id: str
    case_id: str
    timestamp: str
    analyst: str
    text: str

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "case_id": self.case_id,
            "timestamp": str(self.timestamp),
            "analyst": self.analyst,
            "text": self.text,
        }


@dataclass
class CaseHistoryEvent:
    """Audit log entry tracking the operational lifecycle of a case."""
    event_id: str
    case_id: str
    timestamp: str
    event_type: str
    details: str

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "case_id": self.case_id,
            "timestamp": str(self.timestamp),
            "event_type": self.event_type,
            "details": self.details,
        }


@dataclass
class InvestigationCase:
    """Analyst review queue case entity."""
    case_id: str
    transaction_id: int | str
    timestamp: str
    amount: float
    policy_decision: str
    priority: CasePriority
    priority_reason: str = "Standard policy evaluation criteria."
    customer_id: str | None = None
    merchant_id: str | None = None
    status: CaseStatus = CaseStatus.OPEN
    assigned_to: str | None = None
    resolution: str | None = None
    resolution_reason: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    report: InvestigationReport | None = None
    notes: list[AnalystNote] = field(default_factory=list)
    history: list[CaseHistoryEvent] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "transaction_id": self.transaction_id,
            "customer_id": self.customer_id,
            "merchant_id": self.merchant_id,
            "timestamp": str(self.timestamp),
            "amount": self.amount,
            "policy_decision": self.policy_decision,
            "priority": self.priority.value if isinstance(self.priority, CasePriority) else str(self.priority),
            "priority_reason": self.priority_reason,
            "status": self.status.value if isinstance(self.status, CaseStatus) else str(self.status),
            "assigned_to": self.assigned_to,
            "resolution": self.resolution,
            "resolution_reason": self.resolution_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "report": self.report.to_dict() if self.report else None,
            "notes": [n.to_dict() for n in self.notes],
            "history": [h.to_dict() for h in self.history],
        }
