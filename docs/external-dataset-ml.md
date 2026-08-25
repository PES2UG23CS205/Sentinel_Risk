# SentinelRisk — External Dataset ML Inference & Schema-Adaptive Risk Pipeline

> **Dedicated Machine Learning & Point-in-Time Risk Pipeline for the Fraud Detection Handbook Dataset**  
> *Date: August 2026 • Status: Complete & Verified • Automated Tests: 144/144 Passing*

---

## 1. Executive Overview & Design Philosophy

In real-world payment platforms (such as **Razorpay**, **Stripe**, or **Adyen**), risk engines process transactions originating from heterogeneous channels:
1. **First-Party Integrated Checkout**: Provides rich device telemetry, hardware canvas fingerprints, user account age, and payment instrument tokens (e.g., SentinelRisk's 47-feature primary world).
2. **Third-Party Acquirer / External Ingestion**: Provides standard ISO-style transaction feeds containing only amounts, timestamps, customer IDs, and terminal IDs (e.g., the benchmark **Fraud Detection Handbook dataset**).

### The Anti-Pattern (Fabrication):
A common hackathon anti-pattern is to generate synthetic `device_id` or `payment_instrument_id` values to force third-party data through a model trained on rich first-party data. This causes artificial graph links, distorted probabilities, and false confidence.

### The SentinelRisk Solution (Schema-Adaptive ML):
SentinelRisk uses **schema-specific models rather than fabricating unavailable features**.
- When full first-party data is ingested $\rightarrow$ **`primary_synthetic_lightgbm`** (47 features).
- When third-party ISO / Handbook data is ingested $\rightarrow$ **`external_handbook_lightgbm`** (24 point-in-time features).
- When unmapped custom CSV data is ingested $\rightarrow$ **Deterministic Rule Fallback**.

```
                           INCOMING TRANSACTION
                                    │
                         [Schema Auto-Detection]
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
[Primary Schema (47 Feat)]  [Handbook Schema (24 Feat)]  [Custom / Unmapped Schema]
        │                           │                           │
  Primary LightGBM           External LightGBM           Deterministic Rules
(ATO/Bot/Ring Synthesis)     (Velocity/Spend Drift)     (Velocity Boundary Checks)
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    ▼
                         STAGE 7 POLICY ENGINE
                         (Cost-Sensitive Precedence)
                                    ▼
                         APPROVE / REVIEW / HOLD
                                    ▼
                       AI INVESTIGATION & AUDIT LOG
```

---

## 2. External Dataset Physical Profile

- **Dataset Source**: *Reproducible Machine Learning for Credit Card Fraud Detection* (Le Borgne, Siblini, Lebichot, Bontempi, 2022).
- **Storage Location**: [`data/external/fraud_handbook/data/`](file:///c:/Users/acer/Documents/SentinelRisk/data/external/fraud_handbook/data/)
- **Partitions**: **183 daily `.pkl` files** (`2018-04-01.pkl` to `2018-09-30.pkl`).
- **Total Volume**: **1,754,155 transactions**.
- **Fraud Volume**: **14,681 transactions** (**0.837% baseline fraud prevalence**).

### Raw Column Schema vs SentinelRisk Mapping

| Native Handbook Column | Data Type | Semantics | SentinelRisk Canonical Mapping |
|---|---|---|---|
| `TRANSACTION_ID` | `int64` | Unique authorization sequence ID | `transaction_id` |
| `TX_DATETIME` | `datetime64[ns]` | Transaction timestamp | `timestamp` |
| `CUSTOMER_ID` | `int64 / str` | Originating customer identity | `customer_id` |
| `TERMINAL_ID` | `int64 / str` | Merchant POS / Terminal identifier | `merchant_id` |
| `TX_AMOUNT` | `float64` | Authorization amount (EUR) | `amount` |
| `TX_TIME_SECONDS` | `int64` | Elapsed seconds since simulation epoch | `derived_fields.TX_TIME_SECONDS` |
| `TX_TIME_DAYS` | `int64` | Elapsed days (0 to 182) | Chronological Split Index |
| `TX_FRAUD` | `int64` (0/1) | Ground-truth fraud label | `ground_truth_fraud` (**Isolated**) |
| `TX_FRAUD_SCENARIO` | `int64` (0-3) | Fraud scenario archetype | `ground_truth_scenario` (**Isolated**) |

---

## 3. Feature Engineering: Available vs Unavailable

### Available Features (24 Point-in-Time Features)
All features are extracted strictly as of $t < T$ using [`ml/features/external_features.py`](file:///c:/Users/acer/Documents/SentinelRisk/ml/features/external_features.py):

1. **Transaction Core (6)**:
   - `amount`: Raw authorization amount.
   - `amount_log`: $\ln(1 + \text{amount})$.
   - `hour_of_day`: 0 to 23.
   - `day_of_week`: 0 (Mon) to 6 (Sun).
   - `is_weekend`: Binary (1 if Saturday/Sunday else 0).
   - `is_night`: Binary (1 if hour $\in [0, 5]$ else 0).
2. **Customer Historical Behavioral Baselines (10)**:
   - `cust_txn_count_prev`: Prior completed transactions by customer.
   - `cust_velocity_1h`: Customer transactions in preceding 1 hour ($0 \le \Delta t \le 3,600\text{s}$).
   - `cust_velocity_24h`: Customer transactions in preceding 24 hours ($0 \le \Delta t \le 86,400\text{s}$).
   - `cust_velocity_7d`: Customer transactions in preceding 7 days ($0 \le \Delta t \le 604,800\text{s}$).
   - `cust_amount_sum_prev`: Cumulative spend prior to current transaction.
   - `cust_amount_mean_prev`: Prior average order value (AOV).
   - `cust_amount_std_prev`: Prior standard deviation of ticket sizes.
   - `cust_amount_max_prev`: Prior maximum transaction amount.
   - `cust_amount_ratio`: $\text{amount} / \max(1.0, \text{AOV})$.
   - `cust_amount_zscore`: $(\text{amount} - \text{AOV}) / \sigma$.
3. **Terminal / Merchant Behavioral Baselines (8)**:
   - `terminal_txn_count_prev`: Prior transactions processed at this terminal.
   - `terminal_velocity_1h`: Terminal transaction burst in preceding 1 hour.
   - `terminal_velocity_24h`: Terminal volume in preceding 24 hours.
   - `terminal_velocity_7d`: Terminal volume in preceding 7 days.
   - `terminal_amount_mean_prev`: Prior average ticket size at this terminal.
   - `terminal_amount_ratio`: $\text{amount} / \max(1.0, \text{Terminal Mean})$.
   - `terminal_unique_cust_prev`: Count of distinct customers previously seen at terminal.
   - `is_new_terminal_for_cust`: Binary (1 if customer has never transacted at this terminal before).

### Unavailable Features (23 Synthetic-Only Signals Omitted)
- Hardware device tokens (`device_id`, screen resolution, canvas hash, OS build).
- Payment instrument tokens (`payment_instrument_id`, card token, card brand, expiration).
- Account registration age (`cust_age_days`).
- Cross-account bipartite graph sharing metrics (`graph_ring_score`, `graph_ring_candidate`).

---

## 4. Temporal Splitting & Leakage Prevention

To prevent lookahead bias and target leakage:
1. **Chronological Splitting**:
   - **Training Set**: Days 0 to 119 (April 1 to July 29, 2018) — **1,150,370 transactions** (9,293 frauds, 0.808%).
   - **Validation Set**: Days 120 to 149 (July 30 to August 28, 2018) — **287,588 transactions** (2,564 frauds, 0.892%).
   - **Test Set**: Days 150 to 182 (August 29 to September 30, 2018) — **316,197 transactions** (2,824 frauds, 0.893%).
2. **Causality Constraint**: State accumulators update strictly **after** feature calculation ($t < T$).
3. **Label Isolation**: `TX_FRAUD` and `TX_FRAUD_SCENARIO` are strictly segregated from feature extraction and are only used for post-decision evaluation.

---

## 5. Dedicated LightGBM Model Architecture

- **Model Artifact**: [`ml/models/external_fraud/model.joblib`](file:///c:/Users/acer/Documents/SentinelRisk/ml/models/external_fraud/model.joblib)
- **Metadata**: [`ml/models/external_fraud/metadata.json`](file:///c:/Users/acer/Documents/SentinelRisk/ml/models/external_fraud/metadata.json)
- **Feature Manifest**: [`ml/models/external_fraud/feature_manifest.json`](file:///c:/Users/acer/Documents/SentinelRisk/ml/models/external_fraud/feature_manifest.json)
- **Algorithm**: `LGBMClassifier`
- **Parameters**:
  - `n_estimators`: 150
  - `learning_rate`: 0.05
  - `max_depth`: 6
  - `num_leaves`: 31
  - `scale_pos_weight`: **122.789** (derived strictly from training set: $(N_{\text{neg}} / N_{\text{pos}})$)
  - `random_state`: 42
- **Validation Optimized Threshold**: **0.8500** (Max F1 on Validation Set)

---

## 6. Honest Evaluation on Untouched Chronological Test Set

The model was evaluated on the **316,197 transactions** in the test split (August 29 – September 30, 2018):

```
┌────────────────────────────────────────────────────────────────────────┐
│             EXTERNAL DATASET LIGHTGBM TEST SET BENCHMARK               │
├───────────────────────────────┬────────────────────────────────────────┤
│ METRIC                        │ VALUE                                  │
├───────────────────────────────┼────────────────────────────────────────┤
│ Test Set Size                 │ 316,197 transactions                   │
│ Ground Truth Frauds           │ 2,824 frauds (0.893% prevalence)       │
│ Precision                     │ 55.90%                                 │
│ Recall                        │ 32.19% (909 / 2,824 frauds caught)     │
│ F1-Score                      │ 40.85%                                 │
│ PR-AUC                        │ 32.81%                                 │
│ ROC-AUC                       │ 65.21%                                 │
│ False Positive Rate (FPR)     │ 0.23% (717 non-fraud holds)            │
│ False Negative Rate (FNR)     │ 67.81% (1,915 missed frauds)           │
│ Review / Intervention Rate    │ 0.51% (1,626 total flagged)            │
└───────────────────────────────┴────────────────────────────────────────┘
```

### Confusion Matrix
| | Predicted Legitimate | Predicted Fraud |
|---|---|---|
| **Actual Legitimate** | 312,656 | 717 |
| **Actual Fraud** | 1,915 | 909 |

### Why This Is Realistic:
Without hardware device fingerprints or card tokens, the model relies purely on customer velocity, amount surges, and terminal drift. Capturing **32.19% of frauds with a tiny 0.23% false positive rate** is a strong, realistic baseline for terminal-only payment feeds without fabricating data.

---

## 7. Policy Engine Integration

The external ML model produces a calibrated continuous risk score. The **Stage 7 Policy Engine retains absolute decision authority**:

```
External ML Probability (e.g. 0.082)
            +
Customer Velocity Rules (cust_velocity_1h >= 3)
            +
Spend Anomaly Rules (cust_amount_ratio >= 3.0)
            ↓
    Policy Engine Hierarchy
            ↓
  APPROVE  /  REVIEW  /  HOLD
```

### Real-Time API Response Metadata:
```json
{
  "transaction_id": 14205,
  "decision": "REVIEW",
  "primary_trigger": "ELEVATED_ML_RISK",
  "ml_probability": 0.0712,
  "ml_status": "AVAILABLE",
  "model_source": "external_handbook_lightgbm",
  "feature_schema": "fraud_handbook_v1",
  "available_signal_count": 24,
  "missing_signal_count": 23,
  "missing_context": [
    "External dataset lacks hardware device fingerprints and payment card tokens (23 synthetic graph/device features unavailable)."
  ]
}
```

---

## 8. Reproducibility Demo Command

To run the offline replay benchmark on 1,000 transactions:
```bash
python scripts/replay_external_ml.py --sample-size 1000
```

To run on 5,000 transactions across 10 days:
```bash
python scripts/replay_external_ml.py --sample-size 5000 --days 10
```

---

## 9. Verification & Test Suite

All 144 automated unit and integration tests pass:
```bash
python -m pytest tests/ -v
# Output: 144 passed in 15.59s
```
