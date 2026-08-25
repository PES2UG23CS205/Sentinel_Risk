# SentinelRisk — Stage 12: Risk-Based Payment Friction & Step-Up Challenge Orchestration

## 1. Executive Summary

Traditional fraud prevention architectures rely on a simplistic binary or tri-state decision model (`APPROVE`, `REVIEW`, `HOLD`). In real-world payment ecosystems (such as Razorpay's merchant network), treating fraud mitigation as *"block everything suspicious"* induces massive business friction:
- **False Declines / High Churn**: Legitimate customers making unusual or high-ticket purchases are insulted by hard declines.
- **Analyst Queue Overload**: Minor behavioral anomalies flood human fraud review queues with low-priority tickets.
- **Conversion Loss**: Every point of unnecessary friction reduces merchant gross merchandise value (GMV).

**SentinelRisk Stage 12 introduces Risk-Based Payment Friction Orchestration**, transforming the policy engine into a **Quad-State Decision System**:

$$\text{Decision} \in \{\text{APPROVE (Zero Friction)}, \text{CHALLENGE (Step-Up)}, \text{REVIEW (Analyst Queue)}, \text{HOLD (Platform Protection)}\}$$

Instead of treating risk management as binary enforcement, SentinelRisk applies **the least-friction intervention that minimizes expected loss**.

---

## 2. Decision Precedence Matrix & Hierarchy

The Policy Engine enforces deterministic precedence across 4 tiers:

```
                                  INCOMING TRANSACTION
                                           │
                                [Feature & Model Scoring]
                                           │
          ┌────────────────────────────────┴────────────────────────────────┐
          ▼                                                                 ▼
  [High Confidence Threat / Bot]                               [Syndicate / Heavy Loss Risk]
  (ML >= 0.50, Vel >= 5, Ring >= 0.80)                         (Ring >= 0.50, ML >= 0.25)
          │                                                                 │
        HOLD                                                              REVIEW
  (Platform Protection)                                            (Human Analyst Triage)
                                                                            │
          ┌─────────────────────────────────────────────────────────────────┘
          ▼
  [Moderate Anomaly / Uncertainty]                             [Low Risk Baseline]
  (0.05 <= ML < 0.25, Vel 3-4, Ratio 4-6, New Dev)             (All signals <= baseline)
          │                                                                 │
      CHALLENGE                                                          APPROVE
  (Automated Step-Up Friction)                                      (Zero Friction Pass)
```

| Decision State | Precedence | Triggers & Risk Range | Target Action | Analyst Case Created? |
| :--- | :---: | :--- | :--- | :---: |
| **`HOLD`** | **Tier 1 (Highest)** | $\text{ML} \ge 0.50$, $\text{Velocity}_{1\text{h}} \ge 5$, $\text{Ring} \ge 0.80$, Compound Threat | Immediate platform block | **Yes** (Priority P0) |
| **`REVIEW`** | **Tier 2** | $0.50 \le \text{Ring} < 0.80$, $\text{ML} \ge 0.25$, $\text{Ratio} \ge 6.0\times$ | Human analyst case triage | **Yes** (Priority P1/P2) |
| **`CHALLENGE`** | **Tier 3** | $0.05 \le \text{ML} < 0.25$, $\text{Velocity} \in [3, 4]$, $\text{Ratio} \in [4.0, 6.0)$, New Device + Novelty | Automated step-up auth | **No** (Zero analyst queue overhead) |
| **`APPROVE`** | **Tier 4 (Lowest)** | All risk signals below challenge threshold | Frictionless zero-delay pass | **No** |

---

## 3. Deterministic Challenge Catalog

When `CHALLENGE` is triggered, the system selects an evidence-grounded challenge type tailored to the specific risk vector:

```
┌──────────────────────────────────────┬──────────────────┬────────────────────────────────────────────────────────────────────────┐
│ Challenge Code                       │ Friction Level   │ Trigger Condition                                                      │
├──────────────────────────────────────┼──────────────────┼────────────────────────────────────────────────────────────────────────┤
│ CHALLENGE_DEVICE_VERIFICATION        │ LOW (1-Click)    │ Unrecognized device hardware token + moderate spend deviation          │
│ CHALLENGE_CUSTOMER_CONFIRMATION      │ LOW (Push/SMS)   │ Spend anomaly on established customer account                          │
│ CHALLENGE_PAYMENT_REAUTH             │ MEDIUM (3DS OTP) │ High-velocity card token burst across disparate terminals              │
└──────────────────────────────────────┴──────────────────┴────────────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Defense-Only Simulation Boundary**: In accordance with project safeguards, SentinelRisk **does not** execute actual 3DS redirects, issue live SMS OTPs, or invoke external payment gateway APIs. Step-up challenges are simulated as deterministic orchestration metadata.

---

## 4. Cost Model & Financial Tradeoff Formulation

The system optimizes for **Total Expected Cost**:

$$\text{Cost}_{\text{total}} = C_{\text{fraud\_loss}} + C_{\text{friction}} + C_{\text{analyst}}$$

Where:
- $C_{\text{fraud\_loss}} = \sum (\text{Uncaught Fraud Amount} \times 1.0)$
- $C_{\text{friction}} = (\text{Held Legit Txns} \times ₹250) + (\text{Challenged Legit Txns} \times ₹35)$
- $C_{\text{analyst}} = \text{Reviewed Cases} \times ₹50$

### Unit Cost Assumptions
- **Hard Decline Insult Cost ($C_{\text{hold}}$)**: $₹250.00$ (Customer churn, merchant support tickets, lost lifetime value)
- **Automated Challenge Cost ($C_{\text{challenge}}$)**: $₹35.00$ (~$7\times$ cheaper than hard decline; automated OTP/biometric step-up)
- **Manual Review Cost ($C_{\text{review}}$)**: $₹50.00$ (Human investigator labor and case queue latency)
- **Fraud Loss Multiplier ($C_{\text{fraud}}$)**: $1.0\times$ (Direct unrecovered chargeback loss)

---

## 5. Quantitative Benchmark Results

Evaluated on the frozen synthetic test set (10,179 transactions) and external Fraud Detection Handbook test set (316,197 transactions):

### Synthetic Payments Ecosystem (Held-Out Test Set: 10,179 Txns)

| Policy Engine Architecture | Approval Rate | Challenge Rate | Review Rate | Hold Rate | Fraud Recall | Total Financial Cost |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Stage 7 Tri-State Policy** | 96.83% | 0.00% | 1.90% (193 cases) | 1.28% | 98.47% | **₹48,055.32** |
| **Stage 12 Quad-State Policy** | 96.74% | 1.16% (118 challenges) | **0.83% (84 cases)** | 1.28% | 98.47% | **₹30,385.32** |
| **Delta / Improvement** | *-0.09%* | *+1.16%* | **-56.5% Analyst Load** | *0.00%* | **+0.00% (Identical Recall)** | **-36.8% Cost Savings** |

### External Dataset Replay (Held-Out Test Set: 316,197 Txns)

| Policy Engine Architecture | Approval Rate | Challenge Rate | Review Rate | Hold Rate | Total Cost |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stage 7 Tri-State Policy** | 56.12% | 0.00% | 37.81% (119,544 cases) | 6.07% | €28,414,720.83 |
| **Stage 12 Quad-State Policy** | 56.12% | 15.94% (50,409 challenges) | **21.86% (69,135 cases)** | 6.07% | **€20,135,300.83** |
| **Delta / Improvement** | *0.00%* | *+15.94%* | **-42.2% Analyst Load** | *0.00%* | **-29.1% Cost Savings** |

---

## 6. Architectural Guarantees & Safeguards

1. **Deterministic Authority**: The Policy Engine is the single source of truth for decision outcomes. Downstream LLM agents cannot alter decisions or bypass challenges.
2. **Analyst Queue Protection**: Step-up challenges do not create analyst tickets. Only `REVIEW` and `HOLD` populate the investigation queue.
3. **Idempotent API Responses**: Repeated evaluations return identical decision states and cached challenge metadata.
4. **Schema-Adaptive Compatibility**: The friction ladder functions seamlessly across synthetic multi-token schemas and external single-token schemas.
