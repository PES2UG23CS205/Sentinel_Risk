#!/usr/bin/env python3
"""
SentinelRisk — Synthetic Data Generation CLI

Usage:
    python scripts/generate_data.py [--seed 42] [--output-dir data/generated]

Generates a deterministic synthetic payments ecosystem including merchants,
customers, devices, payment instruments, transactions, and disputes over
a 6-month simulated window.
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.data_generation.config import GenerationConfig
from simulation.data_generation.generator import SyntheticDataGenerator
from simulation.validation.validator import DatasetValidator


def main():
    parser = argparse.ArgumentParser(description="Generate SentinelRisk synthetic payment data.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--output-dir", type=str, default="data/generated", help="Output directory for CSVs and metadata")
    parser.add_argument("--merchants", type=int, default=1500, help="Target merchant count (default: 1500)")
    parser.add_argument("--customers", type=int, default=40000, help="Target customer count (default: 40000)")
    parser.add_argument("--transactions", type=int, default=60000, help="Target transaction count (default: 60000)")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / args.output_dir

    print("=" * 65)
    print(f"  SENTINELRISK — SYNTHETIC DATA GENERATOR (Seed: {args.seed})")
    print("=" * 65)
    print(f"Target Configuration:")
    print(f"  Merchants   : {args.merchants:,}")
    print(f"  Customers   : {args.customers:,}")
    print(f"  Transactions: {args.transactions:,}")
    print(f"  Output Dir  : {out_dir}")
    print("-" * 65)
    print("Generating simulated payments world...")

    config = GenerationConfig(
        seed=args.seed,
        num_merchants=args.merchants,
        num_customers=args.customers,
        target_transactions=args.transactions,
    )

    generator = SyntheticDataGenerator(config)
    dataset = generator.generate()

    print("Generation complete! Validating dataset integrity...")
    validator = DatasetValidator(dataset=dataset)
    report = validator.validate()

    validator.print_summary()

    if not report["is_valid"]:
        print("\n[!] DATASET VALIDATION FAILED! Check errors above.")
        sys.exit(1)

    print(f"\nExporting dataset to {out_dir}...")
    paths = generator.export_csv(dataset, out_dir)
    print(f"[OK] Successfully exported {len(paths)} files:")
    for name, path in paths.items():
        size_kb = path.stat().st_size / 1024
        print(f"  - {path.name} ({size_kb:.1f} KB)")

    print("\nDataset ready for database seeding.")
    print("Run `python scripts/seed_database.py` to populate SQLite.")


if __name__ == "__main__":
    main()
