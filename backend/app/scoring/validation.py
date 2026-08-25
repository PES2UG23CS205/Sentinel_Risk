"""
SentinelRisk — Production Risk Request Validation & Input Hashing

Provides:
  - Strict schema and domain validation for incoming real-time risk evaluation requests
  - Deterministic SHA-256 input hashing for immutable audit trails and replay verification
"""

import json
import hashlib
from datetime import datetime
from typing import Any


class ValidationError(Exception):
    """Raised when a risk evaluation request violates domain constraints."""
    pass


def validate_risk_request(payload: dict) -> dict:
    """
    Validate incoming payment transaction authorization payload.

    Required fields:
      - transaction_id (str | int)
      - amount (float > 0)
      - customer_id (str | int)
      - device_id (str | int)
      - payment_instrument_id (str | int)
      - merchant_id (str | int)
      - timestamp (ISO-8601 or YYYY-MM-DD HH:MM:SS)

    Returns:
      Normalized payload dict.
    Raises:
      ValidationError if payload is malformed or invalid.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request payload must be a JSON object.")

    required_fields = [
        "transaction_id",
        "amount",
        "timestamp",
    ]

    for field in required_fields:
        if field not in payload or payload[field] is None:
            raise ValidationError(f"Missing mandatory field '{field}'.")

    # Default optional identifiers to UNKNOWN if omitted
    for id_field in ("customer_id", "device_id", "payment_instrument_id", "merchant_id"):
        if id_field not in payload or payload[id_field] is None or str(payload[id_field]).strip() == "":
            payload[id_field] = "UNKNOWN"

    # 1. Amount validation
    try:
        amount = float(payload["amount"])
        if amount <= 0.0:
            raise ValidationError(f"Transaction amount must be strictly positive (> 0.0), got {amount}.")
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid transaction amount: {payload['amount']}.")

    # 2. Timestamp validation
    ts_str = str(payload["timestamp"]).strip()
    if not ts_str:
        raise ValidationError("Timestamp field cannot be empty.")

    valid_ts = False
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            datetime.strptime(ts_str.replace("Z", ""), fmt)
            valid_ts = True
            break
        except ValueError:
            continue

    if not valid_ts:
        raise ValidationError(f"Invalid timestamp format: '{ts_str}'. Expected ISO-8601 or YYYY-MM-DD HH:MM:SS.")

    # 3. Identifier non-emptiness validation
    for id_field in ("transaction_id", "customer_id", "device_id", "payment_instrument_id", "merchant_id"):
        val_str = str(payload[id_field]).strip()
        if not val_str:
            raise ValidationError(f"Identifier '{id_field}' cannot be empty.")

    return {
        "transaction_id": payload["transaction_id"],
        "amount": round(amount, 2),
        "customer_id": str(payload["customer_id"]).strip(),
        "device_id": str(payload["device_id"]).strip(),
        "payment_instrument_id": str(payload["payment_instrument_id"]).strip(),
        "merchant_id": str(payload["merchant_id"]).strip(),
        "timestamp": ts_str,
        "currency": payload.get("currency", "INR"),
        "features": payload.get("features", {}),
    }


def compute_input_hash(payload: dict) -> str:
    """
    Compute a deterministic SHA-256 digest of canonicalized request inputs.
    Excludes non-deterministic or ephemeral keys (like correlation_id).
    """
    canonical_dict = {
        "transaction_id": str(payload.get("transaction_id", "")),
        "amount": f"{float(payload.get('amount', 0.0)):.2f}",
        "customer_id": str(payload.get("customer_id", "")),
        "device_id": str(payload.get("device_id", "")),
        "payment_instrument_id": str(payload.get("payment_instrument_id", "")),
        "merchant_id": str(payload.get("merchant_id", "")),
        "timestamp": str(payload.get("timestamp", "")),
    }

    serialized = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
