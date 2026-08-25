# Model Card: LightGBM Gradient-Boosted Decision Trees Risk Baseline

> Non-linear gradient-boosted tree supervised benchmark for transaction fraud detection in SentinelRisk.

---

## 1. Model Details

- **Model Type**: Gradient-Boosted Decision Tree Classifier (`lightgbm.LGBMClassifier`)
- **Version**: 1.0.0
- **Library**: `lightgbm==4.7.0`
- **Objective**: Binary Log-loss
- **Key Hyperparameters**:
  - `scale_pos_weight`: `86.16` (derived from training class ratio $N_{\text{neg}} / N_{\text{pos}}$)
  - `n_estimators`: `150`
  - `learning_rate`: `0.05`
  - `max_depth`: `6`
  - `num_leaves`: `31`
  - `min_child_samples`: `20`
  - `random_state`: `42`
- **Decision Probability Threshold**: `0.05` (Optimized on Validation set to minimize Expected Financial Loss)

---

## 2. Intended Use

- **Primary Objective**: Establish the non-linear machine-learning benchmark for tabular payment risk scoring.
- **Input**: 47 point-in-time engineered features as-of timestamp $t < T$.
- **Output**: Calibrated risk probability $P(\text{fraud} \mid \mathbf{x}) \in [0.0, 1.0]$.
- **Target Audience**: Real-time authorization scoring and fraud operations triage.

---

## 3. Training Data & Preprocessing

- **Dataset**: `data/features/transaction_features.csv` (Stage 3 point-in-time feature store).
- **Partition**: Chronological first 70% (47,500 transactions, Jan 1 to May 23, 2025).
- **Target Variable**: `is_fraud_ground_truth` (545 positive fraud cases, 1.15% prevalence).
- **Feature Schema**: 47 continuous, categorical, and binary features.
- **Excluded Features**: Raw identifiers (`customer_id`, `merchant_id`, `device_id`, `payment_instrument_id`), timestamp, and observed noisy labels.

---

## 4. Evaluation Performance (Held-Out Test Set)

Evaluated on 10,179 held-out test transactions (June 11 to June 30, 2025):

- **Precision**: **97.73%**
- **Recall**: **98.47%**
- **F1 Score**: **98.10%**
- **PR-AUC**: **99.92%**
- **ROC-AUC**: **100.00%**
- **False Positive Rate (FPR)**: **0.03%** (Only 3 false positives out of 10,048 legitimate transactions!)
- **False Negative Rate (FNR)**: **1.53%** (Only 2 missed fraud cases out of 131)
- **Expected Financial Loss**: **INR 16,255.32** (97.5% reduction vs. Stage 4 Rules!)
- **Fraud Loss Prevented (Benefit)**: **INR 655,639.31**

### Archetype Recall Breakdown:
- **Card Testing Velocity**: **100.00%** (31/31 caught)
- **Account Takeover (ATO)**: **98.00%** (98/100 caught)
- **Coordinated Rings**: **0.00%** (0/0 cases in test set)

---

## 5. Top Predictive Features (by Gain Importance)

1. `pi_velocity_count_1h`: Primary driver of card testing and rapid reuse fraud.
2. `cust_amount_to_mean_ratio`: Key indicator of account takeover spending deviations.
3. `device_is_new_for_cust`: Unrecognized device authorization flag.
4. `cust_amount_zscore`: Standardized statistical distance from customer baseline.
5. `amount_to_merchant_mean_ratio`: Merchant-relative anomaly detection.

---

## 6. Limitations & Known Failure Modes

1. **Synthetic Distribution Calibration**: Extremely high test metrics (PR-AUC 99.92%) reflect clear synthetic behavioral archetype separations; real production traffic exhibits fuzzier adversary evolution and heavier label noise.
2. **Coordinated Multi-Account Rings**: Tree models evaluate single rows independently and cannot detect shared device rings spanning multiple identities without graph features.
3. **Threshold Sensitivity**: Operating threshold (0.05) is calibrated for high recall under class-imbalance weighting (`scale_pos_weight=86.16`).
