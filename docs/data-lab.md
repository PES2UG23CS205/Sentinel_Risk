# SentinelRisk — Data Lab & External Risk Assessment Studio

---

## 1. Overview & Core Purpose

The **SentinelRisk Data Lab** is a self-service, production-grade dataset ingestion and real-world payment risk assessment studio.

While earlier stages of SentinelRisk established authoritative benchmarks on frozen synthetic and public datasets (such as the *Fraud Detection Handbook*), the Data Lab enables operators, risk officers, and evaluation panels to:
1. **Upload arbitrary external transaction CSV datasets** (up to 25 MB).
2. **Automatically detect column headers and data types** with confidence scoring and alias matching.
3. **Interactively map or adjust canonical schema bindings**.
4. **Execute deep data quality validation** (detecting negative amounts, unparsable timestamps, duplicates, missing fields, and non-chronological sorting).
5. **Inspect the authoritative Signal Availability Matrix** under SentinelRisk's core **Zero Feature Fabrication Guarantee** (unavailable signals are never invented or substituted with synthetic zeros).
6. **Execute dual-mode risk assessment**:
   - **Mode A: Quick Partial-Signal Assessment** (calibrated scoring on partial-token schemas).
   - **Mode B: Full Historical Replay** (point-in-time sliding windows, device novelty, merchant profiling, and graph ring topology).
7. **Analyze multi-dimensional KPI results** (decision breakdown, financial exposure, amount at risk, and supervised ground-truth metrics if labeled).
8. **Explore and filter scored transactions** with a side **Transaction Signal Inspector Drawer** detailing available vs unavailable evidence and policy rationale.
9. **Export audit-ready scored CSVs and JSON summary reports**, and manage persistent assessment history with clean deletion.

---

## 2. Architectural Principles & Zero Feature Fabrication

```
   ┌──────────────────────────────────────────────────────────┐
   │            External CSV Upload / Demo Preset             │
   └────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ 1. Header Alias Detection & Type Inference Engine        │
   │    - Matches 10 canonical fields across 35+ alias patterns│
   │    - Assigns HIGH, MEDIUM, LOW, UNMATCHED confidence     │
   └────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ 2. Deep Data Quality Validator                          │
   │    - Standardizes timestamps & validates positive amounts│
   │    - Identifies duplicates, nulls, and chronological jumps│
   └────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ 3. Signal Availability Matrix (Zero Fabrication)         │
   │    - Classifies 8 signal families (Available vs Missing) │
   │    - Guarantees NO synthetic zeroes or fabricated values │
   └────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ 4. Dual-Mode Risk Assessment Engine                     │
   │    - Mode A: Quick Partial-Signal Assessment             │
   │    - Mode B: Full Historical Point-in-Time Replay        │
   │    - Cost-Sensitive Quad-State Policy (APPROVE/CHALLENGE/│
   │      REVIEW/HOLD) + Step-Up Challenge Orchestration      │
   └────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ 5. Isolated Persistence & Audit Trail                   │
   │    - Stored in data/user_assessments/{assessment_id}/   │
   │    - Frozen benchmarks remain strictly isolated          │
   └──────────────────────────────────────────────────────────┘
```

### The Zero Feature Fabrication Guarantee
In payment fraud prevention, fabricating unavailable features (e.g. inventing synthetic card IDs, hallucinating device fingerprints, or substituting dummy baseline ratios) is dangerous and invalidates risk scoring. 

SentinelRisk enforces transparent signal availability:
- If a dataset lacks `device_id`, the system tags device signals as **UNAVAILABLE**, sets device-derived features to neutral defaults without hallucinating novelty, and explicitly notes missing evidence in the policy decision rationale.
- If a dataset lacks `payment_instrument_id`, card velocity bursts are marked **UNAVAILABLE** and bypassed cleanly.
- If a dataset is unlabeled, ground-truth metrics (Precision, Recall, F1) display *"Ground Truth Unavailable"* rather than calculating fictitious metrics.

---

## 3. Canonical Field Mappings & Detection Aliases

SentinelRisk recognizes the following canonical fields:

