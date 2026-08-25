# SentinelRisk — Rules-Only Risk Baseline & Benchmark Report

> Transparent, deterministic rules-based fraud detection benchmark evaluated on a temporally held-out test set.

---

## 1. Executive Overview & Purpose

The **Rules-Only Baseline** establishes an interpretable, deterministic benchmark for SentinelRisk. In payment risk engineering, machine learning models should not be assumed to be superior by default; they must demonstrate measurable, statistically sound improvements over a well-configured rules baseline.

This stage answers the core question:
> *"How well can a carefully designed rules-based system perform before introducing machine learning?"*

### Scope Boundary
- **Pure Deterministic Rules**: Configurable rule thresholds, integer weights, and explicit reason explanations.
- **Strict Chronological Evaluation**: 70% Train (Jan 1–May 23), 15% Validation (May 23–Jun 11), 15% Held-Out Test (Jun 11–Jun 30).
- **Zero Test Set Contamination**: Threshold selection was performed strictly on the Validation set; the Test set was evaluated once with frozen parameters.
- **No Machine Learning**: No Logistic Regression, no LightGBM, no neural networks, and no graph algorithms were used.

---

## 2. Rule Architecture & Signal Definitions

| Rule | Signal Evaluated | Activation Condition | Weight | Rationale |
|---|---|---|:---:|---|
| **RULE_CUST_AMOUNT_ANOMALY** | Customer Amount Anomaly | `cust_is_first_txn == 0` and `cust_amount_to_mean_ratio >= 4.0` | `+2` | Identifies sudden spending surges 4x above the customer's established average. |
| **RULE_CUST_VELOCITY** | Customer Velocity Surge | `velocity_txn_count_1h >= 3` or `velocity_txn_count_24h >= 6` | `+2` | Captures rapid-fire transactions on a single customer profile in a short window. |
| **RULE_DEVICE_NOVELTY_COMPOUND**| Device Novelty Compound | `device_is_new_for_cust == 1` and (`cust_amount_to_mean_ratio >= 2.5` or `cust_is_first_txn == 0 and amount >= 5000`) | `+2` | Recognizes high-ticket or elevated spend executed on a brand new device (primary ATO signal). |
| **RULE_PI_VELOCITY** | Payment Token Velocity | `pi_velocity_count_1h >= 3` | `+3` | Detects automated card-testing bot attacks executing multiple rapid authorizations on a single card token. |
| **RULE_MERCHANT_ANOMALY** | Merchant Relative Spike | `amount_to_merchant_mean_ratio >= 5.0` | `+1` | Flags transactions 5x higher than the merchant's normal baseline AOV (e.g. ₹50k ticket at a micro-merchant). |
| **RULE_OFF_HOUR_ANOMALY** | Off-Hour Night Anomaly | `is_night == 1` (00:00–05:59) and `amount >= 8000.0` | `+1` | Flags high-ticket transactions occurring in the middle of the night when legitimate retail volume is near zero. |

### Decision Risk Bands:
- `Score < 3.0` $\rightarrow$ **APPROVE** (Low Risk)
- `3.0 <= Score < 5.0` $\rightarrow$ **REVIEW** (Medium Risk — analyst triage)
- `Score >= 5.0` $\rightarrow$ **HOLD / DECLINE** (High Risk)

---

## 3. Chronological Dataset Split

To simulate real-world production deployment (*"train on the past, deploy on the future"*), the 67,858 transactions were partitioned strictly by timestamp:

```text
2025-01-01 ───────────────────────── 2025-05-23 ────────── 2025-06-11 ────────── 2025-06-30
           TRAIN (70%)                     VAL (15%)              TEST (15%)
         47,500 txns                      10,179 txns             10,179 txns
        545 fraud (1.15%)                44 fraud (0.43%)        131 fraud (1.29%)
```

---

## 4. Threshold Tuning on Validation Set

Candidate rule-score thresholds were evaluated strictly on the Validation set:

| Score Threshold | Precision | Recall | F1 Score | Review Rate | Expected Loss (INR) | Selection Rationale |
|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **1.0** | 9.43% | 68.18% | 16.57% | 3.12% | ₹117,062.45 | High review volume and friction |
| **2.0** | 10.47% | 61.36% | 17.88% | 2.53% | ₹138,753.86 | Suboptimal precision |
| **3.0 (Selected)** | **44.64%** | **56.82%** | **50.00%** | **0.55%** | **₹112,296.47** | **Optimal balance of review volume and fraud recall** |
| **4.0** | 75.76% | 56.82% | 64.94% | 0.32% | ₹107,696.47 | High precision, same recall |
| **5.0** | 100.00% | 54.55% | 70.59% | 0.24% | ₹113,229.24 | Conservative |
| **6.0+** | 0.00% | 0.00% | 0.00% | 0.00% | ₹113,470.01 | Overly strict (misses all fraud) |

