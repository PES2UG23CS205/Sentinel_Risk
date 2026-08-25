# SentinelRisk — Point-in-Time Feature Engineering & Leakage Prevention

> Production-style, leak-free feature engineering architecture for defensive transaction risk intelligence.

---

## 1. Core Principle: Zero Future Lookahead

In payment fraud detection, **temporal data leakage** is the single most common failure mode when transitioning models from offline benchmarks to production authorization engines. 

For a transaction evaluated at timestamp $T$:
```text
Transaction T
     │
     ├── Prior customer transactions (t < T)       ✅ ALLOWED
     ├── Prior merchant transactions (t < T)       ✅ ALLOWED
     ├── Prior device activity (t < T)             ✅ ALLOWED
     ├── Trailing 1h, 24h, 7d velocity [T-dt, T)   ✅ ALLOWED
     │
     ├── Current transaction in historical stats   ❌ LEAKAGE (Excluded)
     ├── Future transactions (t > T)               ❌ LEAKAGE (Forbidden)
     ├── Future disputes / chargebacks (t > T)     ❌ LEAKAGE (Forbidden)
     ├── Future fraud label confirmations          ❌ LEAKAGE (Forbidden)
     └── Final transaction outcome                 ❌ LEAKAGE (Forbidden)
```

SentinelRisk enforces this principle programmatically via a single-pass, stateful chronological pipeline where features are computed as-of strictly **BEFORE** the current transaction state is registered.

---

## 2. Feature Inventory

The pipeline computes **47 numerical and categorical risk features** across 6 distinct categories:

### A. Intrinsic Transaction Features (8 features)

| Feature | Definition | Time Window | Why It Matters | Leakage Risk |
|---|---|---|---|---|
| `amount` | Transaction value in INR | Instant ($T$) | Baseline transaction value | None (observed at authorization) |
| `amount_log` | $\ln(\text{amount} + 1)$ | Instant ($T$) | Normalizes heavy right-skew of amounts | None |
| `hour_of_day` | Hour of transaction (0–23) | Instant ($T$) | Identifies off-hour attacks (2 AM spikes) | None |
| `day_of_week` | Day of week (0=Mon ... 6=Sun) | Instant ($T$) | Captures weekend shopping patterns | None |
| `is_weekend` | 1 if Saturday or Sunday | Instant ($T$) | Distinguishes weekend transaction shifts | None |
| `is_night` | 1 if hour in [0, 5] (12 AM–6 AM) | Instant ($T$) | Strong signal for automated bot attacks | None |
| `merchant_category_idx` | Ordinal index of merchant category | Instant ($T$) | Captures category-specific risk profiles | None |
| `pi_type_idx` | Ordinal index of payment method (card, UPI, wallet) | Instant ($T$) | Identifies payment instrument risk vectors | None |

### B. Customer Historical Behavior (11 features)

| Feature | Definition | Time Window | Why It Matters | Leakage Risk |
|---|---|---|---|---|
| `cust_age_days` | $(T - \text{account\_created\_at})$ in days | Prior ($t < T$) | New accounts carry higher baseline risk | None |
| `cust_txn_count_prev` | Total prior transactions by customer | Prior ($t < T$) | Quantifies customer maturity & history | High if $t \ge T$ included |
| `cust_amount_sum_prev` | Total amount of prior transactions | Prior ($t < T$) | Measures historical customer spending | High if $t \ge T$ included |
| `cust_amount_mean_prev` | Average prior transaction amount | Prior ($t < T$) | Customer's baseline spending profile | High if future txns included |
| `cust_amount_std_prev` | Standard deviation of prior amounts | Prior ($t < T$) | Measures spending volatility | High if future txns included |
| `cust_amount_max_prev` | Maximum prior transaction amount | Prior ($t < T$) | Historical spending ceiling | High if future txns included |
| `cust_days_since_last_txn` | $(T - \text{last\_txn\_time})$ in days | Prior ($t < T$) | Identifies dormant accounts suddenly active | High if future txns included |
| `cust_amount_to_mean_ratio` | $\text{amount} / \max(1, \text{mean\_prev})$ | Prior ($t < T$) | Relative spending anomaly (ATO signal) | High if current txn in mean |
| `cust_amount_zscore` | $(\text{amount} - \text{mean}) / \text{std}$ | Prior ($t < T$) | Standardized anomaly score | High if current txn in stats |
| `cust_is_first_txn` | 1 if `cust_txn_count_prev == 0` | Prior ($t < T$) | Explicit cold-start indicator | High if future txns counted |
| `cust_decline_rate_prev` | Prior failed transactions / total count | Prior ($t < T$) | Customer friction / decline history | High if current status used |

