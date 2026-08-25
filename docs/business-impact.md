# SentinelRisk — Business Impact, Cost Optimization & Tradeoffs

> Multi-dimensional optimization balancing fraud chargeback losses, customer checkout friction, and analyst operational capacity.

---

## 1. The Trilemma in Payment Risk Management

Modern payment gateways face an inherent three-way conflict:
1. **Direct Fraud Losses (Chargebacks & Fines)**: Unintercepted fraud results in 100% loss of transaction principal, card scheme fines, and merchant chargeback penalties.
2. **Customer Friction & Churn**: False positives (declining legitimate cardholders) erode GMV, damage consumer trust, and reduce platform checkout conversion.
3. **Analyst Fatigue & Queue Overflows**: Manual review queues have fixed human capacity ($< 1.0\%$ of traffic). Overloading analysts leads to queue backlogs and missed SLAs.

```
                   Direct Fraud Loss
                      (Chargebacks)
                          ▲
                         / \
                        /   \
                       /     \
                      /       \
                     /  Target \
                    /  Balance  \
                   /             \
                  ▼───────────────▼
         Customer Friction    Analyst Operational
           (False Rejects)         Capacity
```

---

## 2. Multi-Signal Defense Comparison (Held-Out Test Benchmark)

Evaluated on 10,179 held-out test transactions (June 11–30, 2025):

| Risk Defense System | Fraud Recall | Total Interventions | Review Rate | Hold Rate | Expected Financial Loss | Fraud Loss Prevented |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Stage 4 Rules Baseline** | 21.37% | 63 (0.62%) | 0.62% | 0.00% | ₹641,079.22 | ₹30,865.41 |
| **Stage 5 Logistic Regression**| 92.37% | 190 (1.87%) | 1.87% | 0.00% | ₹85,394.91 | ₹599,299.72 |
| **Stage 5 LightGBM Baseline** | 98.47% | 132 (1.30%) | 1.30% | 0.00% | ₹16,255.32 | ₹655,639.31 |
| **Stage 7 Policy Engine v1** | **98.47%** | **185 (1.82%)** | **0.84%** | **0.98%** | **₹26,355.32** | **₹655,639.31** |

### Key Business Insights:
1. **95.9% Financial Loss Reduction vs. Rules**: Upgrading from static velocity rules to SentinelRisk Policy v1 reduces total financial loss from **₹641,079.22 down to ₹26,355.32**.
2. **Frictionless Legitimate Traffic**: Over **98.27% of transactions** are approved instantly without human friction.
3. **Targeted Analyst Queue**: By separating high-confidence fraud into automated `HOLD` ($0.98\%$) and ambiguous edge cases into `REVIEW` ($0.84\%$), analyst triage volume is kept strictly within sustainable operations SLAs ($< 1.0\%$).

---

## 3. Fraud Archetype Defense Perimeter (Full 6-Month Dataset)

Across the entire 6-month payments simulation (67,858 transactions, 720 ground-truth frauds):

- **Total Fraud Intercepted**: **718 / 720 (99.72% overall recall)**
- **Card Testing Bot Bursts**: **100.00%** (385/385 caught)
- **Account Takeover (ATO) Surges**: **98.40%** (123/125 caught)
- **Coordinated Abuse Syndicates**: **100.00%** (210/210 caught across 15/15 rings)
- **Total Fraud Loss Prevented**: **INR 2,697,676.01**
