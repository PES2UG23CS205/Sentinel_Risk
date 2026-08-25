#!/usr/bin/env python3
"""
SentinelRisk — Interactive Demo Launcher

Usage:
    python scripts/run_demo.py

Displays interactive CLI menu to execute all demo scenarios and view system metrics.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.demo import run_scenario


def main():
    while True:
        print("\n" + "=" * 80)
        print("          SENTINELRISK — INTERACTIVE DEMO CONSOLE")
        print("=" * 80)
        print("Select a scenario to demonstrate:")
        print("  1. Legitimate Transaction (APPROVE)")
        print("  2. Account Takeover Surge (HOLD + ATO Investigation)")
        print("  3. Coordinated Abuse Ring (HOLD + Graph Cluster Investigation)")
        print("  4. Card Testing Velocity Attack (HOLD + Bot Containment)")
        print("  5. 'What Broke at 2 AM?' Incident Simulation (Flagship Incident Replay)")
        print("  6. Run In-Process Load Benchmark (1,000 requests)")
        print("  7. Replay 500 Historical Decisions (Reproducibility Check)")
        print("  0. Exit")
        print("-" * 80)

        choice = input("Enter choice [0-7]: ").strip()

        if choice == "1":
            run_scenario("LEGITIMATE_TRANSACTION")
        elif choice == "2":
            run_scenario("ACCOUNT_TAKEOVER")
        elif choice == "3":
            run_scenario("COORDINATED_ABUSE_RING")
        elif choice == "4":
            run_scenario("CARD_TESTING")
        elif choice == "5":
            run_scenario("WHAT_BROKE_AT_2AM")
        elif choice == "6":
            from backend.app.scoring.load_tester import LoadTester
            tester = LoadTester()
            res = tester.run_benchmark([1000])
            b = res["benchmark_results"]["load_1000_requests"]
            print(f"\n[BENCHMARK RESULT] 1000 Requests: Throughput={b['throughput_rps']:,.2f} RPS, p50={b['latencies_ms']['p50']}ms, p99={b['latencies_ms']['p99']}ms")
        elif choice == "7":
            from scripts.replay_risk import main as run_replay
            run_replay()
        elif choice == "0":
            print("\nExiting SentinelRisk Demo Console. Goodbye!")
            break
        else:
            print("[!] Invalid choice; please try again.")


if __name__ == "__main__":
    main()
