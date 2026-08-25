# Fraud Detection Handbook Dataset Integration (Stage 11)

This document details the architectural integration of the simulated transaction dataset from the **Fraud Detection Handbook** into the SentinelRisk ecosystem.

---

## 1. Dataset Overview & File Format

- **Location**: `data/external/fraud_handbook/data/*.pkl`
- **Total Files**: 183 daily serialized Pandas DataFrame pickle (`.pkl`) files
- **Date Range**: `2018-04-01 00:00:31` to `2018-09-30 23:59:57` (6 full months)
- **Total Rows**: `1,754,155` simulated transactions
- **Ground Truth Fraud Count**: `14,681` transactions
- **Fraud Prevalence**: `0.836927%` (~0.84%)
- **Raw Schema**:
  1. `TRANSACTION_ID` (int64): Unique transaction identifier
  2. `TX_DATETIME` (datetime64[ns]): Exact transaction timestamp
  3. `CUSTOMER_ID` (int64 / str): Customer account identifier
  4. `TERMINAL_ID` (int64 / str): Merchant POS / online terminal identifier
  5. `TX_AMOUNT` (float64): Transaction authorization amount in EUR
  6. `TX_TIME_SECONDS` (int64): Elapsed seconds from dataset epoch
  7. `TX_TIME_DAYS` (int64): Elapsed days from dataset epoch
  8. `TX_FRAUD` (int64): Binary ground-truth label (`0` = legitimate, `1` = fraud)
  9. `TX_FRAUD_SCENARIO` (int64): Simulated fraud scenario archetype code (`0` to `3`)

---

## 2. Canonical Normalization & Provenance

External transactions are normalized into SentinelRisk's canonical `NormalizedTransaction` representation via `FraudHandbookLoader.normalize_row()`:

| Canonical Field | Source in External Dataset | Provenance & Handling |
|---|---|---|
| `transaction_id` | `TRANSACTION_ID` | Direct string cast |
| `timestamp` | `TX_DATETIME` | ISO-8601 string formatting (`YYYY-MM-DD HH:MM:SS`) |
| `amount` | `TX_AMOUNT` | Direct float cast (Currency: EUR) |
| `customer_id` | `CUSTOMER_ID` | Direct string cast |
| `terminal_id` | `TERMINAL_ID` | Stored in metadata |
| `merchant_id` | `f"TERM_{TERMINAL_ID}"` | **DERIVED COMPATIBILITY FIELD** |
| `device_id` | `"DEV_UNKNOWN"` | **DERIVED COMPATIBILITY FIELD** (Unprovided in raw schema) |
| `payment_instrument_id` | `f"PI_CUST_{CUSTOMER_ID}"` | **DERIVED COMPATIBILITY FIELD** (From Customer ID) |
| `ground_truth_fraud` | `TX_FRAUD` | **ISOLATED FOR EVALUATION ONLY** |
| `ground_truth_scenario` | `TX_FRAUD_SCENARIO` | **ISOLATED FOR EVALUATION ONLY** |

> [!IMPORTANT]
> **Zero Leakage & Ground Truth Isolation**:
> `TX_FRAUD` is strictly isolated. It is never fed into feature extraction, LightGBM inference, entity graphs, velocity counters, or policy engine rules. It is utilized purely post-decision to compute real-time evaluation metrics ($TP$, $FP$, $TN$, $FN$, Precision, Recall, F1).

---

## 3. Pipeline Component Compatibility & Honesty

SentinelRisk does **not** fabricate fake features or ML scores when external datasets lack fields. The pipeline honestly evaluates and reports component availability:

```
Point-in-Time Features (strictly t < T)
        ↓
ML Layer: UNAVAILABLE FOR EXTERNAL SCHEMA (Synthetic 47-feature LightGBM model)
        ↓
Graph Layer: UNAVAILABLE (No device fingerprinting tokens in raw schema)
        ↓
Velocity Rules: AVAILABLE (Point-in-time Customer & Terminal velocity)
        ↓
Behavioral Anomaly: AVAILABLE (Customer spending ratio & z-score)
        ↓
Policy Engine: ACTIVE (Deterministic rule-based evaluation)
        ↓
AI Investigation: AVAILABLE (Generated on REVIEW / HOLD)
```

---

## 4. Replay Architecture & Streaming

To avoid overwhelming browser memory with 1.75M rows, the dataset is loaded in manageable chronological slices (`--limit 1000`, `--limit 5000`, etc.) and streamed through `LiveSessionManager`.

### Replay Controls
- **Start**: Initiates real-time chronological processing loop.
- **Pause**: Suspends processing without resetting session state.
- **Stop**: Halts streaming.
- **Step Single**: Processes exactly one transaction with full telemetry.
- **Clear**: Resets in-memory rolling state and privacy buffers.
- **Speed**: Configurable playback multipliers ($1\times$, $2\times$, $5\times$, $10\times$).

---

## 5. External Replay Metrics

During external dataset replay, SentinelRisk calculates an isolated confusion matrix:
- **True Positives (TP)**: Ground Truth = Fraud AND Decision $\in \{\text{REVIEW}, \text{HOLD}\}$
- **False Positives (FP)**: Ground Truth = Legit AND Decision $\in \{\text{REVIEW}, \text{HOLD}\}$
- **True Negatives (TN)**: Ground Truth = Legit AND Decision = $\text{APPROVE}$
- **False Negatives (FN)**: Ground Truth = Fraud AND Decision = $\text{APPROVE}$

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad \text{F1} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

These metrics are labeled **EXTERNAL DATASET REPLAY METRICS** and are kept strictly distinct from the frozen Stage 5 & 7 synthetic benchmarks.

---

## 6. How to Run

### CLI Replay
```bash
# Replay 1,000 transactions
python scripts/replay_fraud_handbook.py --limit 1000

# Replay 5,000 transactions
python scripts/replay_fraud_handbook.py --limit 5000

# Replay specific date window
python scripts/replay_fraud_handbook.py --start-date 2018-04-01 --end-date 2018-04-05
```

### Web Operations Console
1. Start backend: `uvicorn backend.app.main:app --reload --port 8000`
2. Open `http://localhost:8000/dashboard`
3. Click the **📚 Fraud Detection Handbook** tab.
4. Click **⚡ Load 1,000 Transactions** and press **▶ Start Stream**.
