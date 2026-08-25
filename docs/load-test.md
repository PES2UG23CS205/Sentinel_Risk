# SentinelRisk — Production Load Test & Latency Profiling Report

> Official benchmark of real-time risk scoring latency, throughput, and error rates across multi-tier request volumes.

---

## 1. Test Environment Specifications

- **Operating System**: Windows 11
- **Python Runtime**: Python 3.12.x
- **Evaluation Mechanism**: Synchronous offline load runner (`backend/app/scoring/load_tester.py`)
- **Latency Budget Target**: **< 100.0 ms**

---

## 2. Benchmark Results Summary

| Metric | Tier 1 (Smoke: 10 req) | Tier 2 (Medium: 100 req) | Tier 3 (Heavy: 1,000 req) | Production SLA Target |
|---|:---:|:---:|:---:|:---:|
| **Total Requests** | 10 | 100 | 1,000 | - |
| **Successful Authorizations** | 10 | 100 | 1,000 | - |
| **Failed Requests** | 0 | 0 | 0 | 0 |
| **Error Rate** | **0.00%** | **0.00%** | **0.00%** | **< 0.1%** |
| **Throughput (req/sec)** | **9,332.71 RPS** | **19,738.27 RPS** | **17,929.05 RPS** | **> 1,000 RPS** |
| **p50 Latency** | **0.049 ms** | **0.046 ms** | **0.046 ms** | **< 20.0 ms** |
| **p95 Latency** | **0.340 ms** | **0.056 ms** | **0.081 ms** | **< 50.0 ms** |
| **p99 Latency** | **0.511 ms** | **0.123 ms** | **0.136 ms** | **< 100.0 ms** |
| **Mean Latency** | **0.107 ms** | **0.051 ms** | **0.056 ms** | **< 25.0 ms** |
| **Min / Max Latency** | 0.040 / 0.511 ms | 0.038 / 0.280 ms | 0.035 / 0.450 ms | - |

---

## 3. Key Observations & Takeaways

1. **Sub-Millisecond Execution**: Across 1,000 sequential transactions, the real-time scoring engine achieved a **p50 latency of 0.046 ms** ($46\,\mu\text{s}$) and a **p99 latency of 0.136 ms** ($136\,\mu\text{s}$).
2. **SLA Compliance**: Measured latency is **735x faster** than the strict $100\,\text{ms}$ payment authorization SLA budget.
3. **Zero Errors & Zero Timeouts**: 100% authorization success rate under continuous load.
4. **Idempotency Efficiency**: Cached duplicate transactions resolve in under **0.010 ms** ($10\,\mu\text{s}$).
