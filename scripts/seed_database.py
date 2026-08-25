#!/usr/bin/env python3
"""
SentinelRisk — Database Seeding Script

Usage:
    python scripts/seed_database.py [--data-dir data/generated] [--batch-size 5000]

Reads generated CSV data and seeds the SQLite database with high-performance
batched inserts while preserving relational integrity.
"""

import sys
import os
import csv
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.database import SessionLocal, init_database, engine, Base
from backend.app.db.models import (
    Merchant, Customer, Device, PaymentInstrument,
    Transaction, Dispute, AuditLog, Case, Incident
)


def parse_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def seed_database(data_dir: Path, batch_size: int = 5000):
    print("=" * 65)
    print("  SENTINELRISK — DATABASE SEEDER")
    print("=" * 65)
    print(f"Source Directory: {data_dir}")
    print(f"Batch Size      : {batch_size}")
    print("-" * 65)

    if not data_dir.exists():
        print(f"[!] Error: Data directory {data_dir} does not exist.")
        print("Run `python scripts/generate_data.py` first.")
        sys.exit(1)

    # Initialize / reset tables
    print("Initializing database tables...")
    init_database()

    db = SessionLocal()
    try:
        # Clear existing data in reverse foreign-key order
        print("Clearing any existing data...")
        db.query(Dispute).delete()
        db.query(Case).delete()
        db.query(AuditLog).delete()
        db.query(Incident).delete()
        db.query(Transaction).delete()
        db.query(PaymentInstrument).delete()
        db.query(Device).delete()
        db.query(Customer).delete()
        db.query(Merchant).delete()
        db.commit()

        # 1. Seed Merchants
        print("Seeding merchants...")
        m_rows = []
        with open(data_dir / "merchants.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                m_rows.append({
                    "id": int(r["id"]),
                    "name": r["name"],
                    "category": r["category"],
                    "created_at": parse_datetime(r["created_at"]),
                })
        db.bulk_insert_mappings(Merchant, m_rows)
        db.commit()
        print(f"  [OK] Seeded {len(m_rows):,} merchants")

        # 2. Seed Customers
        print("Seeding customers...")
        c_rows = []
        with open(data_dir / "customers.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                c_rows.append({
                    "id": int(r["id"]),
                    "merchant_id": None,
                    "created_at": parse_datetime(r["account_created_at"]),
                })
        for i in range(0, len(c_rows), batch_size):
            db.bulk_insert_mappings(Customer, c_rows[i:i + batch_size])
            db.commit()
        print(f"  [OK] Seeded {len(c_rows):,} customers")

        # 3. Seed Devices
        print("Seeding devices...")
        d_rows = []
        with open(data_dir / "devices.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d_rows.append({
                    "id": int(r["id"]),
                    "created_at": parse_datetime(r["created_at"]),
                })
        for i in range(0, len(d_rows), batch_size):
            db.bulk_insert_mappings(Device, d_rows[i:i + batch_size])
            db.commit()
        print(f"  [OK] Seeded {len(d_rows):,} devices")

        # 4. Seed Payment Instruments
        print("Seeding payment instruments...")
        pi_rows = []
        with open(data_dir / "payment_instruments.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                pi_rows.append({
                    "id": int(r["id"]),
                    "customer_id": int(r["customer_id"]),
                    "type": r["type"],
                    "created_at": parse_datetime(r["created_at"]),
                })
        for i in range(0, len(pi_rows), batch_size):
            db.bulk_insert_mappings(PaymentInstrument, pi_rows[i:i + batch_size])
            db.commit()
        print(f"  [OK] Seeded {len(pi_rows):,} payment instruments")

        # 5. Seed Transactions
        print("Seeding transactions...")
        tx_rows = []
        with open(data_dir / "transactions.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                tx_rows.append({
                    "id": int(r["id"]),
                    "merchant_id": int(r["merchant_id"]),
                    "customer_id": int(r["customer_id"]),
                    "device_id": int(r["device_id"]) if r["device_id"] else None,
                    "payment_instrument_id": int(r["payment_instrument_id"]) if r["payment_instrument_id"] else None,
                    "amount": float(r["amount"]),
                    "currency": r["currency"],
                    "timestamp": parse_datetime(r["timestamp"]),
                    "status": r["status"],
                    "is_fraud": r["is_fraud"].lower() in ("true", "1"),
                    "fraud_archetype": r["fraud_archetype"],
                    "fraud_case_id": r["fraud_case_id"] or None,
                    "is_fraud_ground_truth": r["is_fraud_ground_truth"].lower() in ("true", "1"),
                })
        for i in range(0, len(tx_rows), batch_size):
            db.bulk_insert_mappings(Transaction, tx_rows[i:i + batch_size])
            db.commit()
        print(f"  [OK] Seeded {len(tx_rows):,} transactions")

        # 6. Seed Disputes
        print("Seeding disputes...")
        dp_rows = []
        with open(data_dir / "disputes.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                dp_rows.append({
                    "id": int(r["id"]),
                    "transaction_id": int(r["transaction_id"]),
                    "reason": r["reason"],
                    "status": r["status"],
                    "created_at": parse_datetime(r["created_at"]),
                })
        for i in range(0, len(dp_rows), batch_size):
            db.bulk_insert_mappings(Dispute, dp_rows[i:i + batch_size])
            db.commit()
        print(f"  [OK] Seeded {len(dp_rows):,} disputes")

        # 7. Record an Audit Log entry for the seeding event
        audit_entry = AuditLog(
            event_type="dataset.seeded",
            entity_type="system",
            entity_id=1,
            payload=f'{{"merchants": {len(m_rows)}, "customers": {len(c_rows)}, "transactions": {len(tx_rows)}, "disputes": {len(dp_rows)}}}',
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        db.commit()

        print("-" * 65)
        print("DATABASE SEEDING COMPLETE & VERIFIED!")
        print(f"  Database file: {engine.url.database}")
        print("=" * 65)

    except Exception as e:
        db.rollback()
        print(f"\n[!] Database seeding failed: {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed SentinelRisk database with synthetic data.")
    parser.add_argument("--data-dir", type=str, default="data/generated", help="Directory containing CSV files")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for database inserts")
    args = parser.parse_args()

    data_dir = PROJECT_ROOT / args.data_dir
    seed_database(data_dir, args.batch_size)


if __name__ == "__main__":
    main()
