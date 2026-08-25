#!/usr/bin/env python3
"""
SentinelRisk — Primary Demo Scenarios CLI

Usage:
    python scripts/demo.py --scenario LEGITIMATE_TRANSACTION
    python scripts/demo.py --scenario ACCOUNT_TAKEOVER
    python scripts/demo.py --scenario COORDINATED_ABUSE_RING
    python scripts/demo.py --scenario CARD_TESTING
    python scripts/demo.py --scenario WHAT_BROKE_AT_2AM
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.scoring.realtime_service import RealtimeRiskService
from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.agent import InvestigationAgent
from simulation.incident_simulator.simulator import IncidentSimulator


def run_scenario(scenario_name: str):
    service = RealtimeRiskService()
    agent = InvestigationAgent()
    manager = CaseManager(agent)

    print("=" * 80)
    print(f"      SENTINELRISK — DEMO SCENARIO: {scenario_name}")
    print("=" * 80)

    if scenario_name == "WHAT_BROKE_AT_2AM":
        sim = IncidentSimulator()
        res = sim.run_scenario("CARD_TESTING_ATTACK")
        m = res["metrics"]
        rep = res["sample_investigation_report"]

        print(f"Scenario Description : {res['scenario']['description']}")
        print(f"Attack Timestamp     : {res['scenario']['start_time']}")
        print("\n1. OPERATIONAL DETECTION TRACE:")
        print(f"  • Total Transactions : {m['total_transactions']}")
        print(f"  • Fraud Transactions : {m['fraud_transactions']}")
        print(f"  • HOLD Interventions : {m['hold_count']}")
        print(f"  • Cases Created      : {m['investigation_cases_created']}")
        print(f"  • Prevented Loss     : INR {m['fraud_loss_prevented_inr']:,.2f}")

        if rep:
            print("\n2. AI INVESTIGATION DOSSIER:")
            print(f"  • Lead Case ID       : {rep['case_id']}")
            print(f"  • Summary            : {rep['analyst_summary']}")
            print(f"  • Primary Hypothesis : {rep['hypotheses'][0]['hypothesis']}")
            print(f"  • Cited Evidence     : {[f['evidence_ids'] for f in rep['findings']]}")

        print("\n3. CONTAINMENT & RECOVERY PLAYBOOK:")
        for i, rec in enumerate(res["recovery_recommendations"], 1):
            print(f"  {i}. {rec}")
        return

    # Deterministic Transaction Scenarios
    scenarios_data = {
        "LEGITIMATE_TRANSACTION": {
            "transaction_id": "DEMO-LEGIT-001",
            "customer_id": "CUST_LEGIT_101",
            "device_id": "DEV_TRUSTED_01",
            "payment_instrument_id": "PI_PERSONAL_01",
            "merchant_id": "MERCH_GROCERY_01",
            "amount": 420.00,
            "timestamp": "2025-06-15 14:20:00",
            "ml_probability": 0.0012,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 1.0, "device_is_new_for_cust": 0},
            "desc": "Regular daytime grocery payment from recognized device with normal historical spend.",
        },
        "ACCOUNT_TAKEOVER": {
            "transaction_id": "DEMO-ATO-002",
            "customer_id": "CUST_VICTIM_404",
            "device_id": "DEV_ATTACKER_99",
            "payment_instrument_id": "PI_VICTIM_CARD",
            "merchant_id": "MERCH_ELECTRONICS_05",
            "amount": 24500.00,
            "timestamp": "2025-06-15 02:15:00",
            "ml_probability": 0.985,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 6.2, "cust_amount_zscore": 4.1, "device_is_new_for_cust": 1},
            "desc": "Late-night luxury electronics spend (6.2x average) initiated from a brand-new device token.",
        },
        "COORDINATED_ABUSE_RING": {
            "transaction_id": "DEMO-RING-003",
            "customer_id": "CUST_MULE_12",
            "device_id": "DEV_SYNDICATE_BOX",
            "payment_instrument_id": "PI_SHARED_CARD_99",
            "merchant_id": "MERCH_DIGITAL_01",
            "amount": 3200.00,
            "timestamp": "2025-06-15 04:30:00",
            "ml_probability": 0.220,
            "graph_ring_score": 0.88,
            "graph_ring_candidate": 1,
            "features": {"pi_velocity_count_1h": 2, "cust_amount_to_mean_ratio": 1.2, "device_customer_count": 6, "payment_instrument_customer_count": 5},
            "desc": "Collusive payment syndicate sharing hardware devices and cards across 6 distinct user profiles.",
        },
        "CARD_TESTING": {
            "transaction_id": "DEMO-BOT-004",
            "customer_id": "CUST_SCRIPT_01",
            "device_id": "DEV_BOT_01",
            "payment_instrument_id": "PI_STOLEN_BIN",
            "merchant_id": "MERCH_GAMING_02",
            "amount": 85.00,
            "timestamp": "2025-06-15 02:05:00",
            "ml_probability": 0.9995,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 8, "velocity_txn_count_1h": 8, "device_is_new_for_cust": 1},
            "desc": "Automated card-testing script firing rapid micro-transactions across gaming merchants.",
        },
    }

    t = scenarios_data.get(scenario_name)
    if not t:
        print(f"[!] Unknown scenario: {scenario_name}")
        return

    print(f"Description     : {t['desc']}")
    print(f"Transaction ID  : {t['transaction_id']} (Amount: INR {t['amount']:,.2f})")
    print(f"Timestamp       : {t['timestamp']}")

    # 1. Real-Time Risk Evaluation
    res = service.evaluate_transaction(t)
    print("\n1. REAL-TIME RISK DECISION:")
    print(f"  • Decision        : {res['decision']} (Intervention: {res['is_intervention']})")
    print(f"  • Primary Trigger : {res['primary_trigger']}")
    print(f"  • Policy Version  : {res['policy_version']}")
    print(f"  • ML Probability  : {res['ml_probability']:.4f}")
    print(f"  • Graph Ring Score: {res['graph_ring_score']:.2f}")
    print(f"  • Latency         : {res['latencies_ms']['total_ms']} ms (In-process)")
    print(f"  • Input Hash      : {res['input_hash'][:16]}...")
    print(f"  • Reasons         : {res['decision_reasons']}")

    # 2. Case Management & AI Investigation
    if res["is_intervention"] == 1:
        case = manager.create_case_from_decision(res, t, {"graph_ring_score": t["graph_ring_score"], "graph_ring_candidate": t["graph_ring_candidate"]})
        print(f"\n2. ENQUEUED INVESTIGATION CASE: {case.case_id} (Priority: {case.priority.value})")

        report = manager.investigate_case(case.case_id)
        print("\n3. AI INVESTIGATION REPORT (Evidence-Grounded):")
        print(f"  • Analyst Summary : {report.analyst_summary}")
        print(f"  • Findings ({len(report.findings)} items):")
        for f in report.findings:
            print(f"    - [{f.finding_id}] {f.statement} (Citations: {f.evidence_ids})")
        print(f"  • Hypotheses:")
        for h in report.hypotheses:
            print(f"    - [{h.hypothesis_id}] {h.hypothesis} (Conf: {h.confidence.value})")
        print(f"  • Recommended Next Actions:")
        for step in report.recommended_next_steps:
            print(f"    - {step}")
    else:
        print("\n2. TRANSACTION APPROVED: Frictionless payment authorization; no case required.")


def main():
    parser = argparse.ArgumentParser(description="SentinelRisk Demo Scenarios Runner.")
    parser.add_argument(
        "--scenario",
        type=str,
        default="WHAT_BROKE_AT_2AM",
        choices=[
            "LEGITIMATE_TRANSACTION",
            "ACCOUNT_TAKEOVER",
            "COORDINATED_ABUSE_RING",
            "CARD_TESTING",
            "WHAT_BROKE_AT_2AM",
        ],
        help="Demo scenario to run"
    )
    args = parser.parse_args()
    run_scenario(args.scenario)


if __name__ == "__main__":
    main()
