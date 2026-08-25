#!/usr/bin/env python3
"""
SentinelRisk — Bootstrap & Environment Setup Script

Usage:
    python scripts/setup_demo.py

Verifies prerequisites, ensures SQLite database, feature datasets, graph artifacts,
and ML model files exist. Bootstraps missing artifacts if required.
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_file(path: Path, description: str) -> bool:
    if path.exists():
        size_kb = path.stat().st_size / 1024
        print(f"  [OK] {description} ({path.name}, {size_kb:.1f} KB)")
        return True
    else:
        print(f"  [MISSING] {description} ({path.name})")
        return False


def main():
    print("=" * 80)
    print("      SENTINELRISK — DEMO ENVIRONMENT BOOTSTRAP CHECK")
    print("=" * 80)

    # 1. Check directories
    dirs = ["data/raw", "data/features", "ml/models", "evaluation/policy_v1", "evaluation/production", "config"]
    print("\n1. Verifying Project Directories:")
    for d in dirs:
        p = PROJECT_ROOT / d
        p.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {d}/")

    # 2. Check essential artifacts
    print("\n2. Checking Core Artifacts:")
    db_ok = check_file(PROJECT_ROOT / "sentinelrisk.db", "SQLite Database")
    raw_ok = check_file(PROJECT_ROOT / "data/raw/transactions.csv", "Synthetic Payments Dataset (67k txns)")
    feat_ok = check_file(PROJECT_ROOT / "data/features/transaction_features.csv", "Point-in-Time Features")
    graph_ok = check_file(PROJECT_ROOT / "data/features/graph_features.csv", "Graph Ring Features")
    lgb_ok = check_file(PROJECT_ROOT / "ml/models/lightgbm_model.pkl", "LightGBM Supervised Model")
    policy_ok = check_file(PROJECT_ROOT / "config/policy.yaml", "Policy Engine Configuration")

    # 3. Bootstrap missing components if needed
    if not db_ok:
        print("\n[!] Initializing SQLite database...")
        from backend.app.db.database import init_database
        init_database()
        print("  [OK] Database schema initialized.")

    if not (feat_ok and graph_ok and lgb_ok and policy_ok):
        print("\n[!] Notice: Some pre-computed artifacts are missing. Run data/model generation scripts if needed.")
    else:
        print("\n[SUCCESS] All prerequisites and pre-computed artifacts are in place.")
        print("You can run the demo immediately via:")
        print("  python scripts/demo.py --scenario WHAT_BROKE_AT_2AM")


if __name__ == "__main__":
    main()
