#!/usr/bin/env python3
"""
SentinelRisk — Evaluate Investigation Agent Quality & Grounding

Usage:
    python scripts/evaluate_investigations.py [--output-dir evaluation/investigation]

Runs quality benchmarks across 4 archetype cases, verifies evidence grounding,
citation correctness, hallucination rate, policy preservation, and exports artifacts.
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.investigation.evaluator import InvestigationEvaluator


def main():
    parser = argparse.ArgumentParser(description="Evaluate investigation agent quality.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/investigation",
        help="Output directory for benchmark reports"
    )
    args = parser.parse_args()
    out_dir = PROJECT_ROOT / args.output_dir

    print("=" * 80)
    print("      SENTINELRISK — STAGE 8: INVESTIGATION QUALITY BENCHMARK")
    print("=" * 80)

    evaluator = InvestigationEvaluator()
    eval_results = evaluator.run_evaluation()
    m = eval_results["evaluation_metrics"]

    print("\n1. INVESTIGATION QUALITY & GROUNDING METRICS:")
    print("-" * 80)
    print(f"  Benchmark Cases Evaluated  : {m['total_benchmark_cases']}")
    print(f"  Total Findings Evaluated   : {m['total_findings_evaluated']}")
    print(f"  Evidence Grounding Rate    : {m['evidence_grounding_rate_pct']}")
    print(f"  Citation Correctness       : {m['citation_correctness_pct']}")
    print(f"  Hallucination Rate         : {m['hallucination_rate_pct']}")
    print(f"  Policy Preservation Rate   : {m['policy_preservation_pct']}")
    print(f"  Schema Validity Rate       : {m['schema_validity_pct']}")

    paths = evaluator.export_artifacts(eval_results, out_dir)
    print(f"\n[OK] Benchmark artifacts successfully exported to {out_dir}:")
    for name, p in paths.items():
        print(f"  [OK] {p.name}")


if __name__ == "__main__":
    main()
