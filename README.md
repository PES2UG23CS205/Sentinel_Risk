# SentinelRisk — Interpretable Payment Risk Intelligence & Decision Engine

> A production-ready, multi-layered payment risk intelligence platform combining point-in-time machine learning, heterogeneous entity graph analytics, cost-sensitive policy execution, step-up risk challenges, and evidence-grounded AI investigation.

---

## 1. Project Overview & Problem Statement

Payment gateways and checkout infrastructures face a fundamental **trilemma**:
1. **Prevent Direct Financial Loss**: Stop card-not-present (CNP) fraud, account takeovers (ATO), rapid velocity bursts, and collusive fraud rings.
2. **Minimize Legitimate Customer Friction**: Avoid insulting genuine users with false-positive declines that destroy checkout conversion rates.
3. **Control Operational Analyst Burden**: Prevent millions of transactions from overwhelming manual investigation queues.

Traditional rule-based systems stop only **~21%** of fraudulent transactions while generating massive false alarm floods. Conversely, naive black-box AI models introduce regulatory risk, latency bottlenecks, and opaque decisions.

**SentinelRisk** solves this by establishing a deterministic, multi-layered risk perimeter that delivers sub-millisecond evaluation latency, 98.47% fraud recall, and a 36.8% reduction in expected business costs.

---

## 2. System Architecture

```
                    PAYMENT AUTHORIZATION REQUEST
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │     API Gateway / Risk    │ (Validation, SHA-256 Input Hash,
                    │     POST /risk/evaluate   │  Idempotency Check, Correlation ID)
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    Online Feature Store   │ (Point-in-time state t < T,
                    │   & Context Layer (<1ms)  │  Velocity counters, Baselines)
                    └─────────────┬─────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
 ┌─────────────────────┐┌─────────────────────┐┌─────────────────────┐
 │  LightGBM Inference ││  Entity Graph Engine││ Deterministic Rules │
 │ Calibrated P(Fraud) ││  Ring Score & Cand  ││ Velocity Burst & ATO│
 └──────────┬──────────┘└──────────┬──────────┘└──────────┬──────────┘
            │                      │                      │
            └─────────────────────┼──────────────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │   Stage 12 Policy Engine  │ (sentinelrisk-policy-v1,
                    │   Precedence Hierarchy    │  Quad-state risk-based friction)
                    └─────────────┬─────────────┘
                                  │
             ┌──────────────┬─────┴──────┬──────────────┐
             │              │            │              │
             ▼              ▼            ▼              ▼
      ┌─────────────┐┌─────────────┐┌─────────────┐┌─────────────┐
      │   APPROVE   ││  CHALLENGE  ││   REVIEW    ││    HOLD     │
      │  (96.74%)   ││   (1.16%)   ││   (0.83%)   ││   (1.28%)   │
      │Zero Friction││Auto Step-Up ││Human Analyst││  Immediate  │
      └─────────────┘└─────────────┘└──────┬──────┘└──────┬──────┘
                                           │              │
                                           ▼              ▼
                                    ┌─────────────────────────────┐
                                    │    Analyst Review Queue     │
                                    │        (CaseManager)        │
                                    └──────────────┬──────────────┘
                                                   │
                                                   ▼
                                    ┌─────────────────────────────┐
                                    │    AI Investigation Agent   │
                                    │ (Asynchronous Evidence Rpt) │
                                    └─────────────────────────────┘
```

---

## 3. Main Capabilities

- **Point-in-Time Stateful Machine Learning (LightGBM)**: Calibrated tabular risk model trained on 47 point-in-time features with zero data leakage ($t < T$).
- **Heterogeneous Entity Graph Intelligence**: Identifies collusive multi-account syndicates and shared-device/card abuse ($100\%$ case recall on 15/15 rings).
- **Stage 12 Quad-State Policy Engine**: Executes deterministic precedence hierarchy (`APPROVE`, `CHALLENGE`, `REVIEW`, `HOLD`) with dynamic step-up challenges (OTP, 3DS, Biometric).
- **Evidence-Grounded AI Investigation Agent**: Synthesizes atomic evidence tags (`[EVID-xxx]`) into auditable dossiers with strict decision immutability.
- **"What Broke at 2 AM?" Incident Simulator**: Replays realistic merchant-level attacks, pinpoints root causes, and recommends containment playbooks.
- **Merchant Risk Profiling & PSI Drift Monitoring**: Tracks merchant chargeback rates and model population stability index (PSI) in real time.
- **Real-Time Live Ingestion & Replay**: High-throughput asynchronous streaming supporting both synthetic and external benchmark data.

---

## 4. Technology Stack

| Layer | Technologies |
|---|---|
| **Backend & API** | Python 3.10+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy, SQLite |
| **Machine Learning & Graph** | LightGBM, Scikit-learn, Pandas, NumPy, SciPy, NetworkX, Joblib |
| **Frontend & UI** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS / Vanilla CSS |
| **AI / LLM Integration** | Deterministic Mock LLM Provider (zero-cost) + Google Gemini API Provider |
| **Testing & Quality** | Pytest, HTTPX, Load Testing Harness |

