"""
SentinelRisk — Heterogeneous Entity Graph

Manages the in-memory entity graph tracking relationships across:
  - Customer (customer:ID)
  - Device (device:ID)
  - Payment Instrument (payment_instrument:ID)
  - Merchant (merchant:ID)

Uses indexed adjacency sets and Disjoint Set Union (DSU) for O(1) point-in-time metrics,
with NetworkX for global structural statistics and ego-network analysis.
"""

from collections import defaultdict
import networkx as nx
from backend.app.graph.models import (
    EntityType,
    EdgeType,
    EdgeMetadata,
    make_node_id,
    parse_node_id,
)


class DisjointSetUnion:
    """High-performance Disjoint Set Union (Union-Find) with path compression."""

    def __init__(self):
        self.parent = {}
        self.size = {}

    def find(self, i: str) -> str:
        if i not in self.parent:
            self.parent[i] = i
            self.size[i] = 1
            return i
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: str, j: str):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.size[root_i] < self.size[root_j]:
                root_i, root_j = root_j, root_i
            self.parent[root_j] = root_i
            self.size[root_i] += self.size[root_j]

    def get_component_size(self, i: str) -> int:
        root = self.find(i)
        return self.size.get(root, 1)


class EntityGraph:
    """Heterogeneous entity graph manager with NetworkX and indexed lookups."""

    def __init__(self):
        self.g = nx.Graph()
        self.dsu = DisjointSetUnion()

        # Direct indexed sets for ultra-fast point-in-time queries
        self.device_to_customers = defaultdict(set)
        self.device_to_merchants = defaultdict(set)
        self.pi_to_customers = defaultdict(set)
        self.pi_to_merchants = defaultdict(set)
        self.customer_to_devices = defaultdict(set)
        self.customer_to_pis = defaultdict(set)
        self.customer_to_merchants = defaultdict(set)

    def add_transaction_edges(
        self,
        customer_id: int | str,
        device_id: int | str,
        payment_instrument_id: int | str,
        merchant_id: int | str,
        timestamp_sec: float,
        amount: float,
    ):
        """
        Record historical transaction evidence into the entity graph.
        """
        c_str = str(customer_id)
        d_str = str(device_id)
        pi_str = str(payment_instrument_id)
        m_str = str(merchant_id)

        c_node = make_node_id(EntityType.CUSTOMER, c_str)
        d_node = make_node_id(EntityType.DEVICE, d_str)
        pi_node = make_node_id(EntityType.PAYMENT_INSTRUMENT, pi_str)
        m_node = make_node_id(EntityType.MERCHANT, m_str)

        # Update fast index mappings
        self.device_to_customers[d_str].add(c_str)
        self.device_to_merchants[d_str].add(m_str)
        self.pi_to_customers[pi_str].add(c_str)
        self.pi_to_merchants[pi_str].add(m_str)
        self.customer_to_devices[c_str].add(d_str)
        self.customer_to_pis[c_str].add(pi_str)
        self.customer_to_merchants[c_str].add(m_str)

        # Update DSU connected components
        self.dsu.union(c_node, d_node)
        self.dsu.union(c_node, pi_node)
        self.dsu.union(c_node, m_node)

        # Update NetworkX graph
        if not self.g.has_node(c_node):
            self.g.add_node(c_node, entity_type=EntityType.CUSTOMER.value, raw_id=c_str)
        if not self.g.has_node(d_node):
            self.g.add_node(d_node, entity_type=EntityType.DEVICE.value, raw_id=d_str)
        if not self.g.has_node(pi_node):
            self.g.add_node(pi_node, entity_type=EntityType.PAYMENT_INSTRUMENT.value, raw_id=pi_str)
        if not self.g.has_node(m_node):
            self.g.add_node(m_node, entity_type=EntityType.MERCHANT.value, raw_id=m_str)

        self._add_or_update_edge(c_node, d_node, EdgeType.CUSTOMER_USES_DEVICE, timestamp_sec, amount)
        self._add_or_update_edge(c_node, pi_node, EdgeType.CUSTOMER_OWNS_PI, timestamp_sec, amount)
        self._add_or_update_edge(c_node, m_node, EdgeType.CUSTOMER_TRANSACTS_MERCHANT, timestamp_sec, amount)
        self._add_or_update_edge(d_node, m_node, EdgeType.DEVICE_SEEN_MERCHANT, timestamp_sec, amount)

    def _add_or_update_edge(
        self,
        u: str,
        v: str,
        edge_type: EdgeType,
        timestamp_sec: float,
        amount: float,
    ):
        if self.g.has_edge(u, v):
            meta: EdgeMetadata = self.g[u][v]["metadata"]
            meta.update(timestamp_sec, amount)
        else:
            meta = EdgeMetadata(
                edge_type=edge_type,
                first_seen_ts=timestamp_sec,
                last_seen_ts=timestamp_sec,
                txn_count=1,
                amount_sum=amount,
                txn_timestamps=[timestamp_sec],
            )
            self.g.add_edge(u, v, metadata=meta, edge_type=edge_type.value)

    # --- Ultra-Fast Point-in-Time Graph Metric Queries ---

    def get_device_customer_count(self, device_id: int | str) -> int:
        return len(self.device_to_customers.get(str(device_id), set()))

    def get_device_merchant_count(self, device_id: int | str) -> int:
        return len(self.device_to_merchants.get(str(device_id), set()))

    def get_pi_customer_count(self, pi_id: int | str) -> int:
        return len(self.pi_to_customers.get(str(pi_id), set()))

    def get_pi_merchant_count(self, pi_id: int | str) -> int:
        return len(self.pi_to_merchants.get(str(pi_id), set()))

    def get_customer_shared_device_count(self, customer_id: int | str) -> int:
        devs = self.customer_to_devices.get(str(customer_id), set())
        return sum(1 for d in devs if len(self.device_to_customers.get(d, set())) > 1)

    def get_customer_shared_pi_count(self, customer_id: int | str) -> int:
        pis = self.customer_to_pis.get(str(customer_id), set())
        return sum(1 for p in pis if len(self.pi_to_customers.get(p, set())) > 1)

    def get_entity_connected_component_size(self, entity_type: EntityType | str, entity_id: int | str) -> int:
        node = make_node_id(entity_type, str(entity_id))
        return self.dsu.get_component_size(node)

    def get_ego_subgraph(self, entity_type: EntityType | str, entity_id: int | str, radius: int = 2) -> nx.Graph:
        node = make_node_id(entity_type, str(entity_id))
        if not self.g.has_node(node):
            sub = nx.Graph()
            sub.add_node(node, entity_type=str(entity_type), raw_id=str(entity_id))
            return sub
        return nx.ego_graph(self.g, node, radius=radius)

    def get_graph_statistics(self) -> dict:
        n_nodes = self.g.number_of_nodes()
        n_edges = self.g.number_of_edges()

        cust_count = sum(1 for _, d in self.g.nodes(data=True) if d.get("entity_type") == EntityType.CUSTOMER.value)
        dev_count = sum(1 for _, d in self.g.nodes(data=True) if d.get("entity_type") == EntityType.DEVICE.value)
        pi_count = sum(1 for _, d in self.g.nodes(data=True) if d.get("entity_type") == EntityType.PAYMENT_INSTRUMENT.value)
        merch_count = sum(1 for _, d in self.g.nodes(data=True) if d.get("entity_type") == EntityType.MERCHANT.value)

        edge_types_count = {}
        for _, _, d in self.g.edges(data=True):
            etype = d.get("edge_type", "unknown")
            edge_types_count[etype] = edge_types_count.get(etype, 0) + 1

        components = list(nx.connected_components(self.g)) if n_nodes > 0 else []
        n_components = len(components)
        max_comp_size = max([len(c) for c in components]) if components else 0
        degrees = [d for _, d in self.g.degree()] if n_nodes > 0 else [0]
        avg_degree = sum(degrees) / max(1, len(degrees))
        max_degree = max(degrees) if degrees else 0

        return {
            "total_nodes": n_nodes,
            "total_edges": n_edges,
            "nodes_by_type": {
                "customers": cust_count,
                "devices": dev_count,
                "payment_instruments": pi_count,
                "merchants": merch_count,
            },
            "edges_by_type": edge_types_count,
            "connected_components_count": n_components,
            "largest_component_size": max_comp_size,
            "average_degree": round(avg_degree, 2),
            "max_degree": max_degree,
        }
