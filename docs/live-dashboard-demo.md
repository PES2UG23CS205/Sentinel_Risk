# SentinelRisk — Live Operations Dashboard Demo Guide

> Step-by-step walkthrough for demonstrating the live real-time operations console, user CSV ingestion, live transaction feed, incident detection, and pre-loaded fraud scenarios.

---

## 1. Quick Start

1. Start the FastAPI backend:
   ```bash
   uvicorn backend.app.main:app --port 8000
   ```
2. Open the console in your browser:
   👉 **[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**

---

## 2. Step-by-Step Demo Script

### Step 1: Historical Benchmark Mode
- Click the **`📊 Frozen Synthetic Benchmark`** tab.
- **Story**: *"Here is our frozen 6-month synthetic payments benchmark. Across 67,858 transactions, the system achieved 99.72% fraud recall with 98.27% frictionless approval rate and 0.046 ms decision latency."*

### Step 2: My Data — Ingesting User CSV
- Click the **`📁 My Data (CSV Upload & Map)`** tab.
- Click **`📥 Load Built-in Sample (sample_transactions.csv)`** (or upload your own custom CSV).
- Click **`🔍 Parse Schema & Validate`**.
- Notice:
  - Automatic column mapping detects `transaction_id`, `timestamp`, `amount`, `customer_id`, etc.
  - Validation displays: `✓ 19 Valid Rows • 0 Invalid Rows`.
  - Preview table shows normalized rows.
- Click **`🚀 Ingest Dataset & Prepare Stream`**.

### Step 3: Real-Time Live Streaming & Authorization Feed
- Switch to the **`⚡ Real-Time Live Feed`** tab.
- Click **`▶ Start Stream`** (or **`🔄 Step Single`** for controlled frame-by-frame demonstration).
- Set speed to **`2x`** or **`5x`**.
- Watch:
  - Transactions stream into the **Live Authorization Feed** in real time.
  - Live session counters (`Processed`, `APPROVE`, `REVIEW`, `HOLD`) update dynamically.
  - The progress bar tracks stream position (`Progress: 12 / 19`).

### Step 4: Inspecting a High-Risk Event
- When a `🔴 HOLD` event appears in the feed (e.g. `TXN-USR-021` or `TXN-USR-026`):
  - Click the transaction in the feed.
  - Detail panel immediately displays:
    - **Decision Banner**: `🔴 HOLD` with primary policy trigger.
    - **Point-in-Time Risk Signals**: ML Probability (e.g. `98.5%`), Velocity count, Device novelty, Spend deviation ratio.
    - **Decision Reasoning**: Exact bullet triggers from the policy engine.
    - **AI Investigation Dossier**: Structured findings citing `[EVID-002]`, `[EVID-004]`, and grounded hypotheses.

### Step 5: Live Incident Surge Detection
- As the bot burst transactions (`TXN-USR-021` to `TXN-USR-025`) stream in:
  - An active red banner illuminates: **`⚡ INCIDENT DETECTED: CARD_TESTING_BOT_BURST`**.
  - Displays first-seen timestamp and affected transaction count.

### Step 6: Single Transaction Tester
- Click the **`🔍 Single Transaction Tester`** tab.
- Modify amounts or device tokens (e.g. ₹28,500 on novel device `DEV_UNRECOGNIZED_99`).
- Click **`⚡ Evaluate Transaction`** to observe instantaneous decisioning and dossier creation.

### Step 7: Clear Session Data
- Click **`🗑️ Clear`** in the stream controls bar to reset all live counters, state, and privacy buffers.