---

## 5. Authoritative Benchmark Results

Evaluated on **10,179 held-out synthetic test transactions** and **316,197 external Fraud Detection Handbook transactions**:

| Risk Defense Layer | Decision Output | Fraud Recall | Review Rate | Hold Rate | Total Expected Cost | Key Benefit |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Stage 4 Rules Baseline** | Binary (`APPROVE`/`REVIEW`) | 21.37% | 0.62% | 0.00% | ₹641,079.22 | Baseline |
| **Stage 5 LightGBM Model** | Continuous Probability | 98.47% | 1.30% | 0.00% | ₹16,255.32 | High Recall |
| **Stage 7 Policy Engine** | Tri-State (`APPROVE`/`REVIEW`/`HOLD`) | 98.47% | 1.90% | 1.28% | ₹48,055.32 | Baseline Tri-State |
| **Stage 12 Policy Engine** | **Quad-State (+ `CHALLENGE`)** | **98.47%** | **0.83%** | **1.28%** | **₹30,385.32** | **36.8% Cost Savings & 56.5% Less Analyst Load** |

---

## 6. Dataset Information & Zero-Leakage Guarantee

SentinelRisk supports two benchmark data streams:

1. **Synthetic Multi-Archetype Dataset** (`data/generated/`):
   - 50,000+ generated transactions covering legitimate consumers, velocity spikes, card testing, account takeovers, and collusive fraud rings.
   - Strictly pre-computed point-in-time features (`data/features/`).
2. **External Fraud Detection Handbook Benchmark** (`data/external/fraud_handbook/`):
   - 1.75M simulated transactions across 183 daily batches from the ULB Machine Learning Group benchmark.
   - Raw binary `.pkl` files are excluded from Git to keep the repository lightweight; download anytime with `python scripts/download_fraud_handbook.py`.

> **Zero Data Leakage Guarantee**: Ground-truth labels (`TX_FRAUD`) are strictly isolated for post-decision evaluation. Features are computed strictly over past timestamps ($t < T$).

---

## 7. Installation & Quick Start

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher & npm

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/SentinelRisk.git
cd SentinelRisk

# 2. Set up Python virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Install frontend dependencies
cd frontend
npm install
cd ..

# 5. Initialize database and verify environment
python scripts/setup_demo.py
```

---

## 8. Running the Application

### Start Backend API Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- **REST API Docs (Swagger UI)**: `http://localhost:8000/docs`
- **Health Probes**: `http://localhost:8000/health`

### Start Frontend Dashboard
```bash
cd frontend
npm run dev
```
- **Web Operations Console**: `http://localhost:3000`
- Navigation routes:
  - `/` — Live Risk Evaluation Dashboard & Stream Replay
  - `/incidents` — "What Broke at 2 AM?" Incident Simulator
  - `/review-queue` — Analyst Case Management & Human-in-the-Loop
  - `/operations` — System Health & Operational Latency Probes

---

## 9. Running Tests & Demonstrations

### Automated Test Suite
SentinelRisk features **167 automated unit, integration, and contract tests (100% passing)**:
```bash
python -m pytest tests/ -v
```

### Master Final Demo (11-Step Panel Walkthrough)
```bash
python scripts/final_demo.py
```

### Load & Latency Test
```bash
python scripts/load_test.py
```

### Replay External Benchmark Data
```bash
python scripts/replay_fraud_handbook.py --limit 1000
```

---

## 10. Important Disclaimer

> [!IMPORTANT]
> **Defensive Research & Prototype Disclaimer**:
> SentinelRisk is an independent, defense-oriented payment risk intelligence engine and research prototype built for evaluation and demonstration using synthetic and open-source benchmark datasets. It is **not** affiliated with, nor does it connect to, live Razorpay production payment rails or banking APIs.

---

## 11. Authoritative Documentation Suite

- [docs/final-completion-report.md](docs/final-completion-report.md) — Authoritative final completion report (Stages 1–15)
- [docs/final-architecture.md](docs/final-architecture.md) — Complete final system architecture manual
- [docs/final-demo-script.md](docs/final-demo-script.md) — Step-by-step panel rehearsal script & master narrative
- [docs/risk-based-friction.md](docs/risk-based-friction.md) — Stage 12 Quad-State policy architecture & challenge catalog
- [docs/external-dataset-ml.md](docs/external-dataset-ml.md) — Schema-adaptive ML pipeline & external dataset integration
- [docs/production-architecture.md](docs/production-architecture.md) — Resilience, failure matrix & scaling blueprint
- [docs/business-impact.md](docs/business-impact.md) — Cost tradeoffs & financial loss analysis
- [docs/panel-defense.md](docs/panel-defense.md) — Top 25 Razorpay panel technical answers

---

## 12. License & Submission

Feature-complete payment risk intelligence engine — Built for technical panel evaluation.
Feature development is **FROZEN**.

