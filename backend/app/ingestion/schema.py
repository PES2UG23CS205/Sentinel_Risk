"""
SentinelRisk — Transaction Ingestion Schemas & Mapping

Defines:
  - Canonical NormalizedTransaction schema
  - SchemaMapping with automatic alias inference
  - Validation issue records
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class NormalizedTransaction(BaseModel):
    """Canonical internal schema required by SentinelRisk risk pipeline."""
    transaction_id: str | int = Field(..., description="Unique transaction identifier")
    timestamp: str = Field(..., description="Transaction ISO or standard datetime string")
    amount: float = Field(..., description="Transaction amount (strictly positive)")
    currency: str = Field("INR", description="Transaction currency")
    customer_id: str | int = Field("UNKNOWN", description="Customer identifier")
    merchant_id: str | int = Field("UNKNOWN", description="Merchant / terminal identifier")
    device_id: str | int = Field("UNKNOWN", description="Device hardware token or IP")
    payment_instrument_id: str | int = Field("UNKNOWN", description="Card or payment token")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional raw attributes")
    ground_truth_fraud: Optional[int] = Field(None, description="Isolated evaluation ground truth (0=legit, 1=fraud)")
    ground_truth_scenario: Optional[int] = Field(None, description="External dataset fraud scenario code")


class SchemaMapping(BaseModel):
    """Maps arbitrary external CSV column names to canonical SentinelRisk fields."""
    transaction_id: str = "transaction_id"
    timestamp: str = "timestamp"
    amount: str = "amount"
    customer_id: Optional[str] = "customer_id"
    merchant_id: Optional[str] = "merchant_id"
    device_id: Optional[str] = "device_id"
    payment_instrument_id: Optional[str] = "payment_instrument_id"
    currency: Optional[str] = None


# Common column name aliases for automatic schema detection
FIELD_ALIASES: dict[str, list[str]] = {
    "transaction_id": ["transaction_id", "txn_id", "id", "tx_id", "trans_id", "payment_id", "reference_id"],
    "timestamp": ["timestamp", "time", "date", "created_at", "txn_time", "datetime", "created"],
    "amount": ["amount", "value", "amt", "price", "txn_amount", "total", "volume"],
    "customer_id": ["customer_id", "user_id", "cust_id", "buyer_id", "client_id", "account_id", "customer"],
    "merchant_id": ["merchant_id", "merch_id", "seller_id", "vendor_id", "store_id", "terminal_id", "merchant"],
    "device_id": ["device_id", "dev_id", "hardware_id", "fingerprint", "device_fingerprint", "ip_address", "device"],
    "payment_instrument_id": ["payment_instrument_id", "card_token", "pi_id", "instrument_id", "card_id", "token_id", "card_number", "payment_token"],
    "currency": ["currency", "curr", "currency_code"],
}


def infer_schema_mapping(columns: list[str]) -> SchemaMapping:
    """
    Automatically infer best column mappings by matching normalized header names against alias lists.
    """
    clean_cols = {col.lower().strip().replace(" ", "_").replace("-", "_"): col for col in columns}
    mapping_kwargs: dict[str, Any] = {}

    for canonical_field, aliases in FIELD_ALIASES.items():
        matched_col = None
        for alias in aliases:
            if alias in clean_cols:
                matched_col = clean_cols[alias]
                break
        if matched_col:
            mapping_kwargs[canonical_field] = matched_col
        elif canonical_field in ("transaction_id", "timestamp", "amount"):
            # Try partial substring match for mandatory fields
            for clean_name, orig_col in clean_cols.items():
                if any(alias in clean_name for alias in aliases):
                    matched_col = orig_col
                    break
            mapping_kwargs[canonical_field] = matched_col or canonical_field
        else:
            mapping_kwargs[canonical_field] = None

    return SchemaMapping(**mapping_kwargs)
