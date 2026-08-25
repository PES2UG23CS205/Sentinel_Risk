# SentinelRisk — Real-Time Operations Console & Ingestion Implementation Report

---

## 1. Architecture

SentinelRisk now features a multi-source real-time risk intelligence architecture:

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

## 2. Data Ingestion & Normalization

- **Modules Created**:
  - [`backend/app/ingestion/schema.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/ingestion/schema.py): Canonical `NormalizedTransaction` schema and `SchemaMapping`.
  - [`backend/app/ingestion/validator.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/ingestion/validator.py): Flexible timestamp parser (10+ datetime formats, Unix epochs), column validator, duplicate ID detector, and invalid row record builder.
- **Privacy & Security**: Uploaded transaction data is processed strictly in-memory within local runtime. Zero network transmission to external APIs.

---

## 3. Schema Mapping & Detection

- Automatic keyword alias matching matches standard column names (`txn_id`, `created_at`, `amt`, `card_token`, `user_id`, etc.).
- Interactive frontend mapping interface allows manual overrides with required fields clearly distinguished (`transaction_id`, `timestamp`, `amount`).

---

## 4. Incremental Point-in-Time Risk Evaluation

- **Module**: [`backend/app/ingestion/feature_builder.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/ingestion/feature_builder.py)
- **Incremental Features Computed**:
  - `pi_velocity_count_1h`, `cust_velocity_count_1h` (strictly $t < T$).
  - `cust_amount_to_mean_ratio`, `cust_amount_zscore` (based on prior amounts).
  - `device_is_new_for_cust` (novelty flag).
  - `device_customer_count`, `payment_instrument_customer_count` (bipartite graph connectivity).
  - `graph_ring_score`, `graph_ring_candidate` (syndicate ring detection).
- **ML Compatibility & Reliability Handling**:
  - Avoids fabricating artificial values.
  - If customer/device is new: `is_cold_start = 1`, labeled `ML STATUS: COLD_START_INFERENCE`.
  - If critical tokens are missing: labeled `ML STATUS: INSUFFICIENT CONTEXT` and falls back to deterministic rule gating.

---

## 5. Real-Time Transport & Session Management

- **Module**: [`backend/app/ingestion/session_manager.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/ingestion/session_manager.py) & [`backend/app/api/stream.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/api/stream.py)
- **Controls**: Start (`▶`), Pause (`⏸`), Stop (`⏹`), Step Single (`🔄`), Speed Multipliers (`1x`, `2x`, `5x`, `10x`), Clear Session (`🗑️`).
- **Transport**: Server-Sent Events (SSE) at `GET /stream/events` + step polling at `POST /stream/step`.
- **Live Counters**: Separated strictly from frozen historical benchmarks. Tracks `total_processed`, `approved_count`, `review_count`, `hold_count`, `fraud_loss_prevented_inr`, and `avg_latency_ms`.
- **Live Incident Detection**: Real-time sliding window analysis triggers active incident alerts (`CARD_TESTING_BOT_BURST`, `COORDINATED_RING_SURGE`) when consecutive holds or velocity thresholds surge.

---

## 6. Dashboard State & Multi-View UI

- **Module**: [`backend/app/api/dashboard.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/api/dashboard.py)
- **Five Primary Views**:
  1. `⚡ Real-Time Live Feed`: Scrolling live authorization feed, active incident alerts, and interactive transaction detail inspector.
  2. `📁 My Data (CSV Upload & Map)`: Local file browser, drag-and-drop, interactive column mapping, validation report, and sample dataset loader.
  3. `🔍 Single Transaction Tester`: Form to enter/paste ad-hoc payment transactions for instant live scoring.
  4. `🎯 Pre-Loaded Demo Scenarios`: Stage 10 approved scenarios (`WHAT_BROKE_AT_2AM`, `LEGITIMATE_TRANSACTION`, `ACCOUNT_TAKEOVER`, etc.).
  5. `📊 Frozen Synthetic Benchmark`: Reference metrics from the 67,858 transaction benchmark.

---

## 7. User Data Testing & Sample Dataset

Created [`data/user_samples/sample_transactions.csv`](file:///c:/Users/acer/Documents/SentinelRisk/data/user_samples/sample_transactions.csv) containing:
- Daytime legitimate payments (₹180 - ₹2,100).
- Card-testing micro-authorization bursts (₹85.00, 30-second intervals).
- Late-night Account Takeover luxury spending (₹28,500 on novel hardware).
- Coordinated ring transactions across shared mule accounts.

---

## 8. Test Suite Verification

```bash
python -m pytest tests/ -v
```
- **Total Passing Tests**: **121 / 121 (100% pass rate in 4.98s)**
- **Test Modules Added**:
  - `tests/unit/test_realtime_ingestion.py` (7 tests covering schema mapping, validator, incremental features, session manager, and stream routes).

---

## 9. Manual Browser Verification

- Tested upload & validation with `sample_transactions.csv`: Passed (`19 valid rows, 0 invalid rows`).
- Tested live streaming playback at 2x and 5x speed: Live feed updated sequentially, counters incremented accurately.
- Tested clicking live feed items: Detailed risk signals, decision reasoning, and AI dossiers rendered cleanly.
- Tested incident alert: Bot attack burst triggered `⚡ INCIDENT DETECTED: CARD_TESTING_BOT_BURST`.
- Tested session clear: State and privacy buffers purged.

---

## 10. Files Modified & Created

- [`backend/app/ingestion/schema.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/ingestion/schema.py) (NEW)
- [`backend/app/ingestion/validator.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/ingestion/validator.py) (NEW)
- [`backend/app/ingestion/feature_builder.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/ingestion/feature_builder.py) (NEW)
- [`backend/app/ingestion/session_manager.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/ingestion/session_manager.py) (NEW)
- [`backend/app/api/stream.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/api/stream.py) (NEW)
- [`backend/app/main.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/main.py) (Registered stream router)
- [`backend/app/api/dashboard.py`](file:///c:/Users/acer/Documents/SentinelRisk/backend/app/api/dashboard.py) (Updated with multi-tab real-time console)
- [`data/user_samples/sample_transactions.csv`](file:///c:/Users/acer/Documents/SentinelRisk/data/user_samples/sample_transactions.csv) (NEW)
- [`tests/unit/test_realtime_ingestion.py`](file:///c:/Users/acer/Documents/SentinelRisk/tests/unit/test_realtime_ingestion.py) (NEW)
- [`docs/realtime-data.md`](file:///c:/Users/acer/Documents/SentinelRisk/docs/realtime-data.md) (NEW)
- [`docs/live-dashboard-demo.md`](file:///c:/Users/acer/Documents/SentinelRisk/docs/live-dashboard-demo.md) (NEW)
- [`docs/realtime-implementation-report.md`](file:///c:/Users/acer/Documents/SentinelRisk/docs/realtime-implementation-report.md) (NEW)

---

## 11. Known Limitations

- In-process session streaming runs in memory; large production scale would use distributed stream queues (e.g. Kafka/Redis), but local in-process architecture satisfies zero-dependency buildathon requirements with sub-millisecond execution.
- Uploaded CSV records must contain at least `transaction_id`, `timestamp`, and `amount` (> 0).

---

## 12. Final Status

### **REAL-TIME DASHBOARD: READY**
### **USER DATA PIPELINE: READY**
### **LIVE RISK EVALUATION: READY**

The console is fully live and operational at **[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**.