### C. Trailing-Window Velocity Features (6 features)

| Feature | Definition | Time Window | Why It Matters | Leakage Risk |
|---|---|---|---|---|
| `velocity_txn_count_1h` | Customer transactions in $[T - 1\text{h}, T)$ | $[T - 1\text{h}, T)$ | Rapid card testing & credential stuffing | Extreme (current txn MUST be excluded) |
| `velocity_amount_sum_1h` | Customer spending in $[T - 1\text{h}, T)$ | $[T - 1\text{h}, T)$ | Rapid account draining (ATO burst) | Extreme |
| `velocity_txn_count_24h`| Customer transactions in $[T - 24\text{h}, T)$ | $[T - 24\text{h}, T)$ | Daily velocity spikes | Extreme |
| `velocity_amount_sum_24h`| Customer spending in $[T - 24\text{h}, T)$ | $[T - 24\text{h}, T)$ | Daily spending spikes | Extreme |
| `velocity_txn_count_7d` | Customer transactions in $[T - 7\text{d}, T)$ | $[T - 7\text{d}, T)$ | Weekly velocity surges | Extreme |
| `velocity_amount_sum_7d` | Customer spending in $[T - 7\text{d}, T)$ | $[T - 7\text{d}, T)$ | Weekly volume surge | Extreme |

### D. Merchant Dynamics & Context (9 features)

| Feature | Definition | Time Window | Why It Matters | Leakage Risk |
|---|---|---|---|---|
| `merchant_age_days` | $(T - \text{merchant\_created\_at})$ in days | Prior ($t < T$) | New merchant fraud / bust-out risk | None |
| `merchant_txn_count_prev` | Total prior transactions at merchant | Prior ($t < T$) | Merchant volume baseline | High if future txns included |
| `merchant_amount_mean_prev` | Average prior transaction value at merchant | Prior ($t < T$) | Merchant baseline AOV | High if current txn in mean |
| `merchant_amount_std_prev` | Std dev of prior amounts at merchant | Prior ($t < T$) | Merchant ticket dispersion | High if future txns included |
| `merchant_decline_rate_prev`| Prior decline rate at merchant | Prior ($t < T$) | Merchant terminal health & attacks | High if current status included |
| `merchant_velocity_txn_count_1h` | Merchant transactions in $[T - 1\text{h}, T)$ | $[T - 1\text{h}, T)$ | Target merchant attack burst | High if current txn included |
| `merchant_velocity_txn_count_24h`| Merchant transactions in $[T - 24\text{h}, T)$ | $[T - 24\text{h}, T)$ | 24-hour merchant traffic surge | High |
| `merchant_velocity_txn_count_7d` | Merchant transactions in $[T - 7\text{d}, T)$ | $[T - 7\text{d}, T)$ | 7-day merchant traffic surge | High |
| `amount_to_merchant_mean_ratio` | $\text{amount} / \max(1, \text{merch\_mean})$ | Prior ($t < T$) | Detects ₹50k ticket at ₹500 grocery store | High if current txn in mean |

### E. Device & Cross-Sharing Features (7 features)

