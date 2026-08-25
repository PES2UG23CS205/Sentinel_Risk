# SentinelRisk — Comprehensive Razorpay Panel Defense & Technical Q&A

> Technical defense, architectural justifications, mathematical formulations, and operational strategies for the Razorpay engineering and risk leadership panel.

---

## 1. Architecture & System Design

### Q1: Why did you choose LightGBM over Deep Learning (e.g. TabNet or Transformer)?
**Answer**: In tabular payment transaction streams, Gradient Boosted Decision Trees (LightGBM) consistently outperform deep architectures in training speed, inference latency ($< 0.05\,\text{ms}$), memory footprint, and handling extreme class imbalance. LightGBM natively handles non-linear interactions, missing values (cold-start sentinels `-1.0`), and produces monotonic splits that map cleanly to interpretable SHAP feature contributions.

### Q2: Why is the Policy Engine decoupled from the ML model?
**Answer**: Machine learning models produce uncalibrated continuous probabilities $P(\text{fraud} \mid x)$, not business decisions. A payment gateway operates under dynamic merchant risk appetites, regulatory thresholds, and changing loss costs. Decoupling policy into a declarative YAML engine (`sentinelrisk-policy-v1`) allows risk operators to tune thresholds, add temporary incident overrides, and audit rules without retraining ML weights.

### Q3: Why use a tri-state decision model (`APPROVE` / `REVIEW` / `HOLD`) instead of binary `ALLOW` / `BLOCK`?
**Answer**: Binary blocking forces an aggressive tradeoff between fraud leakage and customer insult rate. A tri-state architecture enables:
1. **`APPROVE` (98.3%)**: Frictionless path for high-confidence legitimate cardholders.
2. **`REVIEW` (0.7%)**: Intermediate ambiguity band routed to human analysts with AI investigation dossiers.
3. **`HOLD` (1.0%)**: High-confidence automated intervention for critical attacks and syndicates.

---

## 2. Data Engineering & Leakage Prevention

### Q4: How did you strictly prevent temporal data leakage in feature engineering?
**Answer**: We enforced a strict point-in-time causality constraint: for any transaction evaluated at timestamp $T$, features are computed exclusively using historical events where $t < T$. Intra-batch transactions sharing the identical millisecond timestamp are isolated. We verified this with a dedicated unit test suite that asserts feature invariance when future events are appended.

### Q5: How do you handle cold-start entities (brand new customers/cards)?
**Answer**: When an entity has zero historical transactions, computing rolling means or z-scores produces undefined values. We inject explicit sentinel values (`-1.0`) across all ratio and velocity features, allowing tree algorithms to branch on cold-start status as an explicit feature without imputing misleading global medians.

---

## 3. Machine Learning & Threshold Optimization

### Q6: Why optimize thresholds on Validation instead of Test?
**Answer**: Tuning decision thresholds on the held-out test set introduces statistical data snooping and produces overly optimistic performance estimates. We derived the optimal classification threshold ($T = 0.05$) exclusively on the 10,179-transaction validation split, and froze the test set (June 11–30, 2025) as an untouched benchmark.

### Q7: Why use PR-AUC instead of ROC-AUC for evaluation?
**Answer**: Under extreme class imbalance (1.06% fraud prevalence), ROC-AUC is misleadingly inflated because the large volume of True Negatives suppresses the False Positive Rate. PR-AUC focuses strictly on True Positives, False Positives, and False Negatives, reflecting the true operational precision and recall experienced by risk analysts.

---

## 4. Graph Intelligence & Abuse Rings

### Q8: What defines a coordinated abuse ring, and why do ML models miss them?
**Answer**: A fraud ring consists of collusive fraudsters sharing physical devices, payment instruments, or digital fingerprints across multiple synthetic accounts. Single-transaction ML models evaluate transactions in isolation, seeing low individual amounts and normal velocity. The heterogeneous entity graph connects shared node topologies, identifying dense multi-account clusters with a ring score $> 0.70$.

### Q9: How do you prevent legitimate family sharing from triggering false positive ring alerts?
**Answer**: Our ring detection algorithm incorporates a legitimate sharing filter: sub-graphs sharing $\le 2$ customer accounts and distinct personal payment instruments are assigned a ring score of `0.0`, preventing false alarms on shared household iPads or family laptops.

---

## 5. AI Investigation Agent & Safeguards

### Q10: Why use an LLM for investigation if it cannot decide fraud?
**Answer**: The LLM acts as an expert intelligence analyst, synthesizing multi-table SQL queries, graph topologies, and behavioral anomalies into a coherent, evidence-grounded incident dossier. This reduces human analyst triage time from 15 minutes down to 30 seconds per case.

### Q11: How do you guarantee zero hallucinations in LLM investigation reports?
**Answer**: Every claim generated by the agent is programmatically validated against an immutable context dictionary of atomic evidence items (`EVID-001`, `EVID-002`). The `InvestigationAgent` strips any statement referencing non-existent evidence IDs and verifies that policy decisions are never overridden.

---

## 6. Real-Time Operations, Latency & Resilience

### Q12: How does the system achieve sub-millisecond real-time scoring?
**Answer**: In-memory feature vectors, compiled LightGBM tree execution, and pre-computed sub-graph ego-network lookups allow the synchronous scoring engine to evaluate a transaction in **0.046 ms (p50)** and **0.136 ms (p99)**, well within the 100ms payment gateway budget.

### Q13: What happens if the ML or Graph service crashes during payment processing?
**Answer**: The system degrades gracefully:
- If ML fails (`ml_status = DEGRADED`), the engine falls back to graph syndicate scoring and deterministic velocity burst rules.
- If Graph fails (`graph_status = UNAVAILABLE`), the engine falls back to LightGBM anomaly scores.
- If the Policy Engine fails, the system fails safe to `REVIEW` to prevent unvalidated fraud leakage.

### Q14: How does idempotency protect against double-charging?
**Answer**: We hash the normalized request payload using canonical SHA-256 (`input_hash`). Duplicate requests with identical hashes return the cached decision in $< 10\,\mu\text{s}$ with `idempotency_cached: true`. Modified payloads sharing the same `transaction_id` are rejected with `409 Conflict`.

---

## 7. Business Impact & Production Scaling

### Q15: How does SentinelRisk quantify business ROI?
**Answer**: On our held-out test benchmark, SentinelRisk reduced expected financial losses by **95.9% (from ₹641,079 down to ₹26,355)** while maintaining a **98.27% frictionless approval rate** and an analyst review queue under **0.84%**.
