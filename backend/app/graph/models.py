"""
SentinelRisk — Entity Graph Data Models

Defines heterogeneous entity types, edge relationship types, node identifier formatters,
edge metadata structures, and detected ring candidate models.
"""

from enum import Enum
from dataclasses import dataclass, field


class EntityType(str, Enum):
    CUSTOMER = "customer"
    DEVICE = "device"
    PAYMENT_INSTRUMENT = "payment_instrument"
    MERCHANT = "merchant"


class EdgeType(str, Enum):
    CUSTOMER_USES_DEVICE = "CUSTOMER_USES_DEVICE"
    CUSTOMER_OWNS_PI = "CUSTOMER_OWNS_PI"
    CUSTOMER_TRANSACTS_MERCHANT = "CUSTOMER_TRANSACTS_MERCHANT"
    DEVICE_SEEN_MERCHANT = "DEVICE_SEEN_MERCHANT"


def make_node_id(entity_type: EntityType | str, entity_id: int | str) -> str:
    """Format collision-free heterogeneous graph node identifier (e.g., 'customer:102')."""
    etype_str = entity_type.value if isinstance(entity_type, EntityType) else str(entity_type)
    return f"{etype_str}:{entity_id}"


def parse_node_id(node_id: str) -> tuple[str, str]:
    """Parse collision-free node ID into (entity_type, entity_id)."""
    parts = node_id.split(":", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "unknown", node_id


@dataclass
class EdgeMetadata:
    """Temporal and transactional metadata stored on graph relationships."""
    edge_type: EdgeType
    first_seen_ts: float
    last_seen_ts: float
    txn_count: int = 1
    amount_sum: float = 0.0
    txn_timestamps: list[float] = field(default_factory=list)

    def update(self, ts: float, amount: float):
        """Update edge metadata with an additional historical transaction."""
        self.last_seen_ts = max(self.last_seen_ts, ts)
        self.txn_count += 1
        self.amount_sum += amount
        self.txn_timestamps.append(ts)


@dataclass
class RingCandidate:
    """Detected coordinated abuse ring candidate subgraph."""
    candidate_id: str
    customers: set[str]
    devices: set[str]
    payment_instruments: set[str]
    merchants: set[str]
    total_txns: int
    timespan_hours: float
    ring_score: float
    signals_triggered: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
