"""
SentinelRisk — Point-in-Time Graph Feature Extraction Pipeline

Executes a high-performance single-pass incremental chronological extraction across all transactions.
Enforces the same-timestamp ordering semantics:
  1. For all transactions at timestamp T, features are evaluated strictly on graph state < T.
  2. After scoring all transactions at T, their edges are committed to the graph.
Guarantees zero current-row, future-event, or intra-timestamp data leakage.
"""

import time
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

from backend.app.graph.config import GraphConfig
from backend.app.graph.entity_graph import EntityGraph
from backend.app.graph.ring_detector import RingDetector


class GraphFeaturePipeline:
    """Incremental point-in-time graph feature generator."""

    def __init__(self, config: GraphConfig | None = None):
        self.config = config or GraphConfig()
        self.graph = EntityGraph()
        self.detector = RingDetector(self.config)

    def process_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process transactions chronologically and extract point-in-time graph features.

        Args:
            df: DataFrame containing at least ['transaction_id', 'timestamp', 'customer_id',
                                            'device_id', 'payment_instrument_id', 'merchant_id', 'amount']
        Returns:
            DataFrame containing extracted graph features aligned with transaction_id.
        """
        # Ensure chronological ordering
        df_sorted = df.sort_values(["timestamp", "transaction_id"]).reset_index(drop=True)
        records = df_sorted.to_dict("records")
        n_total = len(records)

        feature_records = []
        start_time = time.perf_counter()

        i = 0
        while i < n_total:
            current_ts = records[i]["timestamp"]

            # Group consecutive transactions sharing the exact same timestamp
            j = i
            while j < n_total and records[j]["timestamp"] == current_ts:
                j += 1

            same_ts_batch = records[i:j]

            # Parse epoch timestamp once for batch
            dt = datetime.strptime(str(current_ts), "%Y-%m-%d %H:%M:%S")
            ts_sec = dt.timestamp()

            # Phase 1: Score all transactions in same_ts_batch using graph state < T
            for row in same_ts_batch:
                txn_id = row["transaction_id"]
                cust_id = row["customer_id"]
                dev_id = row["device_id"]
                pi_id = row["payment_instrument_id"]
                merch_id = row["merchant_id"]

                # Extract point-in-time metrics
                dev_cust_cnt = self.graph.get_device_customer_count(dev_id)
                dev_merch_cnt = self.graph.get_device_merchant_count(dev_id)
                pi_cust_cnt = self.graph.get_pi_customer_count(pi_id)
                pi_merch_cnt = self.graph.get_pi_merchant_count(pi_id)
                cust_shared_dev = self.graph.get_customer_shared_device_count(cust_id)
                cust_shared_pi = self.graph.get_customer_shared_pi_count(cust_id)
                comp_size = self.graph.get_entity_connected_component_size("customer", cust_id)

                # Ring detection & scoring
                ring_eval = self.detector.evaluate_transaction_cluster(
                    self.graph, cust_id, dev_id, pi_id, merch_id
                )

                feature_records.append({
                    "transaction_id": txn_id,
                    "device_customer_count": dev_cust_cnt,
                    "device_merchant_count": dev_merch_cnt,
                    "payment_instrument_customer_count": pi_cust_cnt,
                    "payment_instrument_merchant_count": pi_merch_cnt,
                    "customer_shared_device_count": cust_shared_dev,
                    "customer_shared_payment_count": cust_shared_pi,
                    "graph_component_size": comp_size,
                    "graph_ring_score": ring_eval["ring_score"],
                    "graph_ring_candidate": int(ring_eval["is_ring_candidate"]),
                })

            # Phase 2: Commit all transactions in same_ts_batch to the graph
            for row in same_ts_batch:
                self.graph.add_transaction_edges(
                    customer_id=row["customer_id"],
                    device_id=row["device_id"],
                    payment_instrument_id=row["payment_instrument_id"],
                    merchant_id=row["merchant_id"],
                    timestamp_sec=ts_sec,
                    amount=float(row.get("amount", 0.0)),
                )

            i = j

        elapsed = time.perf_counter() - start_time
        throughput = n_total / max(0.001, elapsed)

        result_df = pd.DataFrame(feature_records)
        result_df.attrs["elapsed_seconds"] = elapsed
        result_df.attrs["throughput_txns_per_sec"] = throughput

        return result_df