| Feature | Definition | Time Window | Why It Matters | Leakage Risk |
|---|---|---|---|---|
| `device_txn_count_prev` | Total prior transactions on device | Prior ($t < T$) | Device history depth | High if future txns counted |
| `device_distinct_cust_prev` | Distinct customers seen on device before $T$ | Prior ($t < T$) | Multi-accounting & syndicate device sharing | High if future links counted |
| `device_distinct_merchants_prev` | Distinct merchants seen on device before $T$ | Prior ($t < T$) | Device merchant footprint | High |
| `device_velocity_count_24h` | Device transactions in $[T - 24\text{h}, T)$ | $[T - 24\text{h}, T)$ | Device bot velocity | High |
| `device_velocity_count_7d` | Device transactions in $[T - 7\text{d}, T)$ | $[T - 7\text{d}, T)$ | Device weekly activity | High |
| `device_is_new_for_cust` | 1 if customer never used device before $T$ | Prior ($t < T$) | Primary ATO trigger signal | Extreme (must only check past) |
| `device_age_days` | Days since device first seen before $T$ | Prior ($t < T$) | Device reputation maturity | High |

### F. Payment Instrument Features (6 features)

| Feature | Definition | Time Window | Why It Matters | Leakage Risk |
|---|---|---|---|---|
| `pi_txn_count_prev` | Total prior transactions on PI | Prior ($t < T$) | Instrument maturity | High if future txns counted |
| `pi_distinct_cust_prev` | Distinct customers using this PI before $T$ | Prior ($t < T$) | Stolen card sharing across syndicate accounts | High if future links counted |
| `pi_distinct_merchants_prev` | Distinct merchants using this PI before $T$ | Prior ($t < T$) | Card diversity | High |
| `pi_velocity_count_1h` | PI transactions in $[T - 1\text{h}, T)$ | $[T - 1\text{h}, T)$ | Primary Card Testing velocity signal | Extreme |
| `pi_velocity_count_24h` | PI transactions in $[T - 24\text{h}, T)$ | $[T - 24\text{h}, T)$ | 24-hour card velocity | Extreme |
| `pi_age_days` | Days since PI first observed before $T$ | Prior ($t < T$) | Card token age | High |

---

## 3. Cold-Start & Missing Value Strategy

In financial streams, cold-start cases (first customer transaction, first time at a new merchant, new device) are common and carry distinct risk profiles:

1. **First-Time Customer**:
   - `cust_txn_count_prev = 0`
   - `cust_is_first_txn = 1`
   - `cust_days_since_last_txn = -1.0` (sentinel value representing "no prior transaction")
   - `cust_amount_mean_prev = typical_amount` (from registration baseline)
   - `cust_amount_to_mean_ratio = 1.0`
   - `cust_amount_zscore = 0.0`
2. **Zero Standard Deviation**:
   - When a customer has $< 2$ prior transactions or constant amounts ($\text{std} = 0$), `cust_amount_zscore` defaults to `0.0` rather than throwing a division-by-zero or `NaN`.
3. **New Device / PI**:
   - `device_is_new_for_cust = 1`
   - `device_distinct_cust_prev = 0`
   - `pi_velocity_count_1h = 0`

---

## 4. Automated Leakage Verification & Deliberate Leakage Testing

SentinelRisk includes an automated verification engine in [`ml/features/leakage_checks.py`](file:///c:/Users/acer/Documents/SentinelRisk/ml/features/leakage_checks.py):

1. **Current Transaction Exclusion**: Asserts that all first-time transactions have strictly `0` velocity and historical counts.
2. **Future Dispute Isolation**: Asserts that no post-transaction dispute columns exist in the feature set.
3. **Target Isolation**: Asserts that ground-truth labels (`is_fraud`, `is_fraud_ground_truth`, `fraud_archetype`) are segregated and cannot be used as feature inputs.
4. **Temporal Monotonicity**: Asserts that cumulative counters (`cust_txn_count_prev`, `cust_amount_sum_prev`) are monotonically non-decreasing over time for all customers.
5. **Deliberate Leakage Catch Test**: Injects an artificial future lookahead feature (e.g. `future_dispute_status` or `fraud_score_target`) and verifies that the checker raises a `LeakageDetectedError` and halts execution.

---

## 5. Execution Commands

### Build Point-in-Time Features
```bash
python scripts/build_features.py
```
Outputs:
- `data/features/transaction_features.csv` (16.17 MB, 67,858 rows $\times$ 57 columns)
- `data/features/feature_metadata.json`

### Run Standalone Leakage Verification
```bash
python scripts/verify_leakage.py
```

### Run Feature Engineering Test Suite
```bash
python -m pytest tests/unit/test_feature_engineering.py -v
```
