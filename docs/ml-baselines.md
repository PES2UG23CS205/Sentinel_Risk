# SentinelRisk — Machine Learning Baselines & Benchmark Report

> Controlled comparison of Supervised Machine Learning Baselines (Logistic Regression & LightGBM) against the Frozen Stage 4 Rules Benchmark.

---

## 1. Executive Summary & Core Finding

In this stage, we conducted a rigorous controlled experiment to answer the fundamental question:
> *"Does machine learning materially outperform our transparent rules baseline?"*

### The Definitive Answer: **YES**

| Metric | Stage 4 Rules Baseline (Frozen) | Model 1: Logistic Regression | Model 2: LightGBM | ML Gain vs. Rules |
|---|:---:|:---:|:---:|:---:|
| **Precision** | 44.44% | 63.68% | **97.73%** | **+53.29%** |
| **Recall** | 21.37% | 92.37% | **98.47%** | **+77.10%** |
| **F1 Score** | 28.87% | 75.39% | **98.10%** | **+69.23%** |
| **PR-AUC** | -- | 93.36% | **99.92%** | **+99.92%** |
| **ROC-AUC** | -- | 99.80% | **100.00%** | **+100.00%** |
| **False Positive Rate (FPR)**| 0.35% | 0.69% | **0.03%** | **-0.32% (Only 3 FPs!)** |
| **False Negative Rate (FNR)**| 78.63% | 7.63% | **1.53%** | **-77.10% (Only 2 FNs!)** |
| **Review Rate** | 0.62% | 1.87% | **1.30%** | Manageable queue |
| **Expected Financial Loss** | **INR 641,079.22** | **INR 85,394.91** | **INR 16,255.32** | **97.5% Loss Reduction** |
| **Fraud Loss Prevented** | INR 30,865.41 | INR 599,299.72 | **INR 655,639.31** | **+INR 624,773.90** |

---

## 2. Experimental Rigor & Methodology

To ensure scientific honesty and fairness:
1. **Identical Point-in-Time Dataset**: Both models consumed the exact same 47 point-in-time features generated in Stage 3 (`data/features/transaction_features.csv`).
2. **Exact Chronological Split**: Preserved the Stage 4 chronological boundaries:
   - **Train (70%)**: Jan 1 to May 23, 2025 (47,500 transactions, 545 fraud cases)
   - **Validation (15%)**: May 23 to Jun 11, 2025 (10,179 transactions, 44 fraud cases)
   - **Held-Out Test (15%)**: Jun 11 to Jun 30, 2025 (10,179 transactions, 131 fraud cases)
3. **Strict Target & Identifier Exclusion**: Raw entity identifiers (`customer_id`, `merchant_id`, `device_id`, `payment_instrument_id`, `transaction_id`) and target metadata (`is_fraud`, `fraud_archetype`, `fraud_case_id`) were strictly excluded from $X$.
4. **Validation-Only Threshold Optimization**: Probability thresholds were tuned on the **Validation set only** to minimize Expected Loss. The Test set was evaluated once with frozen parameters.

---

## 3. Fraud Archetype Recall Breakdown

| Fraud Archetype | Rules Baseline | Logistic Regression | LightGBM | Behavioral Insight |
|---|:---:|:---:|:---:|---|
| **Card Testing Velocity** | 80.65% (25/31) | **100.00%** (31/31) | **100.00%** (31/31) | Both ML models easily detect high-frequency payment instrument velocity bursts. |
| **Account Takeover (ATO)** | **3.00%** (3/100) | **90.00%** (90/100) | **98.00%** (98/100) | **Massive Breakthrough**: LightGBM resolves the primary rules weakness by learning non-linear interactions across device novelty, spending ratios, and customer age. |
| **Coordinated Abuse Rings** | 0.00% (0/0) | 0.00% (0/0) | 0.00% (0/0) | Multi-account ring fraud bypasses single-row models; motivates graph detection in Stage 6. |

---

## 4. Top Predictive Signals & Interpretability

### Top 5 Features for LightGBM (by Gain Importance):
1. `pi_velocity_count_1h`: Immediate card testing authorization frequency.
2. `cust_amount_to_mean_ratio`: Magnitude of spending deviation from customer baseline.
3. `device_is_new_for_cust`: Unrecognized device flag.
4. `cust_amount_zscore`: Statistical distance from historical mean.
5. `amount_to_merchant_mean_ratio`: Merchant-relative anomaly detection.

### Top Positive Risk Coefficients for Logistic Regression:
1. `pi_velocity_count_1h`: `+3.4241` (Strongest positive risk predictor)
2. `cust_amount_to_mean_ratio`: `+2.1804` (Elevated spending increases log-odds of fraud)
3. `device_is_new_for_cust`: `+1.8512` (Unrecognized device increases fraud log-odds)
4. `velocity_txn_count_1h`: `+1.6219` (Customer short-term velocity surge)

---

## 5. Probability Calibration Analysis

Probabilities were binned into 10 deciles on the held-out test set:

| Risk Decile Bucket | Transaction Count | Mean Predicted Probability | Observed Actual Fraud Rate |
|---|:---:|:---:|:---:|
| `[0.0, 0.1)` | 10,046 | 0.02% | 0.02% (2 FNs) |
| `[0.1, 0.2)` | 2 | 14.20% | 50.00% |
| `[0.2, 0.3)` | 1 | 26.50% | 100.00% |
| `[0.3, 0.4)` | 0 | -- | -- |
| `[0.4, 0.5)` | 2 | 45.10% | 100.00% |
| `[0.5, 0.6)` | 1 | 54.80% | 100.00% |
| `[0.6, 0.7)` | 3 | 66.20% | 100.00% |
| `[0.7, 0.8)` | 5 | 74.90% | 100.00% |
| `[0.8, 0.9)` | 12 | 85.30% | 100.00% |
| `[0.9, 1.0]` | 107 | 98.40% | 97.20% (104/107) |

**Finding**: LightGBM exhibits strong bimodal risk separation: the vast majority of legitimate traffic falls below 0.02%, while fraud is concentrated above 80.0%.

---

## 6. Execution Commands

```bash
# 1. Train models, optimize validation thresholds, and evaluate test set
python scripts/train_models.py

# 2. Evaluate pre-trained models on any features dataset
python scripts/evaluate_models.py

# 3. Run automated ML test suite
python -m pytest tests/unit/test_ml_baselines.py -v
```
