#!/usr/bin/env python3
"""
SentinelRisk — Dataset Validation CLI

Usage:
    python scripts/validate_data.py [--data-dir data/generated]

Validates the CSV dataset files against relational constraints,
timestamp causality, entity counts, fraud prevalence, and sanity limits.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.validation.validator import DatasetValidator


def main():
    parser = argparse.ArgumentParser(description="Validate SentinelRisk dataset.")
    parser.add_argument("--data-dir", type=str, default="data/generated", help="Directory containing CSV files")
    args = parser.parse_args()

    data_path = PROJECT_ROOT / args.data_dir
    if not data_path.exists():
        print(f"[!] Error: Data directory not found at {data_path}")
        print("Please run `python scripts/generate_data.py` first.")
        sys.exit(1)

    print(f"Loading and validating dataset from: {data_path}")
    validator = DatasetValidator(data_dir=data_path)
    report = validator.validate()
    validator.print_summary()

    if not report["is_valid"]:
        sys.exit(1)
    else:
        print("\n[OK] All dataset integrity checks PASSED successfully.")


if __name__ == "__main__":
    main()
