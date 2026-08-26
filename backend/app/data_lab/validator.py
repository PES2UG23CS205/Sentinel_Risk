"""
SentinelRisk — Data Lab Dataset Quality Validator

Performs deep data quality validation on mapped transaction datasets:
  - Required fields presence (amount, timestamp)
  - Amount validity (positive numeric, currency symbol stripping, negative/zero check)
  - Timestamp standardization & chronologicity check
  - Null percentage & cardinality verification
  - Duplicate transaction ID detection
  - Missing entity tokens impact analysis
"""

import re
from datetime import datetime
from typing import Any, Optional
from backend.app.data_lab.models import ValidationIssue, ValidationSummary


def parse_standard_datetime(val: Any) -> Optional[datetime]:
    """Parse a flexible datetime string or unix epoch into a standard datetime object."""
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("null", "none", "nan", ""):
        return None

    # Standard formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y/%m/%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue

    # Unix timestamp detection
    try:
        ts_float = float(val_str)
        if ts_float > 1e11:  # Milliseconds
            ts_float /= 1000.0
        if ts_float > 1e8:   # Reasonable timestamp (> 1973)
            return datetime.fromtimestamp(ts_float)
    except (ValueError, OSError):
        pass

    return None


def parse_numeric_amount(val: Any) -> tuple[Optional[float], Optional[str]]:
    """Parse raw amount into float; returns (amount_val, error_reason)."""
    if val is None:
        return None, "Amount is null or missing"
    s = str(val).strip()
    if not s or s.lower() in ("null", "none", "nan", ""):
        return None, "Amount is empty"

    # Clean currency symbols and commas
    cleaned = s.replace("$", "").replace("€", "").replace("₹", "").replace("£", "").replace(",", "").strip()
    try:
        num = float(cleaned)
        if num < 0.0:
            return num, "Negative transaction amount"
        if num == 0.0:
            return num, "Zero transaction amount"
        return num, None
    except ValueError:
        return None, f"Non-numeric amount string: '{val}'"


