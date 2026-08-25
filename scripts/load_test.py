#!/usr/bin/env python3
"""
SentinelRisk — Production Load Test CLI

Usage:
    python scripts/load_test.py [--output-dir evaluation/production]

Executes offline load benchmarks across 10, 100, and 1,000 requests,
measures throughput and p50/p95/p99 latencies, and exports latency reports.
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.scoring.load_tester import LoadTester


def main():
    parser = argparse.ArgumentParser(description="Run offline load testing benchmark.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/production",
        help="Output directory for reports"
    )
    args = parser.parse_args()
    out_dir = PROJECT_ROOT / args.output_dir

    print("=" * 80)
    print("      SENTINELRISK — STAGE 9: PRODUCTION LOAD & LATENCY BENCHMARK")
    print("=" * 80)

    tester = LoadTester()
    results = tester.run_benchmark([10, 100, 1000])

    print("\n1. BENCHMARK RESULTS SUMMARY:")
    print("-" * 80)
    for name, r in results["benchmark_results"].items():
        lats = r["latencies_ms"]
        print(f"  [{name.upper()}]")
        print(f"    - Requests   : {r['total_requests']}")
        print(f"    - Throughput : {r['throughput_rps']:,.2f} req/sec")
        print(f"    - p50 Latency: {lats['p50']} ms")
        print(f"    - p95 Latency: {lats['p95']} ms")
        print(f"    - p99 Latency: {lats['p99']} ms")
        print(f"    - Error Rate : {r['error_rate_pct']}%\n")

    paths = tester.export_reports(results, out_dir)
    print(f"[OK] Production reports exported to {out_dir}:")
    for name, p in paths.items():
        print(f"  [OK] {p.name}")


if __name__ == "__main__":
    main()
