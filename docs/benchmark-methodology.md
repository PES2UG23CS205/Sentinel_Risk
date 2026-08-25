# SentinelRisk — Benchmark Methodology & Measurement Standards

> Authoritative methodology, evaluation windows, metric calculations, and honest boundaries between local prototype profiling and enterprise cloud production.

---

## 1. Evaluation Windows & Dataset Segregation

SentinelRisk enforces strict temporal segregation across the 6-month simulated payments world (January 1 to June 30, 2025):

| Split / Window | Date Range | Transaction Count | Purpose & Constraint |
|---|:---:|:---:|---|
| **Training Split** | Jan 1 – May 9, 2025 | 47,500 (70.0%) | Feature learning & LightGBM model training (`scale_pos_weight = 86.16`) |
| **Validation Split** | May 10 – June 10, 2025 | 10,179 (15.0%) | Threshold optimization ($T = 0.05$ for ML, $T = 3.0$ for Rules) |
| **Held-Out Test Split** | June 11 – June 30, 2025 | 10,179 (15.0%) | **Strictly frozen common benchmark** untouched during model/policy tuning |
| **Full Ecosystem** | Jan 1 – June 30, 2025 | 67,858 (100.0%) | Full-dataset replay, graph link analysis, and multi-archetype recovery |

> [!IMPORTANT]
> **No Retuning on Held-Out Test**: The Stage 5 test set results remain frozen. Later stages (Graph in Stage 6, Policy in Stage 7) did not retune thresholds against the test set.

---

## 2. In-Process Latency Profiling vs. Cloud Production

### What Was Measured (Local In-Process Benchmark):
- Measured using Python's high-resolution `time.perf_counter()`.
- Evaluates CPU tree traversal, in-memory graph ring score lookups, rule evaluation, and policy precedence in a single process.
- **Results**: **p50 = 0.046 ms** ($46\,\mu\text{s}$), **p99 = 0.136 ms** ($136\,\mu\text{s}$), **Throughput = ~17,900 RPS**.

### What Is Excluded from Local Benchmarks:
1. **Network Transit & Gateway Ingress**: TCP handshake, TLS termination, API Gateway payload parsing ($10\,\text{ms}-20\,\text{ms}$).
2. **Distributed Online Feature Store RPCs**: Remote network calls to Redis / Feast cluster ($1\,\text{ms}-3\,\text{ms}$).
3. **External Distributed Graph Database Traversals**: Multi-hop Cypher queries across Neo4j/Neptune cluster ($5\,\text{ms}-15\,\text{ms}$).
4. **Inter-Service Network Serialization**: gRPC/JSON marshalling between microservice containers.

---

## 3. Financial Cost Model & Loss Calculations

We evaluate business impact using the established cost function:
$$\text{Expected Loss} = \sum_{\text{FN}} \text{Amount} + (\text{FP}_{\text{Review}} \times ₹50.00) + (\text{FP}_{\text{Hold}} \times ₹250.00)$$

- **False Positive Friction Cost**: ₹150.00 (Customer friction & support overhead).
- **Manual Review Cost**: ₹50.00 (Human analyst queue triage time).
- **False Hold Cost**: ₹250.00 (Severe user friction / potential customer churn).
- **Fraud Loss Multiplier**: 1.0 (100% of transaction amount lost on False Negative chargeback).
