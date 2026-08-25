# SentinelRisk — Environment Bootstrap & Reproduction Guide

> Step-by-step instructions to reproduce SentinelRisk from a clean local environment without external API keys or cloud dependencies.

---

## 1. Prerequisites

- **Operating System**: Windows / macOS / Linux
- **Python**: Python 3.10, 3.11, or 3.12
- **Node.js**: Node 18+ and npm (for frontend dashboard)

---

## 2. Fast Setup (Single-Command Bootstrap)

```bash
# 1. Clone repository
git clone <repo-url>
cd SentinelRisk

# 2. Install Python backend dependencies
pip install -r backend/requirements.txt

# 3. Verify environment & bootstrap artifacts
python scripts/setup_demo.py
```

---

## 3. Running Demo Scenarios

Execute any of the deterministic demo scenarios via CLI:

```bash
# Legitimate Transaction (APPROVE)
python scripts/demo.py --scenario LEGITIMATE_TRANSACTION

# Account Takeover Attack (HOLD + ATO Investigation)
python scripts/demo.py --scenario ACCOUNT_TAKEOVER

# Coordinated Abuse Ring (HOLD + Graph Cluster Analysis)
python scripts/demo.py --scenario COORDINATED_ABUSE_RING

# Card Testing Velocity Burst (HOLD + Bot Rate-Limiting)
python scripts/demo.py --scenario CARD_TESTING

# Flagship "What Broke at 2 AM" Incident Simulation
python scripts/demo.py --scenario WHAT_BROKE_AT_2AM
```

---

## 4. Running the Web Dashboard

```bash
# Terminal 1: Start FastAPI backend
uvicorn backend.app.main:app --reload --port 8000

# Terminal 2: Start Next.js frontend
cd frontend
npm install
npm run dev
```

- **Frontend Console**: `http://localhost:3000`
- **Backend API & Swagger Docs**: `http://localhost:8000/docs`
- **Operations & Health Metrics**: `http://localhost:8000/metrics/operations`

---

## 5. Running the Complete Verification Suite

```bash
# 1. Run all 102 automated unit and integration tests
python -m pytest tests/ -v

# 2. Run in-process load benchmark (1,000 requests)
python scripts/load_test.py

# 3. Verify 100% decision replay reproducibility
python scripts/replay_risk.py --sample-size 500
```
