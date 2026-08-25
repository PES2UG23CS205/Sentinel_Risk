#!/usr/bin/env python3
"""
SentinelRisk — Run Investigation CLI

Usage:
    python scripts/run_investigation.py [--case-id CASE-00001]
                                        [--transaction-id 2557]

Runs evidence extraction and on-demand LLM investigation on a flagged transaction.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.agent import InvestigationAgent
from backend.app.policy.engine import PolicyEngine


def main():
    parser = argparse.ArgumentParser(description="Investigate a flagged transaction.")
    parser.add_argument("--transaction-id", type=int, default=2557, help="Transaction ID to investigate")
    args = parser.parse_args()

    feat_path = PROJECT_ROOT / "data/features/transaction_features.csv"
    graph_path = PROJECT_ROOT / "data/features/graph_features.csv"

    if not feat_path.exists() or not graph_path.exists():
        print("[!] Error: Feature datasets not found.")
        sys.exit(1)

    df_feat = pd.read_csv(feat_path)
    df_graph = pd.read_csv(graph_path)

    match_feat = df_feat[df_feat["transaction_id"] == args.transaction_id]
    if match_feat.empty:
        print(f"[!] Transaction {args.transaction_id} not found.")
        sys.exit(1)

    match_graph = df_graph[df_graph["transaction_id"] == args.transaction_id]
    row_feat = match_feat.iloc[0].to_dict()
    row_graph = match_graph.iloc[0].to_dict() if not match_graph.empty else {}

    policy_engine = PolicyEngine()
    agent = InvestigationAgent()
    manager = CaseManager(agent)

    # Evaluate decision
    dec = policy_engine.evaluate(
        transaction_id=args.transaction_id,
        timestamp=row_feat["timestamp"],
        amount=float(row_feat["amount"]),
        ml_probability=0.9995 if row_feat.get("fraud_archetype") == "card_testing" else 0.85,
        graph_ring_score=float(row_graph.get("graph_ring_score", 0.0)),
        graph_ring_candidate=int(row_graph.get("graph_ring_candidate", 0)),
        feature_context=row_feat,
    )

    print("=" * 80)
    print(f"      SENTINELRISK — INVESTIGATING TRANSACTION #{args.transaction_id}")
    print("=" * 80)
    print(f"Decision Record : {dec.decision.value} ({dec.primary_trigger})")
    print(f"Policy Version  : {dec.policy_version}")
    print(f"Amount          : INR {dec.amount:,.2f}")

    case = manager.create_case_from_decision(dec.to_dict(), row_feat, row_graph)
    if not case:
        print(f"Transaction was {dec.decision.value} (no investigation case required).")
        return

    print(f"Created Case    : {case.case_id} (Priority: {case.priority.value})")
    print("Generating evidence-grounded investigation report...")

    report = manager.investigate_case(case.case_id)

    print("\nINVESTIGATION REPORT SUMMARY:")
    print("-" * 80)
    print(f"Risk Summary    : {report.risk_summary}")
    print(f"Analyst Summary : {report.analyst_summary}")
    print(f"Uncertainty     : {report.uncertainty}")

    print(f"\nExtracted Evidence Items ({len(report.evidence)} items):")
    for e in report.evidence:
        print(f"  - [{e.evidence_id}] ({e.evidence_type}): {e.description}")

    print(f"\nFactual Findings ({len(report.findings)} findings):")
    for f in report.findings:
        print(f"  - [{f.finding_id}] {f.statement} (Citing: {f.evidence_ids})")

    print(f"\nHypotheses ({len(report.hypotheses)} hypotheses):")
    for h in report.hypotheses:
        print(f"  - [{h.hypothesis_id}] {h.hypothesis} (Conf: {h.confidence})")

    print("\nRecommended Next Steps:")
    for step in report.recommended_next_steps:
        print(f"  - {step}")


if __name__ == "__main__":
    main()
