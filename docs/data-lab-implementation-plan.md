# SentinelRisk — Data Lab & Real-World User Data Ingestion Architecture & Implementation Plan

## 1. Executive Summary & Objective
SentinelRisk Stages 1–15 established an authoritative, defense-oriented payment risk engine benchmarked against frozen synthetic and public Fraud Detection Handbook datasets. 

The **Data Lab** capability extends SentinelRisk into a self-service external risk assessment tool. It allows external risk officers, analysts, and hackathon judges to upload arbitrary transaction CSV datasets, automatically infer column schemas, inspect data quality, verify signal availability without feature fabrication, execute calibrated point-in-time risk scoring, explore interactive transaction-level decisions, and export auditable reports.

---

## 2. Core Architectural Guarantees & Constraints
1. **Zero Feature Fabrication**: If an uploaded dataset lacks device tokens, payment instrument IDs, or historical timestamps, the system **never** invents fake historical baseline averages, synthetic graph topologies, or dummy zeros to pretend full-signal ML inference occurred.
2. **Benchmark & Test Set Isolation**: User-uploaded data is strictly isolated in `data/user_assessments/` and **never** alters or contaminates frozen benchmarks (`data/benchmark/`, `evaluation/final/`, or `ml/models/`).
3. **No Automatic Model Retraining**: Uploaded data is evaluated in read-only inference mode; no unmonitored model drift or retraining is triggered.
4. **Policy Engine Authority**: Risk decisions (`APPROVE`, `CHALLENGE`, `REVIEW`, `HOLD`) are determined by the deterministic cost-sensitive policy engine and calibrated ML thresholds.
5. **Security & Input Sanitization**: Maximum file size enforcement (25 MB), filename sanitization, safe CSV parsing, no code execution, and secure data deletion (`DELETE /data-lab/{id}`).

---

## 3. Data Flow & Pipeline Architecture

```
User CSV Upload / Demo Dataset
              │
              ▼
┌─────────────────────────────────────────┐
│       1. Ingestion & Storage            │ (Sanitize filename, limit check,
│     data/user_assessments/{id}/         │  parse raw headers & rows)
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│     2. Automatic Column Detection       │ (Alias matching with confidence:
│       & Type Inference Engine           │  HIGH, MEDIUM, LOW, UNMATCHED)
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│    3. Interactive Column Mapping        │ (User overrides / field selection;
│       & Data Quality Validation         │  null %, duplicate IDs, timestamps)
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│    4. Signal Availability Matrix        │ (Honest categorization of 47 signals:
│       (Available vs Unavailable)        │  Available vs Unavailable + Rationale)
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│       5. Risk Assessment Engine         │
│  ┌──────────────────┬─────────────────┐ │
│  │ Mode A: Quick    │ Mode B: Replay  │ │ (Point-in-Time causality t < T,
│  │ Partial Signals  │ Full Topology   │ │  Calibrated ML & Policy Engine)
│  └──────────────────┴─────────────────┘ │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│      6. Interactive Results & Export    │ (Decision KPIs, Risk Distributions,
│    Filtered Table, CSV/JSON Download    │  Ground Truth Metrics if labeled)
└─────────────────────────────────────────┘
```

---

## 4. Component Structure

### 4.1 Backend (`backend/app/data_lab/`)
- `models.py`: Pydantic models for upload payloads, column mappings, validation reports, signal availability, assessment results, and transaction items.
- `column_detector.py`: Alias matching and confidence scoring (`transaction_id`, `timestamp`, `amount`, `customer_id`, `merchant_id`, `device_id`, `payment_instrument_id`, `currency`, `ip_address`, `is_fraud`).
- `validator.py`: Data quality checks (row counts, nulls, negative amounts, timestamp format standardization, sorting checks, ID deduplication).
- `signal_matrix.py`: Evaluates mapped fields and generates an explicit matrix of available signals (e.g. Velocity, Amount Deviation, Merchant History, Device Behavior, Graph Syndicate, Fraud Labels).
- `engine.py`: Assessment execution engine supporting Mode A (Quick Assessment) and Mode B (Historical Point-in-Time Replay).
- `storage.py`: Assessment persistence, isolated file storage, history index, and deletion.

### 4.2 REST API (`backend/app/api/data_lab.py`)
- `POST /data-lab/upload`: Handle file upload or demo dataset loading.
- `GET /data-lab/history`: List past user assessments.
- `GET /data-lab/example-dataset`: Download / inspect sample CSV.
- `GET /data-lab/{id}`: Fetch assessment state and mapping.
- `POST /data-lab/{id}/mapping`: Update column mappings and recalculate signal availability.
- `POST /data-lab/{id}/validate`: Re-run data validation.
- `POST /data-lab/{id}/run`: Run risk scoring pipeline.
- `GET /data-lab/{id}/results`: Get aggregate analytics, decision charts, and ground-truth metrics.
- `GET /data-lab/{id}/transactions`: Query paginated/filtered transactions.
- `GET /data-lab/{id}/export/csv`: Download scored transactions CSV.
- `GET /data-lab/{id}/export/json`: Download summary report JSON.
- `DELETE /data-lab/{id}`: Permanently remove assessment dataset.

### 4.3 UI Integration
- **FastAPI Operations Console (`backend/app/api/dashboard.py`)**:
  - Add `📥 Data Lab` tab with 8-step interactive flow (Upload $\to$ Validation $\to$ Mapping $\to$ Signal Matrix $\to$ Run Assessment $\to$ Decision KPIs $\to$ High-Risk Table & Inspector $\to$ Export & History).
  - Add Data Lab assessment summary card on Executive Overview.
- **Next.js Frontend (`frontend/src/app/data-lab/page.tsx`)**:
  - Standalone Next.js interface with dark operations theme.
  - Update `Sidebar.tsx` navigation.

### 4.4 Demo Data (`data/demo/user_upload_example.csv`)
- Anonymized 500-transaction CSV representing realistic e-commerce traffic with legitimate purchases, velocity bursts, card testing anomalies, and labeled ground truth.

---

## 5. Verification & Testing Plan
- **Automated Pytest Suite (`tests/unit/test_data_lab.py`)**:
  - Upload handling & size/type safeguards.
  - Automatic column detection & confidence assignment.
  - Manual column mapping overrides.
  - Signal availability calculation & feature honesty.
  - Mode A (Quick Assessment) on minimal CSV (Amount + Timestamp only).
  - Mode B (Historical Replay) on full-entity CSV.
  - Labeled dataset evaluation (Precision, Recall, F1) vs unlabeled handling.
  - Scored CSV export and assessment deletion.
  - Benchmark isolation check (frozen benchmark metrics unchanged).
- **End-to-End Test Execution**: Ensure 100% pass rate across existing 167 tests + all new Data Lab tests.
