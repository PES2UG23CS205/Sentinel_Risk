"""
SentinelRisk — Master Data Generation Pipeline

Orchestrates the end-to-end synthetic payments world simulation:
  1. Merchants generation (1,500 across 10 categories)
  2. Customers generation (40,000 across 4 behavioral segments)
  3. Devices & legitimate device sharing
  4. Payment instruments (synthetic tokenized types)
  5. Behavioral normal transaction simulation (6 months)
  6. Injection of 3 Fraud Archetypes (ATO, Card Testing, Coordinated Rings)
  7. Label noise application with ground truth preservation
  8. Delayed dispute generation
  9. Deterministic CSV and metadata export
"""

import os
import json
import csv
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from simulation.data_generation.config import GenerationConfig
from simulation.data_generation.merchants import generate_merchants
from simulation.data_generation.customers import generate_customers
from simulation.data_generation.devices import generate_devices
from simulation.data_generation.payment_instruments import generate_payment_instruments
from simulation.data_generation.transactions import generate_normal_transactions
from simulation.data_generation.fraud_archetypes import inject_fraud_archetypes
from simulation.data_generation.disputes import generate_disputes


class SyntheticDataGenerator:
    """Master generator for SentinelRisk synthetic payments world."""

    def __init__(self, config: GenerationConfig | None = None):
        self.config = config or GenerationConfig()
        self.rng = np.random.default_rng(self.config.seed)

    def generate(self) -> dict:
        """
        Execute the full simulation pipeline.

        Returns:
            Dictionary containing generated entities and summary statistics.
        """
        # 1. Generate Merchants
        merchants = generate_merchants(self.rng, self.config)

        # 2. Generate Customers
        customers = generate_customers(self.rng, self.config, merchants)

        # 3. Generate Devices
        devices, customer_devices, device_customers = generate_devices(self.rng, self.config, customers)

        # 4. Generate Payment Instruments
        payment_instruments, customer_pis = generate_payment_instruments(self.rng, self.config, customers)

        # 5. Generate Normal Transactions
        transactions = generate_normal_transactions(
            self.rng,
            self.config,
            merchants,
            customers,
            customer_devices,
            customer_pis,
        )

        # 6. Inject Fraud Archetypes & Apply Label Noise
        transactions = inject_fraud_archetypes(
            self.rng,
            self.config,
            transactions,
            merchants,
            customers,
            devices,
            payment_instruments,
            customer_devices,
            customer_pis,
        )

        # 7. Generate Disputes
        disputes = generate_disputes(self.rng, self.config, transactions)

        # Calculate statistics
        total_txns = len(transactions)
        fraud_gt_txns = sum(1 for t in transactions if t["is_fraud_ground_truth"])
        observed_fraud_txns = sum(1 for t in transactions if t["is_fraud"])
        fraud_prevalence = (fraud_gt_txns / total_txns) if total_txns > 0 else 0.0

        ato_count = sum(1 for t in transactions if t["fraud_archetype"] == "account_takeover")
        ct_count = sum(1 for t in transactions if t["fraud_archetype"] == "card_testing")
        ring_count = sum(1 for t in transactions if t["fraud_archetype"] == "coordinated_ring")

        # Distinct coordinated rings
        unique_rings = {t["fraud_case_id"] for t in transactions if t["fraud_archetype"] == "coordinated_ring"}

        amounts = [t["amount"] for t in transactions]
        avg_amount = float(np.mean(amounts)) if amounts else 0.0
        median_amount = float(np.median(amounts)) if amounts else 0.0

        stats = {
            "dataset_version": self.config.dataset_version,
            "seed": self.config.seed,
            "num_merchants": len(merchants),
            "num_customers": len(customers),
            "num_devices": len(devices),
            "num_payment_instruments": len(payment_instruments),
            "num_transactions": total_txns,
            "num_disputes": len(disputes),
            "fraud_transactions_ground_truth": fraud_gt_txns,
            "fraud_transactions_observed": observed_fraud_txns,
            "fraud_prevalence": round(fraud_prevalence, 4),
            "fraud_prevalence_pct": f"{fraud_prevalence * 100:.2f}%",
            "account_takeover_count": ato_count,
            "card_testing_count": ct_count,
            "coordinated_ring_count": ring_count,
            "distinct_rings": len(unique_rings),
            "avg_transaction_amount": round(avg_amount, 2),
            "median_transaction_amount": round(median_amount, 2),
            "sim_start": self.config.sim_start.isoformat(),
            "sim_end": self.config.sim_end.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "merchants": merchants,
            "customers": customers,
            "devices": devices,
            "payment_instruments": payment_instruments,
            "transactions": transactions,
            "disputes": disputes,
            "stats": stats,
        }

    def export_csv(self, dataset: dict, output_dir: str | Path) -> dict[str, Path]:
        """
        Export generated dataset to CSV files in output_dir.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        paths = {}

        # 1. Merchants CSV
        merchants_path = out_path / "merchants.csv"
        with open(merchants_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "category", "created_at", "typical_order_value", "typical_order_value_std", "expected_daily_transactions", "tier"])
            for m in dataset["merchants"]:
                writer.writerow([
                    m["id"], m["name"], m["category"],
                    m["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    m["typical_order_value"], m["typical_order_value_std"],
                    m["expected_daily_transactions"], m["tier"],
                ])
        paths["merchants"] = merchants_path

        # 2. Customers CSV
        customers_path = out_path / "customers.csv"
        with open(customers_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "segment", "account_created_at", "typical_amount", "txn_per_month"])
            for c in dataset["customers"]:
                writer.writerow([
                    c["id"], c["segment"],
                    c["account_created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    c["typical_amount"], c["txn_per_month"],
                ])
        paths["customers"] = customers_path

        # 3. Devices CSV
        devices_path = out_path / "devices.csv"
        with open(devices_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "created_at"])
            for d in dataset["devices"]:
                writer.writerow([
                    d["id"],
                    d["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                ])
        paths["devices"] = devices_path

        # 4. Payment Instruments CSV
        pis_path = out_path / "payment_instruments.csv"
        with open(pis_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "customer_id", "type", "created_at"])
            for pi in dataset["payment_instruments"]:
                writer.writerow([
                    pi["id"], pi["customer_id"], pi["type"],
                    pi["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                ])
        paths["payment_instruments"] = pis_path

        # 5. Transactions CSV
        txns_path = out_path / "transactions.csv"
        with open(txns_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "merchant_id", "customer_id", "device_id",
                "payment_instrument_id", "amount", "currency",
                "timestamp", "status", "is_fraud", "fraud_archetype",
                "fraud_case_id", "is_fraud_ground_truth"
            ])
            for t in dataset["transactions"]:
                writer.writerow([
                    t["id"], t["merchant_id"], t["customer_id"],
                    t["device_id"], t["payment_instrument_id"],
                    t["amount"], t["currency"],
                    t["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    t["status"], t["is_fraud"], t["fraud_archetype"],
                    t["fraud_case_id"] or "", t["is_fraud_ground_truth"],
                ])
        paths["transactions"] = txns_path

        # 6. Disputes CSV
        disputes_path = out_path / "disputes.csv"
        with open(disputes_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "transaction_id", "reason", "status", "created_at"])
            for d in dataset["disputes"]:
                writer.writerow([
                    d["id"], d["transaction_id"], d["reason"],
                    d["status"], d["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                ])
        paths["disputes"] = disputes_path

        # 7. Metadata JSON
        meta_path = out_path / "generation_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(dataset["stats"], f, indent=2)
        paths["metadata"] = meta_path

        return paths
