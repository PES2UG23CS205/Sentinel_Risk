"""
SentinelRisk — Ingestion Dataset Validator & CSV Parser

Handles parsing, column mapping, row-level data type verification,
timestamp standardization, duplicate detection, and invalid row reporting.
"""

import io
import csv
import json
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

from backend.app.ingestion.schema import NormalizedTransaction, SchemaMapping, infer_schema_mapping


class InvalidRowRecord(BaseModel):
    row_index: int
    reason: str
    raw_data: dict[str, Any]


class ValidationReport(BaseModel):
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    valid_rows: list[NormalizedTransaction]
    invalid_rows: list[InvalidRowRecord]
    missing_fields_summary: dict[str, int]
    detected_mapping: SchemaMapping
    preview_rows: list[dict[str, Any]]


def parse_flexible_timestamp(val: Any) -> Optional[str]:
    """Parse various timestamp string representations into standard ISO format."""
    if not val:
        return None
    val_str = str(val).strip()
    
    # Common formats
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
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    
    # Unix timestamp detection
    try:
        ts_float = float(val_str)
        # Seconds vs milliseconds
        if ts_float > 1e11:
            ts_float /= 1000.0
        dt = datetime.fromtimestamp(ts_float)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        pass

    return None


class DatasetValidator:
    """Validates and normalizes tabular transaction datasets (CSV / JSON / JSONL)."""

    @staticmethod
    def parse_raw_records(content: str, file_type: str = "csv") -> tuple[list[str], list[dict[str, Any]]]:
        """Parse raw content text into headers and row dictionaries."""
        content = content.strip()
        if not content:
            return [], []

        if file_type == "json" or content.startswith("["):
            data = json.loads(content)
            if not isinstance(data, list) or not data:
                return [], []
            headers = list(data[0].keys())
            return headers, data

        if file_type == "jsonl" or (content.startswith("{") and "\n" in content):
            rows = []
            for line in content.splitlines():
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
            headers = list(rows[0].keys()) if rows else []
            return headers, rows

        # Default: CSV parser
        f = io.StringIO(content)
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
        return list(headers), rows

    @classmethod
    def validate_and_normalize(
        cls,
        raw_rows: list[dict[str, Any]],
        mapping: Optional[SchemaMapping] = None,
        headers: Optional[list[str]] = None,
    ) -> ValidationReport:
        """
        Validate records against schema mapping and return structured report.
        """
        if not headers and raw_rows:
            headers = list(raw_rows[0].keys())
        headers = headers or []

        if mapping is None:
            mapping = infer_schema_mapping(headers)

        valid_rows: list[NormalizedTransaction] = []
        invalid_rows: list[InvalidRowRecord] = []
        missing_fields: dict[str, int] = {
            "customer_id": 0,
            "merchant_id": 0,
            "device_id": 0,
            "payment_instrument_id": 0,
        }
        seen_txn_ids: set[str] = set()

        for idx, row in enumerate(raw_rows, start=1):
            # 1. Transaction ID
            txn_id_key = mapping.transaction_id
            raw_txn_id = row.get(txn_id_key) if txn_id_key else None
            if not raw_txn_id or str(raw_txn_id).strip() == "":
                invalid_rows.append(InvalidRowRecord(row_index=idx, reason="Missing transaction ID", raw_data=row))
                continue
            txn_id_str = str(raw_txn_id).strip()
            if txn_id_str in seen_txn_ids:
                invalid_rows.append(InvalidRowRecord(row_index=idx, reason=f"Duplicate transaction ID '{txn_id_str}'", raw_data=row))
                continue
            seen_txn_ids.add(txn_id_str)

            # 2. Amount
            amount_key = mapping.amount
            raw_amt = row.get(amount_key) if amount_key else None
            try:
                if raw_amt is None or str(raw_amt).strip() == "":
                    raise ValueError("Empty amount")
                amt = float(str(raw_amt).replace(",", "").replace("$", "").replace("₹", "").strip())
                if amt <= 0.0:
                    invalid_rows.append(InvalidRowRecord(row_index=idx, reason=f"Non-positive amount: {amt}", raw_data=row))
                    continue
            except ValueError:
                invalid_rows.append(InvalidRowRecord(row_index=idx, reason=f"Invalid numeric amount '{raw_amt}'", raw_data=row))
                continue

            # 3. Timestamp
            time_key = mapping.timestamp
            raw_time = row.get(time_key) if time_key else None
            parsed_time = parse_flexible_timestamp(raw_time)
            if not parsed_time:
                invalid_rows.append(InvalidRowRecord(row_index=idx, reason=f"Unparsable timestamp format '{raw_time}'", raw_data=row))
                continue

            # 4. Optional entity fields
            cust_val = row.get(mapping.customer_id) if mapping.customer_id else None
            if not cust_val:
                missing_fields["customer_id"] += 1
                cust_val = "UNKNOWN_CUST"

            merch_val = row.get(mapping.merchant_id) if mapping.merchant_id else None
            if not merch_val:
                missing_fields["merchant_id"] += 1
                merch_val = "UNKNOWN_MERCH"

            dev_val = row.get(mapping.device_id) if mapping.device_id else None
            if not dev_val:
                missing_fields["device_id"] += 1
                dev_val = "UNKNOWN_DEV"

            pi_val = row.get(mapping.payment_instrument_id) if mapping.payment_instrument_id else None
            if not pi_val:
                missing_fields["payment_instrument_id"] += 1
                pi_val = "UNKNOWN_PI"

            curr_val = row.get(mapping.currency) if mapping.currency else "INR"

            norm_txn = NormalizedTransaction(
                transaction_id=txn_id_str,
                timestamp=parsed_time,
                amount=round(amt, 2),
                currency=str(curr_val or "INR").strip(),
                customer_id=str(cust_val).strip(),
                merchant_id=str(merch_val).strip(),
                device_id=str(dev_val).strip(),
                payment_instrument_id=str(pi_val).strip(),
                metadata={k: v for k, v in row.items() if k not in (txn_id_key, time_key, amount_key)},
            )
            valid_rows.append(norm_txn)

        preview = [r.model_dump() for r in valid_rows[:10]]

        return ValidationReport(
            total_rows=len(raw_rows),
            valid_rows_count=len(valid_rows),
            invalid_rows_count=len(invalid_rows),
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            missing_fields_summary=missing_fields,
            detected_mapping=mapping,
            preview_rows=preview,
        )
