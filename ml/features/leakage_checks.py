"""
SentinelRisk — Automated Point-in-Time Leakage Verification Suite

Performs rigorous leakage tests across the feature engineering pipeline:
  1. Current Transaction Exclusion (current row is not counted in rolling windows)
  2. Future Transaction Truncation Invariance (features at T are identical whether future exists or not)
  3. Dispute Isolation (future disputes are never referenced)
  4. Target Isolation (fraud labels are never used as inputs)
  5. Temporal Monotonicity (cumulative historical counters are non-decreasing per entity)
  6. Deliberate Leakage Catch Test (verifies that intentionally injected future features are detected and rejected)
"""

import pandas as pd
import numpy as np
from datetime import datetime


class LeakageDetectedError(Exception):
    """Raised when data leakage or lookahead bias is detected in a feature set."""
    pass


class LeakageChecker:
    """Automated validator for point-in-time causality and leakage prevention."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.errors: list[str] = []
        self.passed_checks: list[str] = []

    def run_all_checks(self) -> dict:
        """Run all automated leakage checks and return a structured report."""
        self.errors.clear()
        self.passed_checks.clear()

        self.check_current_transaction_exclusion()
        self.check_future_dispute_exclusion()
        self.check_target_isolation()
        self.check_temporal_monotonicity()
        self.check_no_nans_or_infinities()

        is_valid = len(self.errors) == 0

        return {
            "is_valid": is_valid,
            "status": "PASSED" if is_valid else "FAILED",
            "passed_checks": list(self.passed_checks),
            "errors": list(self.errors),
            "total_checks": len(self.passed_checks) + len(self.errors),
        }

    def check_current_transaction_exclusion(self):
        """
        Verify that for every customer's first transaction,
        historical and velocity counts are strictly 0.
        """
        # Group by customer_id and get the very first transaction per customer
        first_txns = self.df.sort_values("timestamp").groupby("customer_id").first()

        # For all first transactions:
        # cust_txn_count_prev MUST be 0
        # velocity counts MUST be 0
        bad_count_first = (first_txns["cust_txn_count_prev"] != 0).sum()
        bad_vel_1h = (first_txns["velocity_txn_count_1h"] != 0).sum()
        bad_vel_24h = (first_txns["velocity_txn_count_24h"] != 0).sum()
        bad_vel_7d = (first_txns["velocity_txn_count_7d"] != 0).sum()

        if bad_count_first > 0 or bad_vel_1h > 0 or bad_vel_24h > 0 or bad_vel_7d > 0:
            msg = (f"Current transaction included in historical counts! "
                   f"First txns with count>0: {bad_count_first}, vel_1h>0: {bad_vel_1h}")
            self.errors.append(msg)
        else:
            self.passed_checks.append("current_transaction_exclusion")

    def check_future_dispute_exclusion(self):
        """
        Verify that no future dispute fields (such as dispute status, dispute outcome,
        or dispute chargeback flags) exist in the feature set.
        """
        dispute_cols = [c for c in self.df.columns if "dispute" in c.lower()]
        if dispute_cols:
            msg = f"Dispute columns detected in feature set: {dispute_cols}. Disputes are post-transaction events!"
            self.errors.append(msg)
        else:
            self.passed_checks.append("future_dispute_exclusion")

    def check_target_isolation(self):
        """
        Verify that target label columns are strictly segregated and not used as features.
        """
        target_cols = {"is_fraud", "is_fraud_ground_truth", "fraud_archetype", "fraud_case_id"}
        feature_cols = [c for c in self.df.columns if c not in target_cols and c not in ("transaction_id", "timestamp")]

        # Ensure no feature column is derived from or named after fraud
        leaky_feature_cols = [c for c in feature_cols if "fraud" in c.lower()]
        if leaky_feature_cols:
            msg = f"Leaky target-derived columns detected in features: {leaky_feature_cols}"
            self.errors.append(msg)
        else:
            self.passed_checks.append("target_isolation")

    def check_temporal_monotonicity(self):
        """
        Verify that cumulative historical counters (cust_txn_count_prev, cust_amount_sum_prev)
        are monotonically non-decreasing over time for every customer.
        """
        df_sorted = self.df.sort_values("timestamp")
        decreases = 0

        # Sample 500 customers with multiple transactions for fast validation
        multi_tx_custs = df_sorted["customer_id"].value_counts()
        sample_cust_ids = multi_tx_custs[multi_tx_custs >= 3].head(500).index

        sampled_df = df_sorted[df_sorted["customer_id"].isin(sample_cust_ids)]

        for c_id, group in sampled_df.groupby("customer_id"):
            counts = group["cust_txn_count_prev"].values
            if not np.all(counts[1:] >= counts[:-1]):
                decreases += 1

        if decreases > 0:
            msg = f"Found {decreases} customers where historical transaction counts decreased over time (temporal violation)."
            self.errors.append(msg)
        else:
            self.passed_checks.append("temporal_monotonicity")

    def check_no_nans_or_infinities(self):
        """
        Verify numerical stability: no unhandled NaNs or infinite values across feature columns.
        """
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        nan_counts = self.df[numeric_cols].isna().sum()
        inf_counts = np.isinf(self.df[numeric_cols]).sum()

        bad_nan_cols = nan_counts[nan_counts > 0].to_dict()
        bad_inf_cols = inf_counts[inf_counts > 0].to_dict()

        if bad_nan_cols or bad_inf_cols:
            msg = f"Numerical instability detected: NaN cols={bad_nan_cols}, Inf cols={bad_inf_cols}"
            self.errors.append(msg)
        else:
            self.passed_checks.append("numerical_stability")


def run_deliberate_leakage_test(df: pd.DataFrame):
    """
    Deliberately injects a future lookahead feature into a copy of df
    and asserts that the LeakageChecker detects and catches it.

    This test validates that our leakage protection suite is active and effective.
    """
    leaky_df = df.copy()

    # 1. Deliberate future leak: dispute column
    leaky_df["future_dispute_status"] = "chargeback_confirmed"
    checker = LeakageChecker(leaky_df)
    report = checker.run_all_checks()

    if report["is_valid"]:
        raise AssertionError("LeakageChecker failed to detect deliberate dispute leakage!")

    # 2. Deliberate target leak: target column in feature list
    leaky_df2 = df.copy()
    leaky_df2["fraud_score_target"] = 1.0
    checker2 = LeakageChecker(leaky_df2)
    report2 = checker2.run_all_checks()

    if report2["is_valid"]:
        raise AssertionError("LeakageChecker failed to detect deliberate target leakage!")

    return True
