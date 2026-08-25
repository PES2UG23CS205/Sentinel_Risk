# SentinelRisk — Cost-Sensitive Multi-Signal Policy Engine

> Deterministic risk decision layer integrating Supervised ML (LightGBM), Entity Graph Link Analysis, and High-Confidence Velocity Rules.

---

## 1. Executive Summary & Core Motivation

A machine learning model outputs a continuous probability:
> $P(\text{fraud} \mid \vec{x}) = 0.084$

An entity graph detector outputs a structural connectivity score:
> $\text{ring\_score} = 0.65$

A raw score is not an actionable business decision. A payment platform cannot ask a merchant or terminal to *"evaluate probability 0.084"*. The payment system must make a concrete, auditable, tri-state operational decision:
1. **`APPROVE`**: Low-risk transaction permitted immediately without friction.
2. **`REVIEW`**: Moderate risk routed to secondary triage / analyst investigation queue.
3. **`HOLD`**: High-confidence severe threat immediately intercepted and frozen.

The **Policy Engine (`backend/app/policy/engine.py`)** turns raw, disparate risk signals into transparent, deterministic, and auditable business decisions under explicit financial cost constraints.

---

## 2. Decision Architecture

```
                    ┌────────────────────────┐
                    │  Incoming Transaction  │
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ LightGBM ML   │       │ Entity Graph  │       │ Deterministic │
│ Probability   │       │ Ring Score    │       │ Rules         │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                                ▼
                ┌───────────────────────────────┐
                │  Policy Engine Precedence     │
                │  (sentinelrisk-policy-v1)     │
                └───────────────┬───────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
     │   APPROVE   │     │   REVIEW    │     │    HOLD     │
     │  (98.27%)   │     │   (0.68%)   │     │   (1.06%)   │
     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## 3. Policy Configuration & Versioning (`config/policy.yaml`)

Policy logic is decoupled from Python code and managed via external configuration files tagged with explicit versions:

```yaml
policy_version: "sentinelrisk-policy-v1"
description: "Multi-signal risk decision policy integrating LightGBM ML, Entity Graph intelligence, and deterministic rules."

# Machine Learning Thresholds (LightGBM)
ml_thresholds:
  review_threshold: 0.05    # Validation-optimized operating threshold
  hold_threshold: 0.50      # High-confidence hold threshold

# Entity Graph Thresholds (Stage 6)
graph_thresholds:
  ring_score_review: 0.50   # Moderate ring score triggering investigation
  ring_score_hold: 0.80     # Dense syndicate structure triggering immediate freeze
  min_ring_customers: 3

# Deterministic Rule Overrides
rule_conditions:
  severe_card_velocity_1h: 5  # Bot-driven card testing burst
  moderate_card_velocity_1h: 3
  severe_cust_amount_ratio: 6.0
  moderate_cust_amount_ratio: 4.0

# Cost Model (INR)
cost_model:
  false_positive_cost: 150.0  # Customer friction & support cost
  review_cost: 50.0          # Manual review triage cost
  fraud_loss_multiplier: 1.0  # 100% of transaction amount lost on FN
  hold_friction_cost: 250.0  # Friction cost per false hold
