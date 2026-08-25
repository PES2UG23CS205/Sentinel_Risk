# SentinelRisk — Stage 7: Policy Engine Benchmark Report

## 1. Executive Summary
The **SentinelRisk Policy Engine (v1)** integrates LightGBM ML probabilities, entity graph ring scores, and deterministic velocity rules to generate tri-state risk decisions (`APPROVE`, `REVIEW`, `HOLD`).

### Decision Distribution (Overall 67,858 Transactions):
- **APPROVE**: 66,681 (98.27%)
- **REVIEW**: 459 (0.68%)
- **HOLD**: 718 (1.06%)
- **Total Intervention Rate**: 1,177 (1.73%)

---

## 2. Comparative Business Benchmark (Held-Out Test Set)

| System | Precision | Recall | F1 Score | Review Rate | Expected Loss (INR) | Fraud Prevented (INR) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Stage 4 Rules Baseline** | 44.44% | 21.37% | 28.87% | 0.62% | ₹641,079.22 | ₹30,865.41 |
| **Stage 5 Logistic Regression** | 63.68% | 92.37% | 75.39% | 1.87% | ₹85,394.91 | ₹599,299.72 |
| **Stage 5 LightGBM** | 97.73% | 98.47% | 98.10% | 1.30% | ₹16,255.32 | ₹655,639.31 |
| **Stage 7 Policy v1** | **60.00%** | **98.47%** | **74.57%** | **0.84%** | **₹26,355.32** | **₹655,639.31** |

---

## 3. Fraud Archetype Recall (Full 6-Month Dataset)

- **Card Testing Velocity**: **100.00%** (385/385)
- **Account Takeover (ATO)**: **98.40%** (123/125)
- **Coordinated Abuse Rings**: **100.00%** (210/210)
