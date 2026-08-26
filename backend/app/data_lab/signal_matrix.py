"""
SentinelRisk — Data Lab Signal Availability Matrix Generator

Evaluates mapped schema against SentinelRisk's signal architecture.
Strictly adheres to the core principle:
  - Never fabricate unavailable features or substitute arbitrary zeros.
  - Transparently explains what can and cannot be computed.
"""

from typing import Optional
from backend.app.data_lab.models import (
    AssessmentMode,
    SignalAvailabilityItem,
    SignalMatrixReport,
    ValidationSummary,
)


def generate_signal_matrix(
    validation: ValidationSummary,
    mapping: dict[str, Optional[str]],
) -> SignalMatrixReport:
    """
    Generate an authoritative Signal Availability Matrix for the dataset based on mapped fields.
    """
    has_amount = validation.has_amount
    has_timestamp = validation.has_timestamp
    has_cust = validation.has_customer_id
    has_merch = validation.has_merchant_id
    has_dev = validation.has_device_id
    has_pi = validation.has_payment_instrument_id
    has_gt = validation.has_ground_truth

    signals: list[SignalAvailabilityItem] = [
        # 1. Transaction Core
        SignalAvailabilityItem(
            signal_name="Transaction Amount",
            category="Transaction Core",
            is_available=has_amount,
            required_fields=["amount"],
            status_label="AVAILABLE" if has_amount else "UNAVAILABLE",
            technical_rationale="Numeric transaction value used for ticket size analysis and financial exposure." if has_amount else "Amount column is not mapped; cannot evaluate transaction value.",
        ),
        SignalAvailabilityItem(
            signal_name="Temporal Timestamp & Off-Hour Scoring",
            category="Transaction Core",
            is_available=has_timestamp,
            required_fields=["timestamp"],
            status_label="AVAILABLE" if has_timestamp else "UNAVAILABLE",
            technical_rationale="Parsed datetime enabling off-hour risk bands and point-in-time sliding windows." if has_timestamp else "Timestamp column is not mapped; cannot evaluate temporal signals.",
        ),
        SignalAvailabilityItem(
            signal_name="Currency & High-Risk Cross-Border Marker",
            category="Transaction Core",
            is_available=mapping.get("currency") is not None,
            required_fields=["currency"],
            status_label="AVAILABLE" if mapping.get("currency") is not None else "PARTIAL",
            technical_rationale="Explicit currency mapped from dataset." if mapping.get("currency") else "Currency not mapped; default system currency (INR) applied without fabricating FX markers.",
        ),

        # 2. Customer Velocity & Spending Profile
        SignalAvailabilityItem(
            signal_name="Customer Velocity Windows (1h, 24h, 7d)",
            category="Customer Velocity",
            is_available=has_cust and has_timestamp,
            required_fields=["customer_id", "timestamp"],
            status_label="AVAILABLE" if (has_cust and has_timestamp) else "UNAVAILABLE",
            technical_rationale="Sliding window frequency counters computed strictly from preceding timestamps (t < T)." if (has_cust and has_timestamp) else "Customer ID or timestamp missing; sliding customer velocity cannot be calculated.",
        ),
        SignalAvailabilityItem(
            signal_name="Customer Spending Ratio & Z-Score Deviation",
            category="Customer Behavior",
            is_available=has_cust and has_amount and has_timestamp,
            required_fields=["customer_id", "amount", "timestamp"],
            status_label="AVAILABLE" if (has_cust and has_amount and has_timestamp) else "UNAVAILABLE",
            technical_rationale="Calculates amount ratio against historical customer baseline average (strictly t < T)." if (has_cust and has_amount and has_timestamp) else "Customer ID or amount missing; personal spending baseline cannot be computed.",
        ),

        # 3. Merchant Risk Intelligence
        SignalAvailabilityItem(
            signal_name="Merchant / Terminal Velocity",
            category="Merchant Intelligence",
            is_available=has_merch and has_timestamp,
            required_fields=["merchant_id", "timestamp"],
            status_label="AVAILABLE" if (has_merch and has_timestamp) else "UNAVAILABLE",
            technical_rationale="Sliding terminal authorization volume counters computed strictly t < T." if (has_merch and has_timestamp) else "Merchant ID missing; terminal velocity bursts cannot be detected.",
        ),
        SignalAvailabilityItem(
            signal_name="Merchant Point-in-Time Risk Scoring",
            category="Merchant Intelligence",
            is_available=has_merch and has_amount and has_timestamp,
            required_fields=["merchant_id", "amount", "timestamp"],
            status_label="AVAILABLE" if (has_merch and has_amount and has_timestamp) else "UNAVAILABLE",
            technical_rationale="Aggregates merchant volume trajectories and customer concentration risk." if (has_merch and has_amount and has_timestamp) else "Merchant ID missing; merchant-level risk profiling skipped.",
        ),

        # 4. Device & Identity Novelty
        SignalAvailabilityItem(
            signal_name="Device Novelty for Customer",
            category="Identity & Device",
            is_available=has_dev and has_cust,
            required_fields=["device_id", "customer_id"],
            status_label="AVAILABLE" if (has_dev and has_cust) else "UNAVAILABLE",
            technical_rationale="Identifies when an established customer transacts from an unseen hardware token." if (has_dev and has_cust) else "Device ID or customer ID missing; device novelty cannot be evaluated (will not fabricate dummy device).",
        ),
        SignalAvailabilityItem(
            signal_name="Hardware Fingerprint Multi-Account Sharing",
            category="Identity & Device",
            is_available=has_dev and has_cust,
            required_fields=["device_id", "customer_id"],
            status_label="AVAILABLE" if (has_dev and has_cust) else "UNAVAILABLE",
            technical_rationale="Tracks number of distinct customer accounts linked to a single physical device." if (has_dev and has_cust) else "Device ID missing; device sharing collusion cannot be detected.",
        ),

        # 5. Payment Instrument & Card Velocity
        SignalAvailabilityItem(
            signal_name="Card / Payment Instrument Velocity Burst",
            category="Payment Instrument",
            is_available=has_pi and has_timestamp,
            required_fields=["payment_instrument_id", "timestamp"],
            status_label="AVAILABLE" if (has_pi and has_timestamp) else "UNAVAILABLE",
            technical_rationale="Detects rapid micro-authorization card testing attacks across merchants." if (has_pi and has_timestamp) else "Payment instrument / card token missing; card testing velocity cannot be detected.",
        ),
        SignalAvailabilityItem(
            signal_name="Card Multi-Customer Sharing",
            category="Payment Instrument",
            is_available=has_pi and has_cust,
            required_fields=["payment_instrument_id", "customer_id"],
            status_label="AVAILABLE" if (has_pi and has_cust) else "UNAVAILABLE",
            technical_rationale="Identifies single card tokens attempted across distinct customer accounts." if (has_pi and has_cust) else "Payment instrument or customer ID missing; card sharing cannot be evaluated.",
        ),

        # 6. Entity Graph Syndicate Detection
        SignalAvailabilityItem(
            signal_name="Coordinated Abuse Ring Graph Score",
            category="Entity Graph",
            is_available=has_cust and has_dev and has_pi,
            required_fields=["customer_id", "device_id", "payment_instrument_id"],
            status_label="AVAILABLE" if (has_cust and has_dev and has_pi) else "UNAVAILABLE",
            technical_rationale="Bipartite graph topology analysis discovering multi-account collusive rings." if (has_cust and has_dev and has_pi) else "Graph ring detection requires customer, device, and payment instrument tokens; unavailable signals are NOT fabricated.",
        ),

        # 7. Machine Learning Model Inference
        SignalAvailabilityItem(
            signal_name="Calibrated ML Probability Inference",
            category="Machine Learning",
            is_available=has_amount and has_timestamp and (has_cust or has_merch),
            required_fields=["amount", "timestamp"],
            status_label="AVAILABLE" if (has_amount and has_timestamp and (has_cust or has_merch)) else "PARTIAL",
            technical_rationale="Evaluates LightGBM model using available temporal features with explicit schema adaptation." if (has_amount and has_timestamp) else "Insufficient signals for calibrated ML inference.",
        ),

        # 8. Ground Truth Evaluation
        SignalAvailabilityItem(
            signal_name="Supervised Ground-Truth Detection Metrics",
            category="Evaluation",
            is_available=has_gt,
            required_fields=["is_fraud"],
            status_label="AVAILABLE" if has_gt else "UNAVAILABLE",
            technical_rationale="Explicit fraud label detected; Precision, Recall, F1, and Confusion Matrix can be computed." if has_gt else "Ground truth fraud label is not present in dataset; detection metrics will be honestly marked as unavailable.",
        ),
    ]

    avail_list = [s for s in signals if s.is_available]
    unavail_list = [s for s in signals if not s.is_available]

    # Determine recommended mode
    if has_cust and has_merch and (has_dev or has_pi):
        recommended_mode = AssessmentMode.HISTORICAL_REPLAY
    else:
        recommended_mode = AssessmentMode.QUICK_ASSESSMENT

    return SignalMatrixReport(
        available_count=len(avail_list),
        unavailable_count=len(unavail_list),
        available_signals=avail_list,
        unavailable_signals=unavail_list,
        recommended_mode=recommended_mode,
    )
