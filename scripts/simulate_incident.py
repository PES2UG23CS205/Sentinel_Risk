#!/usr/bin/env python3
"""
SentinelRisk — "What Broke at 2 AM" Incident Simulator CLI

Usage:
    python scripts/simulate_incident.py [--scenario CARD_TESTING_ATTACK | ACCOUNT_TAKEOVER_ATTACK | COORDINATED_RING_ATTACK | BASELINE]

Executes realistic offline attack simulations, traces detection, investigation,
and outputs actionable containment & recovery recommendations.
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.incident_simulator.simulator import IncidentSimulator
from simulation.incident_simulator.scenarios import SCENARIOS


def main():
    parser = argparse.ArgumentParser(description="Simulate fraud incident and recovery workflow.")
    parser.add_argument(
        "--scenario",
        type=str,
        default="CARD_TESTING_ATTACK",
        choices=list(SCENARIOS.keys()),
        help="Scenario key to simulate"
    )
    args = parser.parse_args()

    simulator = IncidentSimulator()
    print("=" * 80)
    print("      SENTINELRISK — STAGE 8: INCIDENT SIMULATION & RECOVERY DEMO")
    print("=" * 80)
    print(f"Running Scenario: {args.scenario} ({SCENARIOS[args.scenario].name})")
    print(f"Description     : {SCENARIOS[args.scenario].description}")
    print(f"Start Timestamp : {SCENARIOS[args.scenario].start_time}")

    res = simulator.run_scenario(args.scenario)
    m = res["metrics"]
    rep = res["sample_investigation_report"]

    print("\n1. INCIDENT METRICS & DETECTION TRACE:")
    print("-" * 80)
    print(f"  Total Simulated Transactions : {m['total_transactions']}")
    print(f"  Malicious / Fraud Txns       : {m['fraud_transactions']}")
    print(f"  APPROVED Decisions           : {m['approved_count']}")
    print(f"  REVIEW Decisions             : {m['review_count']}")
    print(f"  HOLD Interventions           : {m['hold_count']}")
    print(f"  Investigation Cases Created  : {m['investigation_cases_created']}")
    print(f"  First Detection Timestamp    : {m['first_detection_timestamp']}")
    print(f"  Estimated Prevented Loss     : INR {m['fraud_loss_prevented_inr']:,.2f}")

    if rep:
        print("\n2. SAMPLE EVIDENCE-GROUNDED INVESTIGATION REPORT (LEAD CASE):")
        print("-" * 80)
        print(f"  Case ID          : {rep['case_id']}")
        print(f"  Policy Decision  : {rep['policy_decision']} ({rep['policy_version']})")
        print(f"  Risk Summary     : {rep['risk_summary']}")
        print(f"  Analyst Summary  : {rep['analyst_summary']}")
        print("\n  Factual Findings:")
        for f in rep["findings"]:
            print(f"    - [{f['finding_id']}] {f['statement']} (Citations: {f['evidence_ids']})")
        print("\n  Hypotheses:")
        for h in rep["hypotheses"]:
            print(f"    - [{h['hypothesis_id']}] {h['hypothesis']} (Conf: {h['confidence']})")

    print("\n3. RECOMMENDED CONTAINMENT & RECOVERY ACTIONS:")
    print("-" * 80)
    for i, rec in enumerate(res["recovery_recommendations"], 1):
        print(f"  {i}. {rec}")


if __name__ == "__main__":
    main()
