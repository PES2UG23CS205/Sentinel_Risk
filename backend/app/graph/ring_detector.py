"""
SentinelRisk — Coordinated Abuse Ring Detector & Scorer

Discovers multi-entity infrastructure-sharing clusters, distinguishes legitimate
household sharing from syndicated abuse, computes deterministic ring scores,
and provides structured explainability.
"""

from backend.app.graph.models import (
    EntityType,
    RingCandidate,
    make_node_id,
    parse_node_id,
)
from backend.app.graph.config import GraphConfig
from backend.app.graph.entity_graph import EntityGraph


class RingDetector:
    """Detects and scores coordinated abuse rings from local entity graph topology."""

    def __init__(self, config: GraphConfig | None = None):
        self.config = config or GraphConfig()

    def evaluate_transaction_cluster(
        self,
        graph: EntityGraph,
        customer_id: int | str,
        device_id: int | str,
        payment_instrument_id: int | str,
        merchant_id: int | str,
    ) -> dict:
        """
        Evaluate the graph neighborhood around a transaction's entities.
        """
        c_str = str(customer_id)
        d_str = str(device_id)
        pi_str = str(payment_instrument_id)

        d_cust_set = graph.device_to_customers.get(d_str, set())
        pi_cust_set = graph.pi_to_customers.get(pi_str, set())

        d_cust_count = len(d_cust_set)
        pi_cust_count = len(pi_cust_set)
        c_shared_dev = graph.get_customer_shared_device_count(c_str)
        c_shared_pi = graph.get_customer_shared_pi_count(c_str)
        comp_size = graph.get_entity_connected_component_size(EntityType.CUSTOMER, c_str)

        # Fast-Path: If device and payment instrument are not shared with any other customer,
        # no coordinated ring infrastructure exists.
        if d_cust_count <= 1 and pi_cust_count <= 1 and c_shared_dev == 0 and c_shared_pi == 0:
            return {
                "ring_score": 0.0,
                "is_ring_candidate": False,
                "linked_customers_count": 1,
                "shared_devices_count": 0,
                "shared_pis_count": 0,
                "device_customer_count": d_cust_count,
                "pi_customer_count": pi_cust_count,
                "customer_shared_device_count": c_shared_dev,
                "customer_shared_payment_count": c_shared_pi,
                "component_size": comp_size,
                "signals_triggered": [],
                "explanations": [],
            }

        # 1. Discover all connected customer accounts sharing the device or PI
        linked_customers = set(d_cust_set) | set(pi_cust_set) | {c_str}
        n_linked_cust = len(linked_customers)

        # 2. Extract shared devices and PIs within this customer cluster
        shared_devices = set()
        shared_pis = set()

        for cust in linked_customers:
            for dev in graph.customer_to_devices.get(cust, set()):
                if len(graph.device_to_customers.get(dev, set())) > 1:
                    shared_devices.add(dev)
            for pi in graph.customer_to_pis.get(cust, set()):
                if len(graph.pi_to_customers.get(pi, set())) > 1:
                    shared_pis.add(pi)

        # 3. Legitimate Shared Infrastructure Accommodation
        # A device shared by <= 2 customers without multi-customer card sharing is considered normal household sharing
        is_legitimate_sharing = (
            n_linked_cust <= self.config.legitimate_device_sharing_cap and
            len(shared_pis) == 0 and
            pi_cust_count <= 1
        )

        # 4. Ring Scoring Calculation
        signals_triggered = []
        explanations = []
        score = 0.0

        if not is_legitimate_sharing and (n_linked_cust >= 2 or d_cust_count >= 2 or pi_cust_count >= 2):
            # Signal 1: Shared Device Density
            if d_cust_count >= 2:
                dev_score = min(1.0, (d_cust_count - 1) / 3.0) * self.config.weight_shared_device
                score += dev_score
                signals_triggered.append("MULTI_CUSTOMER_DEVICE_SHARING")
                explanations.append(
                    f"Device is shared across {d_cust_count} distinct customer accounts."
                )

            # Signal 2: Shared Payment Instrument Density
            if pi_cust_count >= 2:
                pi_score = min(1.0, (pi_cust_count - 1) / 2.0) * self.config.weight_shared_pi
                score += pi_score
                signals_triggered.append("SHARED_PAYMENT_INSTRUMENT_ACROSS_ACCOUNTS")
                explanations.append(
                    f"Payment instrument is shared across {pi_cust_count} distinct customer accounts."
                )

            # Signal 3: Customer Scale (Ring breadth)
            if n_linked_cust >= self.config.min_ring_customers:
                scale_score = min(1.0, n_linked_cust / 5.0) * self.config.weight_customer_scale
                score += scale_score
                signals_triggered.append("HIGH_CUSTOMER_CLUSTER_SIZE")
                explanations.append(
                    f"Connected entity cluster encompasses {n_linked_cust} linked customer accounts."
                )

            # Signal 4: Infrastructure Multi-Sharing (both device and card shared)
            if len(shared_devices) >= 1 and len(shared_pis) >= 1:
                score += self.config.weight_temporal_burst
                signals_triggered.append("MULTI_INFRASTRUCTURE_SHARING")
                explanations.append(
                    f"Syndicate pattern: Cluster shares {len(shared_devices)} devices and {len(shared_pis)} payment instruments."
                )

        score = round(min(1.0, max(0.0, score)), 4)
        is_ring_candidate = (
            score >= self.config.ring_score_threshold and
            n_linked_cust >= self.config.min_ring_customers
        )

        return {
            "ring_score": score,
            "is_ring_candidate": is_ring_candidate,
            "linked_customers_count": n_linked_cust,
            "shared_devices_count": len(shared_devices),
            "shared_pis_count": len(shared_pis),
            "device_customer_count": d_cust_count,
            "pi_customer_count": pi_cust_count,
            "customer_shared_device_count": c_shared_dev,
            "customer_shared_payment_count": c_shared_pi,
            "component_size": comp_size,
            "signals_triggered": signals_triggered,
            "explanations": explanations,
        }