class DataLabValidator:
    """Validates raw dataset rows against user column mappings."""

    @classmethod
    def validate_dataset(
        cls,
        rows: list[dict[str, Any]],
        mapping: dict[str, Optional[str]],
    ) -> ValidationSummary:
        """
        Execute comprehensive data quality evaluation across all dataset rows.
        """
        total_rows = len(rows)
        if total_rows == 0:
            return ValidationSummary(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                issues=[
                    ValidationIssue(
                        severity="ERROR",
                        message="Uploaded dataset contains 0 rows.",
                        affected_rows=0,
                    )
                ],
            )

        col_txn_id = mapping.get("transaction_id")
        col_timestamp = mapping.get("timestamp")
        col_amount = mapping.get("amount")
        col_cust = mapping.get("customer_id")
        col_merch = mapping.get("merchant_id")
        col_dev = mapping.get("device_id")
        col_pi = mapping.get("payment_instrument_id")
        col_fraud = mapping.get("is_fraud")

        issues: list[ValidationIssue] = []

        # Check required fields mapped
        if not col_amount:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    column="amount",
                    message="Mandatory field 'amount' is not mapped to any dataset column.",
                    affected_rows=total_rows,
                )
            )
        if not col_timestamp:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    column="timestamp",
                    message="Mandatory field 'timestamp' is not mapped to any dataset column.",
                    affected_rows=total_rows,
                )
            )

        # Informational notes on missing optional entities
        if not col_cust:
            issues.append(
                ValidationIssue(
                    severity="INFO",
                    column="customer_id",
                    message="Customer ID is not mapped. Customer-level velocity and spending deviation signals will be unavailable.",
                    affected_rows=total_rows,
                )
            )
        if not col_dev:
            issues.append(
                ValidationIssue(
                    severity="INFO",
                    column="device_id",
                    message="Device ID is not mapped. Device novelty and hardware fingerprinting signals will be unavailable.",
                    affected_rows=total_rows,
                )
            )
        if not col_pi:
            issues.append(
                ValidationIssue(
                    severity="INFO",
                    column="payment_instrument_id",
                    message="Payment instrument / card token is not mapped. Card testing velocity bursts will be unavailable.",
                    affected_rows=total_rows,
                )
            )
        if not col_merch:
            issues.append(
                ValidationIssue(
                    severity="INFO",
                    column="merchant_id",
                    message="Merchant ID is not mapped. Terminal velocity and merchant risk intelligence will be unavailable.",
                    affected_rows=total_rows,
                )
            )

        # Row-level validation
        valid_count = 0
        invalid_count = 0
        parsed_timestamps: list[datetime] = []
        seen_txn_ids: set[str] = set()
        duplicate_id_count = 0
        invalid_amount_rows: list[int] = []
        negative_amount_rows: list[int] = []
        invalid_timestamp_rows: list[int] = []
        missing_cust_rows: list[int] = []

        for idx, r in enumerate(rows):
            is_row_valid = True

            # 1. Transaction ID Check
            raw_id = r.get(col_txn_id) if col_txn_id else None
            txn_id = str(raw_id).strip() if raw_id is not None and str(raw_id).strip() != "" else f"TXN_ROW_{idx+1:06d}"
            if txn_id in seen_txn_ids:
                duplicate_id_count += 1
            else:
                seen_txn_ids.add(txn_id)

            # 2. Amount Check
            if col_amount:
                amt_val, amt_err = parse_numeric_amount(r.get(col_amount))
                if amt_val is None:
                    is_row_valid = False
                    invalid_amount_rows.append(idx)
                elif amt_val <= 0.0:
                    negative_amount_rows.append(idx)
                    is_row_valid = False
            else:
                is_row_valid = False

            # 3. Timestamp Check
            if col_timestamp:
                dt = parse_standard_datetime(r.get(col_timestamp))
                if dt is None:
                    is_row_valid = False
                    invalid_timestamp_rows.append(idx)
                else:
                    parsed_timestamps.append(dt)
            else:
                is_row_valid = False

            # 4. Customer Check (Optional)
            if col_cust:
                raw_cust = r.get(col_cust)
                if raw_cust is None or str(raw_cust).strip() in ("", "null", "none", "nan"):
                    missing_cust_rows.append(idx)

            if is_row_valid:
                valid_count += 1
            else:
                invalid_count += 1

        # Check chronology
        is_chronological = True
        if len(parsed_timestamps) > 1:
            for i in range(len(parsed_timestamps) - 1):
                if parsed_timestamps[i] > parsed_timestamps[i + 1]:
                    is_chronological = False
                    break

        if not is_chronological:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    column="timestamp",
                    message="Transactions are not in strict chronological order. SentinelRisk will sort transactions chronologically to enforce point-in-time causality.",
                    affected_rows=total_rows,
                )
            )

        if duplicate_id_count > 0:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    column="transaction_id",
                    message=f"Found {duplicate_id_count} duplicate transaction identifiers. Unique row IDs will be generated where needed.",
                    affected_rows=duplicate_id_count,
                )
            )

        if invalid_amount_rows:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    column="amount",
                    message=f"{len(invalid_amount_rows)} rows contain unparsable or missing transaction amounts.",
                    affected_rows=len(invalid_amount_rows),
                    sample_row_indices=invalid_amount_rows[:5],
                )
            )

        if negative_amount_rows:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    column="amount",
                    message=f"{len(negative_amount_rows)} rows contain zero or negative amounts.",
                    affected_rows=len(negative_amount_rows),
                    sample_row_indices=negative_amount_rows[:5],
                )
            )

        if invalid_timestamp_rows:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    column="timestamp",
                    message=f"{len(invalid_timestamp_rows)} rows contain unparsable date/time strings.",
                    affected_rows=len(invalid_timestamp_rows),
                    sample_row_indices=invalid_timestamp_rows[:5],
                )
            )

        if missing_cust_rows and len(missing_cust_rows) < total_rows:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    column="customer_id",
                    message=f"{len(missing_cust_rows)} rows ({(len(missing_cust_rows)/total_rows)*100:.1f}%) have missing customer identifiers.",
                    affected_rows=len(missing_cust_rows),
                    sample_row_indices=missing_cust_rows[:5],
                )
            )

        ts_range = None
        if parsed_timestamps:
            min_ts = min(parsed_timestamps).strftime("%Y-%m-%d %H:%M:%S")
            max_ts = max(parsed_timestamps).strftime("%Y-%m-%d %H:%M:%S")
            ts_range = (min_ts, max_ts)

        is_valid_overall = (col_amount is not None) and (col_timestamp is not None) and (valid_count > 0)

        return ValidationSummary(
            is_valid=is_valid_overall,
            total_rows=total_rows,
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            has_timestamp=col_timestamp is not None and len(invalid_timestamp_rows) < total_rows,
            has_amount=col_amount is not None and len(invalid_amount_rows) < total_rows,
            has_customer_id=col_cust is not None,
            has_merchant_id=col_merch is not None,
            has_device_id=col_dev is not None,
            has_payment_instrument_id=col_pi is not None,
            has_ground_truth=col_fraud is not None,
            timestamp_range=ts_range,
            is_chronological=is_chronological,
            duplicate_transaction_ids=duplicate_id_count,
            issues=issues,
        )
