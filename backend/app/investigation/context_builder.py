"""
SentinelRisk — Investigation Context Builder

Extracts point-in-time evidence, normalizes risk signals into structured EvidenceItems (EVID-xxx),
builds entity activity timelines, extracts graph neighborhoods, and sanitizes untrusted input.
"""

import re
from typing import Any
import pandas as pd
from datetime import datetime

from backend.app.investigation.models import (
    EvidenceItem,
    TimelineEvent,
    InvestigationContext,
)


class ContextBuilder:
    """Constructs structured InvestigationContext for a transaction."""

    @staticmethod
    def sanitize_text(text: Any) -> str:
        """Sanitize text input against prompt injection attempts."""
        if not isinstance(text, str):
            return str(text)
        # Strip control characters, instruction delimiters, or script tags
        sanitized = re.sub(r"[<>{}\[\]\n\r]+", " ", text)
        sanitized = re.sub(r"(ignore previous|system prompt|override instructions)", "[FILTERED]", sanitized, flags=re.IGNORECASE)
        return sanitized.strip()

    def build_context(
        self,
        case_id: str,
        transaction_data: dict,
        graph_data: dict | None = None,
        policy_decision: str = "REVIEW",
        policy_version: str = "sentinelrisk-policy-v1",
        ml_probability: float = 0.0,
        triggered_rules: list[str] | None = None,
        primary_trigger: str = "UNKNOWN",
    ) -> InvestigationContext:
        """
        Build a complete, normalized InvestigationContext for a flagged transaction.
        """
        t = transaction_data
        g = graph_data or {}
        rules = triggered_rules or []

        txn_id = t.get("transaction_id", "UNKNOWN")
        ts = str(t.get("timestamp", ""))
        amount = float(t.get("amount", 0.0))
        cust_id = t.get("customer_id", "UNKNOWN")
        dev_id = t.get("device_id", "UNKNOWN")
        pi_id = t.get("payment_instrument_id", "UNKNOWN")
        merch_id = t.get("merchant_id", "UNKNOWN")

        # Extract graph signals
        ring_score = float(g.get("graph_ring_score", t.get("graph_ring_score", 0.0)))
        ring_cand = int(g.get("graph_ring_candidate", t.get("graph_ring_candidate", 0)))
        dev_cust_cnt = int(g.get("device_customer_count", t.get("device_customer_count", 1)))
        pi_cust_cnt = int(g.get("payment_instrument_customer_count", t.get("payment_instrument_customer_count", 1)))
        cust_shared_dev = int(g.get("customer_shared_device_count", t.get("customer_shared_device_count", 0)))
        cust_shared_pi = int(g.get("customer_shared_payment_count", t.get("customer_shared_payment_count", 0)))
        comp_size = int(g.get("graph_component_size", t.get("graph_component_size", 1)))

        # Extract features (checking top-level and nested features dict)
        ctx_feat = t.get("features", {}) if isinstance(t.get("features"), dict) else {}
        pi_vel_1h = int(t.get("pi_velocity_count_1h", ctx_feat.get("pi_velocity_count_1h", 0)))
        cust_vel_1h = int(t.get("velocity_txn_count_1h", ctx_feat.get("velocity_txn_count_1h", 0)))
        cust_vel_24h = int(t.get("velocity_txn_count_24h", ctx_feat.get("velocity_txn_count_24h", 0)))
        cust_ratio = float(t.get("cust_amount_to_mean_ratio", ctx_feat.get("cust_amount_to_mean_ratio", 1.0)))
        cust_zscore = float(t.get("cust_amount_zscore", ctx_feat.get("cust_amount_zscore", 0.0)))
        dev_is_new = int(t.get("device_is_new_for_cust", ctx_feat.get("device_is_new_for_cust", 0)))
        is_first_txn = int(t.get("cust_is_first_txn", ctx_feat.get("cust_is_first_txn", 0)))
        is_night = int(t.get("is_night", ctx_feat.get("is_night", 0)))

        evidence_items: list[EvidenceItem] = []
        evid_idx = 1

        def add_evidence(etype: str, source: str, val: Any, desc: str):
            nonlocal evid_idx
            eid = f"EVID-{evid_idx:03d}"
            evidence_items.append(EvidenceItem(
                evidence_id=eid,
                evidence_type=etype,
                source=source,
                timestamp=ts,
                value=val,
                description=desc,
            ))
            evid_idx += 1

        # 1. Transaction Core Evidence
        add_evidence(
            "transaction", "transaction_features", amount,
            f"Transaction amount is INR {amount:.2f} at merchant {merch_id}."
        )

        # 2. Machine Learning Evidence
        add_evidence(
            "ml_score", "lightgbm_model", round(ml_probability, 4),
            f"Supervised LightGBM calibrated fraud probability is {ml_probability:.4f}."
        )

        # 3. Graph Topology Evidence
        if ring_score > 0.0 or dev_cust_cnt > 1 or pi_cust_cnt > 1:
            add_evidence(
                "graph_topology", "entity_graph", round(ring_score, 4),
                f"Entity graph ring score is {ring_score:.2f} (Candidate: {ring_cand}). Device {dev_id} is associated with {dev_cust_cnt} customer accounts."
            )
            if pi_cust_cnt > 1:
                add_evidence(
                    "graph_topology", "entity_graph", pi_cust_cnt,
                    f"Payment instrument {pi_id} is shared across {pi_cust_cnt} distinct customer accounts."
                )

        # 4. Velocity Evidence (Threshold-grounded)
        if pi_vel_1h >= 5 or cust_vel_1h >= 5:
            add_evidence(
                "velocity", "transaction_features", pi_vel_1h,
                f"Severe authorization velocity burst: {pi_vel_1h} transactions on payment token in the past 1 hour (threshold: 5)."
            )
        elif pi_vel_1h >= 3 or cust_vel_1h >= 3:
            add_evidence(
                "velocity", "transaction_features", pi_vel_1h,
                f"Elevated authorization velocity: {pi_vel_1h} transactions on payment token in the past 1 hour (threshold: 3)."
            )
        else:
            add_evidence(
                "benign_indicator", "transaction_features", pi_vel_1h,
                f"Payment instrument velocity is low ({pi_vel_1h} txns in 1 hour), within normal baseline."
            )

        # 5. Customer Baseline Deviation Evidence
        if cust_ratio >= 1.5 or abs(cust_zscore) >= 1.5:
            add_evidence(
                "customer_baseline", "transaction_features", round(cust_ratio, 2),
                f"Transaction amount is {cust_ratio:.1f}x the customer's historical mean spend (Z-score: {cust_zscore:.2f})."
            )

        # 6. Device Novelty Evidence
        if dev_is_new == 1:
            add_evidence(
                "device_novelty", "transaction_features", 1,
                f"Device {dev_id} has never been previously used by customer {cust_id}."
            )

        # 7. Benign Indicators (Evidence against fraud)
        if dev_cust_cnt <= 2 and pi_cust_cnt <= 1:
            add_evidence(
                "benign_indicator", "entity_graph", dev_cust_cnt,
                f"Device sharing is limited to {dev_cust_cnt} customer accounts with strictly independent payment instruments (consistent with legitimate household sharing)."
            )
        if cust_ratio <= 1.2 and cust_vel_1h <= 1:
            add_evidence(
                "benign_indicator", "transaction_features", cust_ratio,
                f"Transaction spend is within normal historical customer baseline ({cust_ratio:.1f}x average)."
            )

        # Build activity timeline
        timeline: list[TimelineEvent] = [
            TimelineEvent(
                timestamp=ts,
                event_type="AUTHORIZATION_ATTEMPT",
                description=f"Customer {cust_id} initiated authorization of INR {amount:.2f} on device {dev_id}.",
                entity_id=str(cust_id),
            )
        ]

        if dev_is_new == 1:
            timeline.insert(0, TimelineEvent(
                timestamp=ts,
                event_type="UNRECOGNIZED_DEVICE_SEEN",
                description=f"First time device {dev_id} observed for customer {cust_id}.",
                entity_id=str(dev_id),
            ))

        if pi_vel_1h >= 3:
            timeline.insert(0, TimelineEvent(
                timestamp=ts,
                event_type="VELOCITY_BURST",
                description=f"Payment instrument {pi_id} recorded {pi_vel_1h} transactions in 60 minutes.",
                entity_id=str(pi_id),
            ))

        # Related entities dictionary
        related_entities = {
            "customers": [str(cust_id)],
            "devices": [str(dev_id)],
            "payment_instruments": [str(pi_id)],
            "merchants": [str(merch_id)],
        }

        return InvestigationContext(
            case_id=case_id,
            transaction_id=txn_id,
            timestamp=ts,
            amount=amount,
            customer_id=cust_id,
            device_id=dev_id,
            payment_instrument_id=pi_id,
            merchant_id=merch_id,
            policy_decision=policy_decision,
            policy_version=policy_version,
            ml_probability=ml_probability,
            graph_ring_score=ring_score,
            graph_ring_candidate=ring_cand,
            triggered_rules=rules,
            evidence_items=evidence_items,
            timeline=timeline,
            related_entities=related_entities,
            primary_trigger=primary_trigger,
            sanitized_metadata={"amount_inr": amount, "decision": policy_decision},
        )