```

---

## 4. Decision Precedence Hierarchy & Conflict Resolution

When multiple risk signals disagree, the Policy Engine applies a strict, deterministic precedence hierarchy:

### Tier 1: HOLD Precedence (Immediate High-Confidence Interception)
- **Severe Velocity Override**: `pi_velocity_count_1h >= 5` (Catches distributed bot card testing).
- **Severe ML Confidence**: `ml_probability >= 0.50`.
- **Severe Graph Syndicate**: `graph_ring_score >= 0.80` and `graph_ring_candidate == 1`.
- **Compound ML + Graph Threat**: `ml_probability >= 0.20` AND `graph_ring_score >= 0.50` (Compound elevated risk across both domains).

### Tier 2: REVIEW Precedence (Suspicious Threat Requiring Investigation)
- **Elevated ML Risk**: `ml_probability >= 0.05`.
- **Elevated Graph Ring Score**: `graph_ring_score >= 0.50` and `graph_ring_candidate == 1`.
- **Elevated Card Velocity**: `pi_velocity_count_1h >= 3`.
- **Severe Spending Surge**: `cust_amount_to_mean_ratio >= 6.0`.

### Tier 3: APPROVE Precedence (Normal Legitimate Traffic)
- All risk signals remain within safe baseline thresholds.

---

## 5. Full Dataset Replay & Decision Distribution (67,858 Transactions)

Replayed across the complete 6-month simulation dataset:

| Decision State | Transaction Count | Percentage | Operational Meaning |
|---|:---:|:---:|---|
| **`APPROVE`** | **66,681** | **98.27%** | Frictionless authorization for legitimate users |
| **`REVIEW`** | **459** | **0.68%** | Triage queue for fraud analysts / secondary verification |
| **`HOLD`** | **718** | **1.06%** | Automated freeze on bot bursts and syndicates |
| **Total Intervention** | **1,177** | **1.73%** | Highly targeted risk perimeter |

### Fraud Archetype Recall Across Full Dataset:
- **Card Testing Velocity**: **100.00%** (385/385 caught)
- **Account Takeover (ATO)**: **98.40%** (123/125 caught)
- **Coordinated Abuse Rings**: **100.00%** (210/210 caught)
- **Total Fraud Detection Recall**: **99.72%** (718/720 total fraud transactions intercepted)
- **Total Fraud Loss Prevented**: **INR 2,697,676.01**

---

## 6. Comparative Business Benchmark (Held-Out Test Set)

Evaluated on the frozen 10,179 held-out test transactions (June 11–30, 2025):

| Risk System | Precision | Recall | F1 Score | Review Rate | Hold Rate | Expected Financial Loss | Fraud Loss Prevented |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Stage 4 Rules Baseline** | 44.44% | 21.37% | 28.87% | 0.62% | 0.00% | ₹641,079.22 | ₹30,865.41 |
| **Stage 5 Logistic Regression** | 63.68% | 92.37% | 75.39% | 1.87% | 0.00% | ₹85,394.91 | ₹599,299.72 |
| **Stage 5 LightGBM** | 97.73% | 98.47% | 98.10% | 1.30% | 0.00% | ₹16,255.32 | ₹655,639.31 |
| **Stage 7 Policy v1** | **60.00%** | **98.47%** | **74.57%** | **0.84%** | **0.98%** | **₹26,355.32** | **₹655,639.31** |

> **Key Architectural Insight**: While LightGBM operated in a single binary classification mode (flagging all 132 transactions as positive), Policy v1 splits actions into **`HOLD`** (0.98%) for instant blocking and **`REVIEW`** (0.84%) for manual review triage, preventing ₹655,639.31 in fraud while keeping human review queues down to only 0.84% of total traffic.

---

## 7. Auditability & Decision Schema (`evaluation/policy_v1/decisions.csv`)

Every transaction evaluated produces an immutable, structured audit record:

```json
{
  "transaction_id": 2557,
  "timestamp": "2025-01-30 21:41:22",
  "amount": 96.32,
  "ml_probability": 0.9995,
  "graph_ring_score": 0.0,
  "graph_ring_candidate": 0,
  "triggered_rules": ["RULE_PI_VELOCITY_ELEVATED"],
  "policy_version": "sentinelrisk-policy-v1",
  "decision": "HOLD",
  "is_intervention": 1,
  "primary_trigger": "HIGH_CONFIDENCE_ML_RISK",
  "reasons": [
    "ML fraud probability (0.999) exceeds critical hold threshold (0.50).",
    "Elevated card velocity: 3 transactions on payment token in 1 hour."
  ]
}
```

---

## 8. Execution Commands

```bash
# 1. Replay policy across historical transaction dataset
python scripts/replay_policy.py

# 2. Run automated policy unit tests (80 tests)
python -m pytest tests/unit/test_policy_engine.py -v
```
