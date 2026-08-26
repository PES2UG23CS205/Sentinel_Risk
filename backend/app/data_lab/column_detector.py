"""
SentinelRisk — Data Lab Column Detector & Type Inference Engine

Provides:
  - Robust column alias matching
  - Confidence scoring (HIGH, MEDIUM, LOW, UNMATCHED)
  - Data type inference (string, float, int, datetime, boolean)
  - Sample value inspection
"""

import re
from datetime import datetime
from typing import Any, Optional
from backend.app.data_lab.models import ColumnConfidence, DetectedColumn


# Canonical SentinelRisk target fields and their prioritized alias lists
CANONICAL_ALIASES: dict[str, list[str]] = {
    "transaction_id": [
        "transaction_id", "txn_id", "tx_id", "payment_id", "id", "trans_id",
        "reference_id", "order_id", "order_number", "tx_hash", "transactionid"
    ],
    "timestamp": [
        "timestamp", "transaction_time", "created_at", "event_time", "datetime",
        "date_time", "time", "date", "tx_time", "tx_datetime", "txn_date", "created"
    ],
    "amount": [
        "amount", "transaction_amount", "payment_amount", "value", "amt",
        "price", "txn_amount", "total", "volume", "grand_total", "bill_amount"
    ],
    "customer_id": [
        "customer_id", "user_id", "cust_id", "buyer_id", "client_id",
        "account_id", "user", "customer", "shopper_id", "payer_id", "consumer_id"
    ],
    "merchant_id": [
        "merchant_id", "seller_id", "vendor_id", "store_id", "terminal_id",
        "merchant", "seller", "vendor", "store", "terminal", "outlet_id", "shop_id"
    ],
    "device_id": [
        "device_id", "dev_id", "device_fingerprint", "hardware_id", "device",
        "fingerprint", "device_identifier", "mobile_device_id", "client_device_id"
    ],
    "payment_instrument_id": [
        "payment_instrument_id", "card_id", "card_token", "card", "pi_id",
        "payment_method", "instrument_id", "card_number", "token_id", "pan_token"
    ],
    "currency": [
        "currency", "currency_code", "curr", "tx_currency", "iso_currency"
    ],
    "ip_address": [
        "ip_address", "ip", "client_ip", "user_ip", "source_ip", "remote_addr"
    ],
    "is_fraud": [
        "is_fraud", "fraud", "fraud_label", "target", "label", "class",
        "is_fraudulent", "fraud_flag", "is_chargeback", "ground_truth"
    ],
}


def infer_data_type(values: list[Any]) -> str:
    """Infer high-level data type from a list of non-null string/raw sample values."""
    if not values:
        return "string"

    # Check for boolean/binary fraud labels
    bool_count = sum(1 for v in values if str(v).strip().lower() in ("0", "1", "true", "false", "yes", "no"))
    if bool_count == len(values):
        return "boolean"

    # Check for integer
    int_count = 0
    for v in values:
        s = str(v).strip()
        if re.match(r"^-?\d+$", s):
            int_count += 1
    if int_count == len(values):
        return "int"

    # Check for float / currency amounts
    float_count = 0
    for v in values:
        s = str(v).strip().replace("$", "").replace("€", "").replace("₹", "").replace(",", "")
        try:
            float(s)
            float_count += 1
        except ValueError:
            pass
    if float_count == len(values):
        return "float"

    # Check for datetime
    dt_count = 0
    for v in values:
        s = str(v).strip()
        if len(s) >= 8 and (("-" in s or "/" in s) or ("T" in s or ":" in s)):
            dt_count += 1
    if dt_count >= max(1, int(len(values) * 0.8)):
        return "datetime"

    return "string"


class ColumnDetector:
    """Automatic header detection and schema inference."""

    @classmethod
    def detect_columns(
        cls,
        headers: list[str],
        sample_rows: list[dict[str, Any]]
    ) -> list[DetectedColumn]:
        """
        Analyze headers and sample row values to detect canonical SentinelRisk fields
        with confidence rating.
        """
        detected_list: list[DetectedColumn] = []
        assigned_targets: set[str] = set()

        # Step 1: Collect non-null sample values & null counts per column
        col_samples: dict[str, list[Any]] = {h: [] for h in headers}
        col_null_counts: dict[str, int] = {h: 0 for h in headers}

        for row in sample_rows:
            for h in headers:
                val = row.get(h)
                if val is None or str(val).strip() == "" or str(val).strip().lower() in ("null", "none", "nan"):
                    col_null_counts[h] += 1
                else:
                    if len(col_samples[h]) < 5:
                        col_samples[h].append(val)

        # Step 2: Evaluate each header against canonical targets
        for orig_header in headers:
            norm_name = orig_header.lower().strip().replace(" ", "_").replace("-", "_")
            samples = col_samples.get(orig_header, [])
            inferred_type = infer_data_type(samples)
            null_c = col_null_counts.get(orig_header, 0)

            best_match: Optional[str] = None
            best_confidence = ColumnConfidence.UNMATCHED

            # A. Exact alias match
            for target_field, aliases in CANONICAL_ALIASES.items():
                if target_field in assigned_targets:
                    continue
                if norm_name in aliases:
                    # Top exact match
                    best_match = target_field
                    best_confidence = ColumnConfidence.HIGH
                    break

            # B. Substring / Prefix / Suffix match if not already exact
            if not best_match:
                for target_field, aliases in CANONICAL_ALIASES.items():
                    if target_field in assigned_targets:
                        continue
                    for alias in aliases:
                        if (alias in norm_name or norm_name in alias) and len(norm_name) >= 3:
                            best_match = target_field
                            best_confidence = ColumnConfidence.MEDIUM
                            break
                    if best_match:
                        break

            # C. Type-heuristic adjustment for critical fields
            if best_match == "amount" and inferred_type not in ("float", "int"):
                best_confidence = ColumnConfidence.LOW
            elif best_match == "timestamp" and inferred_type != "datetime":
                # Check if it might be a unix epoch
                if inferred_type in ("float", "int") and samples and float(samples[0]) > 1e8:
                    best_confidence = ColumnConfidence.MEDIUM
                else:
                    best_confidence = ColumnConfidence.LOW

            if best_match and best_confidence in (ColumnConfidence.HIGH, ColumnConfidence.MEDIUM):
                assigned_targets.add(best_match)

            detected_list.append(
                DetectedColumn(
                    original_name=orig_header,
                    suggested_field=best_match,
                    confidence=best_confidence,
                    detected_type=inferred_type,
                    null_count=null_c,
                    sample_values=[str(v) for v in samples[:3]],
                )
            )

        return detected_list

    @classmethod
    def get_default_mapping(cls, detected_columns: list[DetectedColumn]) -> dict[str, Optional[str]]:
        """Extract a canonical mapping dictionary from high/medium confidence detected columns."""
        mapping: dict[str, Optional[str]] = {k: None for k in CANONICAL_ALIASES.keys()}
        for col in detected_columns:
            if col.suggested_field and col.confidence in (ColumnConfidence.HIGH, ColumnConfidence.MEDIUM):
                mapping[col.suggested_field] = col.original_name
        return mapping
