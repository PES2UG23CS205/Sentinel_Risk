"""
SentinelRisk — ORM Models (Stage 1 Foundation)

Defines the core database schema for SentinelRisk.
These tables form the foundation that later stages will extend
(e.g., adding risk_score to transactions, fraud labels, etc.).

Tables:
    - Merchant       : Payment-accepting businesses
    - Customer        : End users making payments
    - Device          : Devices used for transactions
    - PaymentInstrument : Cards, wallets, bank accounts
    - Transaction     : Individual payment events
    - Dispute         : Customer-initiated chargebacks/disputes
    - Case            : Risk investigation cases
    - AuditLog        : Immutable audit trail of system events
    - Incident        : System-level incidents (outages, anomalies)
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Boolean,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.app.db.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Merchant(Base):
    """A business that accepts payments through the platform."""
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    transactions = relationship("Transaction", back_populates="merchant")


class Customer(Base):
    """An end user who makes payments."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    payment_instruments = relationship("PaymentInstrument", back_populates="customer")
    transactions = relationship("Transaction", back_populates="customer")


class Device(Base):
    """A device (browser, mobile, etc.) associated with transactions."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    transactions = relationship("Transaction", back_populates="device")


class PaymentInstrument(Base):
    """A payment method — card, wallet, bank account, UPI, etc."""
    __tablename__ = "payment_instruments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    type = Column(String(50), nullable=False)  # card, wallet, bank_account, upi
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="payment_instruments")
    transactions = relationship("Transaction", back_populates="payment_instrument")


class Transaction(Base):
    """A single payment event — the core entity of SentinelRisk."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    payment_instrument_id = Column(Integer, ForeignKey("payment_instruments.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    timestamp = Column(DateTime, default=_utcnow, nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    # Statuses: pending, authorized, captured, failed, refunded

    # Ground-truth labels (Stage 2) — for evaluation only, NEVER used as model features
    is_fraud = Column(Boolean, default=False, nullable=False)
    fraud_archetype = Column(String(50), nullable=True)  # account_takeover, card_testing, coordinated_ring
    fraud_case_id = Column(String(50), nullable=True)     # e.g. ATO_001, CT_005, RING_003
    is_fraud_ground_truth = Column(Boolean, default=False, nullable=False)  # original label before noise

    # Relationships
    merchant = relationship("Merchant", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")
    device = relationship("Device", back_populates="transactions")
    payment_instrument = relationship("PaymentInstrument", back_populates="transactions")
    disputes = relationship("Dispute", back_populates="transaction")
    cases = relationship("Case", back_populates="transaction")

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_transactions_merchant_id", "merchant_id"),
        Index("ix_transactions_customer_id", "customer_id"),
        Index("ix_transactions_timestamp", "timestamp"),
        Index("ix_transactions_status", "status"),
    )


class Dispute(Base):
    """A customer-initiated dispute or chargeback."""
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    reason = Column(String(100), nullable=True)  # fraud_reported, product_not_received, billing_error, unauthorized
    status = Column(String(30), nullable=False, default="open")
    # Statuses: open, under_review, resolved, escalated
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="disputes")


class Case(Base):
    """A risk investigation case linked to a suspicious transaction."""
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(50), unique=True, index=True, nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    customer_id = Column(String(100), nullable=True)
    merchant_id = Column(String(100), nullable=True)
    amount = Column(Float, default=0.0, nullable=False)
    decision = Column(String(30), nullable=False, default="REVIEW")
    risk_score = Column(Float, default=0.0, nullable=False)
    priority = Column(String(20), nullable=False, default="MEDIUM")
    priority_reason = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="open")
    # Statuses: open, investigating, escalated, resolved, dismissed
    assigned_to = Column(String(100), nullable=True)
    resolution = Column(String(50), nullable=True)  # CONFIRMED_FRAUD, FALSE_POSITIVE, LEGITIMATE, UNCERTAIN
    resolution_reason = Column(Text, nullable=True)
    report_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="cases")


class AnalystFeedback(Base):
    """
    Structured analyst outcome feedback loop.
    Persists confirmed labels for model monitoring and future retraining signals.
    """
    __tablename__ = "analyst_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(50), nullable=False)
    transaction_id = Column(String(100), nullable=False)
    outcome = Column(String(50), nullable=False)  # CONFIRMED_FRAUD, FALSE_POSITIVE, LEGITIMATE, UNCERTAIN
    analyst_id = Column(String(100), nullable=False, default="Analyst_1")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_analyst_feedback_case_id", "case_id"),
        Index("ix_analyst_feedback_outcome", "outcome"),
        Index("ix_analyst_feedback_created_at", "created_at"),
    )


class MerchantAlertRecord(Base):
    """
    Persistent record of deterministic merchant-level risk alerts.
    """
    __tablename__ = "merchant_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(50), unique=True, nullable=False)
    merchant_id = Column(String(100), nullable=False)
    alert_type = Column(String(100), nullable=False)  # FRAUD_RATE_SPIKE, VELOCITY_SPIKE, etc.
    severity = Column(String(20), nullable=False)     # CRITICAL, HIGH, MEDIUM, LOW
    reason = Column(Text, nullable=False)
    recommended_action = Column(String(50), nullable=False)  # MONITOR, REVIEW, ESCALATE
    status = Column(String(30), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_merchant_alerts_merchant_id", "merchant_id"),
        Index("ix_merchant_alerts_alert_type", "alert_type"),
    )


class AuditLog(Base):
    """
    Immutable audit trail for all significant system events.
    Separated from transactions to maintain a clean, append-only log
    that is queryable independently.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    # e.g., transaction.created, case.escalated, case.confirmed_fraud, model.drift_detected
    entity_type = Column(String(50), nullable=False)
    # e.g., transaction, case, incident, merchant, model
    entity_id = Column(String(100), nullable=True)
    payload = Column(Text, nullable=True)  # JSON blob of event details
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_audit_log_event_type", "event_type"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_audit_log_created_at", "created_at"),
    )


class Incident(Base):
    """
    System-level incidents — service outages, anomaly spikes, etc.
    Used by the incident management layer in later stages.
    """
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_type = Column(String(100), nullable=False)
    # e.g., service_outage, anomaly_spike, model_degradation
    status = Column(String(30), nullable=False, default="open")
    # Statuses: open, investigating, mitigated, resolved
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
