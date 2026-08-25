# Model Card: Logistic Regression Risk Baseline

> Linear supervised classification benchmark for transaction fraud detection in SentinelRisk.

---

## 1. Model Details

- **Model Type**: Regularized Logistic Regression (`sklearn.linear_model.LogisticRegression`)
- **Version**: 1.0.0
- **Library**: `scikit-learn==1.9.0`
- **Solver**: `lbfgs`
- **Regularization**: $L_2$ ($C=1.0$)
- **Class Imbalance Strategy**: `class_weight='balanced'`
- **Decision Probability Threshold**: `0.60` (Optimized on Validation set to minimize Expected Financial Loss)

---

## 2. Intended Use

- **Primary Objective**: Establish an interpretable, linear machine-learning benchmark for payment transaction risk scoring.
- **Input**: 47 point-in-time engineered features as-of timestamp $t < T$.
- **Output**: Calibrated risk probability $P(\text{fraud} \mid \mathbf{x}) \in [0.0, 1.0]$.
- **Target Audience**: Risk operations analysts and risk engine benchmark evaluation.

---

## 3. Training Data & Preprocessing

- **Dataset**: `data/features/transaction_features.csv` (Stage 3 point-in-time feature store).
- **Partition**: Chronological first 70% (47,500 transactions, Jan 1 to May 23, 2025).
- **Target Variable**: `is_fraud_ground_truth` (545 positive fraud cases, 1.15% prevalence).
- **Preprocessing Pipeline**:
  - Continuous features: `StandardScaler` (zero mean, unit variance fitted on training partition only).
  - Categorical indices (`merchant_category_idx`, `pi_type_idx`, `day_of_week`, `hour_of_day`): `OneHotEncoder(handle_unknown='ignore')`.
  - Binary features (`is_weekend`, `is_night`, `cust_is_first_txn`, `device_is_new_for_cust`): Passthrough.
- **Excluded Features**: Raw identifiers (`customer_id`, `merchant_id`, `device_id`, `payment_instrument_id`), timestamp, and observed noisy labels.

---

## 4. Evaluation Performance (Held-Out Test Set)

Evaluated on 10,179 held-out test transactions (June 11 to June 30, 2025):

- **Precision**: **63.68%**
- **Recall**: **92.37%**
- **F1 Score**: **75.39%**
- **PR-AUC**: **93.36%**
- **ROC-AUC**: **99.80%**
- **False Positive Rate (FPR)**: **0.69%** (69 false positives)
- **False Negative Rate (FNR)**: **7.63%** (10 missed fraud cases)
- **Expected Financial Loss**: **INR 85,394.91** (86.7% reduction vs. Stage 4 Rules)

### Archetype Recall Breakdown:
- **Card Testing Velocity**: **100.00%** (31/31 caught)
- **Account Takeover (ATO)**: **90.00%** (90/100 caught)
- **Coordinated Rings**: **0.00%** (0/0 cases in test set)

---

## 5. Strengths & Key Coefficients

### Strengths:
1. High recall on ATO (90.0%) compared to static rules (3.0%), capturing linear combinations of customer ratio, device novelty, and payment instrument velocity.
2. Direct coefficient interpretability: feature log-odds can be inspected without black-box surrogate methods.

### Top Positive Risk Coefficients (Increase Log-Odds of Fraud):
1. `pi_velocity_count_1h`: Strongest positive driver (+3.42)
2. `cust_amount_to_mean_ratio`: Major driver of ATO risk (+2.18)
3. `device_is_new_for_cust`: Unrecognized device indicator (+1.85)
4. `velocity_txn_count_1h`: Customer velocity burst (+1.62)

---

## 6. Limitations & Known Failure Modes

1. **Linearity Assumption**: Cannot learn multiplicative non-linear feature interactions (e.g., interaction between device age and decline rates) without manual polynomial feature engineering.
2. **False Positive Volume**: Generates 69 false positives (0.69% FPR) compared to LightGBM's 3 false positives (0.03% FPR).
3. **Coordinated Ring Blind Spot**: Single-point feature vector cannot discover cross-account graph topology.