| Canonical Field | Type | Requirement | Supported Aliases |
| :--- | :--- | :--- | :--- |
| `transaction_id` | String / Int | **Required** | `transaction_id`, `tx_id`, `txn_id`, `trans_id`, `id`, `order_id`, `payment_id`, `reference` |
| `timestamp` | Datetime / ISO | **Required** | `timestamp`, `tx_datetime`, `txn_time`, `created_at`, `trans_date_trans_time`, `datetime`, `date`, `time` |
| `amount` | Float / Numeric | **Required** | `amount`, `tx_amount`, `txn_amount`, `amt`, `payment_amount`, `value`, `total`, `price` |
| `customer_id` | String | Optional | `customer_id`, `cust_id`, `user_id`, `account_id`, `payer_id`, `buyer_id`, `client_id` |
| `merchant_id` | String | Optional | `merchant_id`, `merch_id`, `seller_id`, `vendor_id`, `receiver_id`, `merchant_name` |
| `device_id` | String | Optional | `device_id`, `device_fingerprint`, `dev_id`, `ip_address`, `client_ip`, `hardware_id` |
| `payment_instrument_id` | String | Optional | `payment_instrument_id`, `card_id`, `card_token`, `card_number`, `instrument_id`, `pan_token` |
| `currency` | String | Optional | `currency`, `currency_code`, `curr`, `ccy` (defaults to `INR`) |
| `is_fraud` | Binary (0 / 1) | Optional | `is_fraud`, `fraud_label`, `tx_fraud`, `target`, `label`, `is_anomaly`, `fraudulent` |

---

## 4. Assessment Modes

### Mode A: Quick Partial-Signal Assessment
- Designed for arbitrary or partial transaction exports that lack full entity tokens.
- Evaluates risk using genuinely available signals: ticket size distribution, off-hour timing, customer velocities (if available), and heuristic anomaly scoring.
- Extremely fast (evaluates 10,000 txns in under 1 second).

### Mode B: Full Historical Replay
- Designed for rich transaction exports containing customer, merchant, device, or card tokens.
- Reconstructs strict causal ($t < T$) historical state:
  - 1-hour and 24-hour sliding customer velocity windows
  - Rolling mean amount and spending deviation z-scores
  - 1-hour payment instrument velocity bursts
  - Device novelty detection and shared device velocity
  - Merchant transaction volume profiling and concentration risk
  - Entity graph bipartite syndicate ring scoring
- Dispatches through the quad-state cost-sensitive policy engine and step-up challenge orchestrator.

---

## 5. REST API Reference

The Data Lab provides a comprehensive REST API under `/data-lab`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/data-lab/upload` | Upload CSV dataset via multipart form-data (up to 25 MB) |
| `POST` | `/data-lab/upload-text` | Upload CSV dataset via JSON payload |
| `POST` | `/data-lab/demo-load` | 1-Click load of built-in 500-transaction demo dataset |
| `GET` | `/data-lab/example-dataset` | Download sample CSV template |
| `GET` | `/data-lab/history` | List all past user assessments and status |
| `GET` | `/data-lab/{id}` | Get assessment metadata, validation report, and signal matrix |
| `POST` | `/data-lab/{id}/mapping` | Update column mapping overrides and recalculate signals |
| `POST` | `/data-lab/{id}/validate` | Trigger manual data quality re-validation |
| `POST` | `/data-lab/{id}/run` | Execute Mode A or Mode B risk assessment |
| `GET` | `/data-lab/{id}/results` | Retrieve assessment analytics, KPI breakdown, and ground-truth metrics |
| `GET` | `/data-lab/{id}/transactions` | Query filterable, searchable scored transaction records |
| `GET` | `/data-lab/{id}/export/csv` | Download scored transactions with policy reasons and evidence tags |
| `GET` | `/data-lab/{id}/export/json` | Download JSON assessment summary and analytics report |
| `DELETE` | `/data-lab/{id}` | Permanently delete assessment and its uploaded data |

---

## 6. Security, Isolation & Safety

1. **Namespace Isolation**: All uploaded datasets, scored transaction logs, and metadata are saved strictly in `data/user_assessments/{assessment_id}/`.
2. **Benchmark Protection**: Frozen benchmark artifacts (`data/benchmark/`, `data/raw/synthetic/`, `evaluation/final/`) are read-only and never modified by Data Lab uploads.
3. **No Automatic Retraining**: User-uploaded data is evaluated strictly in inference mode; models are not automatically retrained on untrusted inputs.
4. **Defense-Only Simulation**: Step-up challenges and payment holds are simulated risk recommendations; no real 3DS blocking or payment network interference occurs.
