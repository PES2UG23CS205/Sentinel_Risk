# SentinelRisk — Real-Time Data Ingestion & Live Streaming Architecture

> Technical reference for user data ingestion, schema normalization, point-in-time feature extraction, real-time transport, and session lifecycle management.

---

## 1. Architectural Overview

```
                          ┌──────────────────────────┐
                          │      DATA SOURCES        │
                          ├──────────────────────────┤
                          │ Existing Synthetic Data  │
                          │ User CSV / JSON Upload   │
                          │ Live Transaction Stream  │
                          │ Pre-Loaded Demo Scenarios│
                          └────────────┬─────────────┘
                                       ↓
                          Transaction Normalization
                                       ↓
                          Point-in-Time Features (t < T)
                                       ↓
                       ┌───────────────┼───────────────┐
                       ↓               ↓               ↓
                    LightGBM         Graph          Rules
                       └───────────────┼───────────────┘
                                       ↓
                                Policy Engine
                                       ↓
                          APPROVE / REVIEW / HOLD
                                       ↓
                             Investigation Agent
                                       ↓
                             Live Risk Dashboard
```

---

## 2. Ingestion & Canonical Schema

SentinelRisk normalizes arbitrary tabular data sources into a strictly validated internal schema:

```json
{
  "transaction_id": "TXN-USR-001",
  "timestamp": "2025-07-01 09:15:00",
  "amount": 450.00,
  "currency": "INR",
  "customer_id": "CUST_ANANYA_01",
  "merchant_id": "MERCH_GROCERY_01",
  "device_id": "DEV_PHONE_01",
  "payment_instrument_id": "PI_CARD_01",
  "metadata": {}
}
```

### Supported CSV / JSON Column Mappings & Aliases

The system automatically detects and maps external column names using fuzzy keyword heuristics:

| Canonical Field | Type | Mandatory? | Common Inferred Aliases |
|---|---|:---:|---|
| `transaction_id` | `str \| int` | **YES** | `txn_id`, `id`, `tx_id`, `trans_id`, `payment_id`, `reference_id` |
| `timestamp` | `str` (ISO / SQL) | **YES** | `timestamp`, `time`, `date`, `created_at`, `txn_time`, `datetime` |
| `amount` | `float` (> 0) | **YES** | `amount`, `value`, `amt`, `price`, `txn_amount`, `total`, `volume` |
| `customer_id` | `str \| int` | No (Default: UNKNOWN) | `customer_id`, `user_id`, `cust_id`, `buyer_id`, `client_id`, `account_id` |
| `merchant_id` | `str \| int` | No (Default: UNKNOWN) | `merchant_id`, `merch_id`, `seller_id`, `vendor_id`, `store_id`, `terminal_id` |
| `device_id` | `str \| int` | No (Default: UNKNOWN) | `device_id`, `dev_id`, `hardware_id`, `fingerprint`, `ip_address` |
| `payment_instrument_id` | `str \| int` | No (Default: UNKNOWN) | `payment_instrument_id`, `card_token`, `pi_id`, `instrument_id`, `card_id` |

---

## 3. Incremental Point-in-Time Feature Builder

When incoming transactions arrive in a stream, SentinelRisk calculates point-in-time safe ($t < T$) features on the fly without recomputing the entire historical database:

1. **Velocity Features**:
   - `pi_velocity_count_1h`: Number of transactions on `payment_instrument_id` in prior 60 minutes.
   - `cust_velocity_count_1h`: Number of transactions on `customer_id` in prior 60 minutes.
2. **Behavioral Deviations**:
   - `cust_amount_to_mean_ratio`: Ratio of current amount to customer's historical mean.
   - `cust_amount_zscore`: Standardized deviation from customer's spending baseline.
   - `device_is_new_for_cust`: 1 if the customer has never used this device token before.
3. **Graph Ring Density**:
   - Evaluates bipartite degrees: `device_customer_count` and `payment_instrument_customer_count`.
   - Ring score triggers $\ge 0.40$ if $\ge 2$ accounts share both device and card tokens.
4. **Cold-Start Handling & ML Reliability**:
   - If a customer or device is brand new, `is_cold_start = 1` is recorded and default ratios ($1.0\times$) are assigned.
   - If required entity identifiers are missing, the system labels `ML STATUS: INSUFFICIENT CONTEXT` and relies on fallback rules and velocity thresholds.

---

## 4. Streaming & Transport Architecture

SentinelRisk supports live stream playback:
- **Server-Sent Events (SSE)**: `GET /stream/events` streams evaluation events to browser clients in real time.
- **REST Stepping**: `POST /stream/step` allows deterministic frame-by-frame evaluation.
- **Speed Multipliers**: Supports `1x`, `2x`, `5x`, `10x` playback replay.
- **Incident Detection**: Sliding 10-transaction window continuously monitors hold rates and velocity bursts, triggering active incident alerts when anomalies surge.

---

## 5. Local Privacy & Session Isolation

- **Zero External Egress**: Uploaded datasets remain 100% in-process within local memory and are never transmitted to external APIs.
- **Session Reset**: `POST /stream/clear` purges all in-memory buffers and state.
- **Benchmark Integrity**: Historical benchmark metrics (`67,858` transactions, `99.72%` recall) are completely isolated from temporary user sessions.
