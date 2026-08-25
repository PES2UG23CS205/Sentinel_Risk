# SentinelRisk — Production Latency & Load Test Report

## 1. Environment Specifications
- **Operating System**: Windows 11
- **Python Runtime**: 3.12.7
- **Hardware/Processor**: AMD64 Family 23 Model 104 Stepping 1, AuthenticAMD
- **Latency Budget Target**: **< 100.0 ms**

---

## 2. Benchmark Summary (1,000 Sequential Authorizations)
- **Total Requests Evaluated**: 1000
- **Throughput**: **17929.05 requests / second**
- **Error Rate**: **0.0%**
- **p50 Latency**: **0.046 ms**
- **p95 Latency**: **0.081 ms**
- **p99 Latency**: **0.136 ms**
- **Mean Latency**: **0.053 ms**
- **Min / Max Latency**: 0.042 ms / 1.912 ms

---

## 3. Scalability Across Load Tiers

| Load Scenario | Requests | Throughput (RPS) | p50 Latency (ms) | p95 Latency (ms) | p99 Latency (ms) | Error Rate |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tier 1 (Smoke)** | 10 | 9332.71 | 0.049 | 0.34 | 0.511 | 0.0% |
| **Tier 2 (Medium)** | 100 | 19738.27 | 0.046 | 0.056 | 0.123 | 0.0% |
| **Tier 3 (Heavy)** | 1,000 | 17929.05 | 0.046 | 0.081 | 0.136 | 0.0% |

All tiers easily comply with the **< 100 ms** payment authorization SLA budget.
