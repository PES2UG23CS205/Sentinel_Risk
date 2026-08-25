"""
SentinelRisk — Idempotency Management

Ensures safe duplicate payment authorization handling:
  - Exact duplicates return previously evaluated decision with idempotency flag
  - Conflicting payload resubmissions with identical transaction ID are rejected with conflict error
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is resubmitted with a conflicting payload."""
    pass


@dataclass
class IdempotencyRecord:
    key: str
    input_hash: str
    response: dict
    timestamp: str


class IdempotencyManager:
    """In-memory thread-safe idempotency cache."""

    def __init__(self):
        self._cache: dict[str, IdempotencyRecord] = {}

    def get(self, key: str) -> IdempotencyRecord | None:
        """Lookup an existing idempotency record."""
        return self._cache.get(str(key))

    def record_decision(self, key: str, input_hash: str, response: dict) -> None:
        """Store evaluated decision in idempotency cache."""
        self._cache[str(key)] = IdempotencyRecord(
            key=str(key),
            input_hash=input_hash,
            response=response,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def check_idempotency(self, key: str, input_hash: str) -> dict | None:
        """
        Check if transaction was already processed.

        Returns:
            - Cached response dict if exact duplicate
            - None if key has not been seen yet
        Raises:
            - IdempotencyConflictError if key seen with different input_hash
        """
        k_str = str(key)
        if k_str in self._cache:
            rec = self._cache[k_str]
            if rec.input_hash == input_hash:
                cached_copy = dict(rec.response)
                cached_copy["idempotency_cached"] = True
                return cached_copy
            else:
                raise IdempotencyConflictError(
                    f"Idempotency conflict for transaction '{key}'. "
                    f"Previous input_hash ({rec.input_hash[:8]}...) differs from current ({input_hash[:8]}...)."
                )
        return None

    def clear(self) -> None:
        """Reset idempotency cache."""
        self._cache.clear()