**Decision**: Score Threshold **3.0** was frozen as the production rules baseline.

---

## 5. Held-Out Test Set Performance (Actual Computed Results)

The frozen configuration (Score Threshold $\ge 3.0$) was evaluated on the 10,179 held-out test transactions:

### Key Metrics:
- **Precision**: **44.44%**
- **Recall**: **21.37%**
- **F1 Score**: **28.87%**
- **False Positive Rate (FPR)**: **0.35%** (Only 35 legitimate users impacted out of 10,048)
- **False Negative Rate (FNR)**: **78.63%**
- **Review Rate**: **0.62%** (63 transactions flagged for review)

### Confusion Matrix (Test Set):
```
                       Actual Status
                 Legitimate         Fraud
Predicted
Legitimate    TN: 10,013         FN: 103
Fraud         FP: 35             TP: 28
```

---

## 6. Business Cost Model & Expected Loss

### Configurable Cost Parameters:
- **False Negative Loss**: 100% of transaction value lost on unprevented fraud.
- **False Positive Cost**: ₹150 per false positive (customer friction + review triage overhead).
- **Manual Review Cost**: ₹50 per reviewed transaction.

### Test Set Financial Impact:
- **False Negative Fraud Loss**: **INR 633,979.22** (103 missed fraud events)
- **False Positive Friction Cost**: **INR 5,250.00** (35 legitimate users impacted)
- **Review Overhead Cost**: **INR 1,850.00**
- **Total Expected Loss**: **INR 641,079.22**
- **Fraud Loss Prevented (True Positive Benefit)**: **INR 30,865.41** (28 fraud transactions stopped)

---

## 7. Fraud Archetype Breakdown (Test Set)

| Fraud Archetype | Total Test Cases | Caught Cases | Missed Cases | Recall | Performance Analysis |
|---|:---:|:---:|:---:|:---:|---|
| **Card Testing Velocity** | 31 | 25 | 6 | **80.65%** | **Strong**: Payment instrument velocity rule (`RULE_PI_VELOCITY`) catches automated high-frequency testing. |
| **Account Takeover (ATO)** | 100 | 3 | 97 | **3.00%** | **Weak**: Single-point rules miss subtle ATO where attackers make normal-looking purchases without triggering high velocity. |
| **Coordinated Abuse Rings** | 0 | 0 | 0 | **N/A** | **Blind Spot**: Coordinated syndicates share infrastructure across separate identities, bypassing individual account rules. |

---

## 8. Systematic Error Analysis

### False Positives (Legitimate Flagged as Fraud):
1. **Legitimate Electronics / Travel Splurge**: A regular customer making an occasional luxury purchase (e.g. ₹18,000 on a laptop at 10 PM) triggers customer amount anomaly and merchant ratio rules.
2. **Flash Sale Velocity**: A legitimate customer purchasing multiple festival gift cards in 30 minutes triggers the customer velocity rule.
3. **Legitimate Device Upgrade**: A customer using a brand new phone to buy a flight ticket triggers the `RULE_DEVICE_NOVELTY_COMPOUND`.

### False Negatives (Fraud Missed by Rules):
1. **Low-Velocity ATO**: An attacker compromising an account and making a single ₹6,000 purchase during daytime (does not trigger velocity, off-hour, or high-ratio rules).
2. **Dispersed Card Testing**: Attackers spacing out card testing attempts across 3–4 hours (staying below the 1-hour threshold of 3 attempts).
3. **Syndicate Ring Transactions**: Coordinated ring members transacting with small amounts (₹2,500) from distinct accounts, looking completely benign to individual account rules.

---

## 9. Key Takeaways & Stage 5 Motivation

1. **Rules Excel at Obvious Velocity**: The baseline achieves an **80.65% recall** on Card Testing attacks with low false positive rate (0.35%).
2. **Rules Fail on Complex / Multi-Entity Patterns**: With only a **3.00% recall** on ATO and complete inability to see graph structures, a rules-only system suffers from heavy false negative losses (₹633,979).
3. **The Challenge for Stage 5**: Machine Learning (Logistic Regression, LightGBM) must demonstrate:
   - Higher overall Recall without destroying Precision.
   - Non-linear feature interactions (combining subtle device age, decline rates, and Z-scores) to catch ATO.
   - Significant reduction in Expected Loss.

---

## 10. Execution Commands

```bash
# Run rules evaluation and export benchmark artifacts
python scripts/evaluate_rules.py

# Run automated test suite
python -m pytest tests/unit/test_rules_baseline.py -v
```
