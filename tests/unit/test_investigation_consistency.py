"""
SentinelRisk — Investigation Consistency & Evidence Grounding Tests

Verifies:
  - Hypotheses strictly align with the primary policy trigger and actual signal values
  - Velocity <= 2 txns/hr is NOT classified as card testing or severe burst
  - Graph ring triggers produce Coordinated Syndicate hypotheses
  - ATO triggers produce Account Takeover hypotheses
  - Policy decisions are 100% immutable across the investigation layer
"""

import pytest
from backend.app.investigation.agent import InvestigationAgent
from backend.app.investigation.context_builder import ContextBuilder
from backend.app.investigation.models import InvestigationContext, EvidenceItem, TimelineEvent, ConfidenceLevel


class TestInvestigationConsistencyAndGrounding:
    """Test investigation consistency, velocity semantics, and hypothesis grounding."""

    def test_graph_trigger_does_not_infer_card_testing(self):
        """
        Regression test: When elevated graph ring score triggers REVIEW with velocity=2,
        the investigation must hypothesize Coordinated Syndicate, NOT Card Testing.
        """
        builder = ContextBuilder()
        agent = InvestigationAgent()

        context = builder.build_context(
            case_id="CASE-AUDIT-001",
            transaction_data={
                "transaction_id": "TXN-RING-01",
                "timestamp": "2025-07-01 12:00:00",
                "amount": 3200.0,
                "customer_id": "CUST_MULE_1",
                "device_id": "DEV_SHARED_BOX",
                "payment_instrument_id": "PI_CARD_1",
                "merchant_id": "MERCH_1",
                "features": {
                    "pi_velocity_count_1h": 2,  # Low velocity (normal)
                    "cust_amount_to_mean_ratio": 1.1,
                    "device_is_new_for_cust": 0,
                },
            },
            graph_data={
                "graph_ring_score": 0.35,
                "graph_ring_candidate": 1,
                "device_customer_count": 3,
                "payment_instrument_customer_count": 2,
            },
            policy_decision="REVIEW",
            policy_version="sentinelrisk-policy-v1",
            ml_probability=0.027,
            primary_trigger="ELEVATED_GRAPH_RING_SCORE",
        )

        # 1. Verify velocity evidence item is benign (NOT suspicious velocity)
        vel_evids = [e for e in context.evidence_items if e.evidence_type == "velocity"]
        assert len(vel_evids) == 0  # 2 txns/hr is classified as benign_indicator, not velocity alert

        # 2. Run investigation
        report = agent.investigate(context)

        # 3. Verify primary hypothesis is Coordinated Syndicate
        assert len(report.hypotheses) > 0
        primary_hyp = report.hypotheses[0].hypothesis
        assert "Coordinated Multi-Accounting Syndicate" in primary_hyp
        assert "Card Testing" not in primary_hyp

        # 4. Verify analyst summary matches primary trigger
        assert "Trigger: ELEVATED_GRAPH_RING_SCORE" in report.analyst_summary
        assert "Coordinated Multi-Accounting Syndicate" in report.analyst_summary

    def test_severe_velocity_burst_triggers_card_testing_hypothesis(self):
        """
        When velocity is 8 txns/hr and trigger is SEVERE_PI_VELOCITY,
        the investigation must hypothesize Card Testing.
        """
        builder = ContextBuilder()
        agent = InvestigationAgent()

        context = builder.build_context(
            case_id="CASE-AUDIT-002",
            transaction_data={
                "transaction_id": "TXN-BOT-01",
                "timestamp": "2025-07-01 02:05:00",
                "amount": 85.0,
                "customer_id": "CUST_BOT_1",
                "device_id": "DEV_BOT_1",
                "payment_instrument_id": "PI_STOLEN_99",
                "merchant_id": "MERCH_GAMING_1",
                "features": {
                    "pi_velocity_count_1h": 8,  # Severe burst
                    "cust_amount_to_mean_ratio": 0.2,
                    "device_is_new_for_cust": 1,
                },
            },
            policy_decision="HOLD",
            policy_version="sentinelrisk-policy-v1",
            ml_probability=0.99,
            primary_trigger="SEVERE_PI_VELOCITY",
        )

        report = agent.investigate(context)

        primary_hyp = report.hypotheses[0].hypothesis
        assert "Card Testing" in primary_hyp
        assert report.policy_decision == "HOLD"

    def test_ato_trigger_produces_ato_hypothesis(self):
        """
        When spend surge + new device triggers HOLD,
        investigation must hypothesize Account Takeover (ATO).
        """
        builder = ContextBuilder()
        agent = InvestigationAgent()

        context = builder.build_context(
            case_id="CASE-AUDIT-003",
            transaction_data={
                "transaction_id": "TXN-ATO-01",
                "timestamp": "2025-07-01 02:30:00",
                "amount": 28500.0,
                "customer_id": "CUST_VICTIM_1",
                "device_id": "DEV_ATTACKER_99",
                "payment_instrument_id": "PI_CARD_1",
                "merchant_id": "MERCH_LUXURY_1",
                "features": {
                    "pi_velocity_count_1h": 1,
                    "cust_amount_to_mean_ratio": 6.5,
                    "cust_amount_zscore": 4.2,
                    "device_is_new_for_cust": 1,
                },
            },
            policy_decision="HOLD",
            policy_version="sentinelrisk-policy-v1",
            ml_probability=0.985,
            primary_trigger="HIGH_CONFIDENCE_ML_RISK",
        )

        report = agent.investigate(context)

        primary_hyp = report.hypotheses[0].hypothesis
        assert "Account Takeover (ATO)" in primary_hyp
        assert report.policy_decision == "HOLD"

    def test_policy_immutability_guarantee(self):
        """
        Verify that investigation agent NEVER modifies policy decisions.
        """
        agent = InvestigationAgent()
        context = InvestigationContext(
            case_id="CASE-IMMUTABLE-01",
            transaction_id="TXN-IMMUTABLE",
            timestamp="2025-07-01 10:00:00",
            amount=500.0,
            customer_id="CUST_1",
            device_id="DEV_1",
            payment_instrument_id="PI_1",
            merchant_id="MERCH_1",
            policy_decision="HOLD",
            policy_version="sentinelrisk-policy-v1",
            ml_probability=0.88,
            graph_ring_score=0.0,
            graph_ring_candidate=0,
            triggered_rules=[],
            evidence_items=[],
            timeline=[],
            related_entities={},
            primary_trigger="HIGH_CONFIDENCE_ML_RISK",
        )

        report = agent.investigate(context)
        assert report.policy_decision == "HOLD"
