# SentinelRisk — Authoritative Final System Architecture (Stages 1–15)

## 1. System Vision & Paradigm
**SentinelRisk** is an authoritative, defense-oriented payment risk operations platform designed for high-throughput acquiring environments (such as Razorpay). It combines point-in-time temporal feature engineering, continuous Machine Learning scoring (LightGBM), graph-topology syndicate detection, deterministic rule overrides, cost-sensitive policy triage, risk-based friction orchestration, evidence-grounded AI investigations, persistent fraud case operations, and merchant risk intelligence.

```
Incoming Authorization
        ↓
Schema Detection & Normalization (Synthetic 47-Signal vs External 24-Signal)
        ↓
Point-in-Time Feature Engineering (Strictly t < T, Zero Leakage)
        ↓
┌───────────────────┬───────────────────┬───────────────────┐
│  LightGBM (ML)    │  Entity Graph     │ Deterministic     │
│  P(Fraud)         │  Syndicates       │ Bot Rules         │
└───────────────────┴───────────────────┴───────────────────┘
                    ↓
        Quad-State Policy Engine (Stage 12)
                    ↓
┌──────────────┬──────────────┬──────────────┬──────────────┐
│   APPROVE    │  CHALLENGE   │    REVIEW    │     HOLD     │
│ (Friction-   │ (Automated   │   (Analyst   │  (Immediate  │
│    less)     │   Step-Up)   │    Queue)    │    Block)    │
└──────────────┴──────────────┴──────────────┴──────────────┘
                    ↓                              ↓
         Live Authorization Stream         Fraud Operations Center
                    ↓                              ↓
        Model & Feature Drift (PSI)        Analyst Feedback Loop
                    ↓                              ↓
        Merchant Risk Intelligence         Incident Command Center
```

---

## 2. Multi-Signal Defense Pipeline

### 2.1 Schema-Adaptive ML Inference
- **Primary Synthetic Pipeline**: 47 point-in-time behavioral signals evaluated by `primary_synthetic_lightgbm` ($p_{\text{fraud}} \in [0.0, 1.0]$).
- **External Handbook Pipeline**: 24 adapted features evaluated by `external_handbook_lightgbm` with schema detection and automatic routing.

### 2.2 Entity Graph Intelligence
- Heterogeneous bipartite graph linking Customers, Payment Instruments (Cards/UPI/Wallets), Hardware Devices, and Merchant Terminals.
- Computes connected component syndicate density ($\text{Ring Score} \in [0.0, 1.0]$) to intercept coordinated multi-accounting rings before chargebacks occur.

### 2.3 Cost-Sensitive Quad-State Policy
$$
\text{Precedence: } \text{Severe Rule/Syndicate HOLD} \succ \text{ML HOLD} \succ \text{Graph REVIEW} \succ \text{ML REVIEW} \succ \text{Step-Up CHALLENGE} \succ \text{APPROVE}
$$
- **HOLD**: Immediate authorization decline for high-confidence threats ($ML \ge 0.50$, $\text{Ring} \ge 0.80$, or velocity burst $\ge 5$).
- **REVIEW**: Queued for human analyst investigation ($ML \in [0.25, 0.50)$ or $\text{Ring} \in [0.50, 0.80)$).
- **CHALLENGE**: Automated step-up verification for mild anomalies ($ML \in [0.05, 0.25)$ or new device), saving $56.5\%$ in manual review costs.
- **APPROVE**: Instant, frictionless settlement for normal baseline traffic.

---

## 3. Fraud Operations Center & Analyst Feedback (Stage 13)
- **Persistent Case Management**: Database-backed review queue storing cases, immutable audit logs (`CASE_CREATED`, `CASE_ASSIGNED`, `NOTE_ADDED`, `INVESTIGATION_COMPLETED`, `CONFIRMED_FRAUD`, `FALSE_POSITIVE`), and analyst notes.
- **Deterministic Priority Triage**: Automated assignment of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` with recorded rationale.
- **Feedback Loop**: Collects validated human ground-truth (`CONFIRMED_FRAUD`, `FALSE_POSITIVE`, `LEGITIMATE`, `UNCERTAIN`) for model monitoring without unmonitored online auto-retraining.
- **Population Stability Index (PSI)**: Statistical monitoring of feature distributions (`amount`, `cust_velocity_1h`, `cust_amount_ratio`, `risk_score`) flagging shifts into `NORMAL` (<0.10), `WATCH` (0.10–0.25), and `DRIFT` (>0.25).

---

## 4. Merchant Risk Intelligence (Stage 14)
- **Point-in-Time Profiles**: Rolling window volume, GMV, chargeback rates, and trend trajectories (`IMPROVING`, `STABLE`, `DETERIORATING`).
- **Interpretable Risk Score**: Weighted score ($0.0 \text{ to } 1.0$) with explicit additive driver attributions:
  $$ \text{Score} = w_1 \cdot \text{FraudRate} + w_2 \cdot \text{VelocityAnomaly} + w_3 \cdot \text{InterventionDensity} + w_4 \cdot \text{Concentration} + w_5 \cdot \text{Trend} $$
- **Deterministic Alerting**: Intercepts `FRAUD_RATE_SPIKE`, `VELOCITY_SPIKE`, `RISK_SCORE_INCREASE`, `UNUSUAL_CUSTOMER_CONCENTRATION`, and `COORDINATED_ACTIVITY` recommending `MONITOR`, `REVIEW`, `ESCALATE` actions.

---

## 5. Operations Console & Command Center (Stage 15)
- **Unified 7-View Interface**: `OVERVIEW`, `LIVE TRANSACTIONS`, `FRAUD CASES`, `MERCHANT RISK`, `MODEL HEALTH`, `INCIDENTS`, and `BENCHMARKS`.
- **"What Broke at 2 AM" Simulation**: Replays multi-phase bot burst attacks, displaying real-time timeline, impact analysis, and actionable recovery playbooks.
