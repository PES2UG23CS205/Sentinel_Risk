# SentinelRisk — Authoritative Final Panel Demo Script

## Overview
This document provides the exact step-by-step presentation narrative and terminal/UI walk-through for demonstrating **SentinelRisk** to an executive judging panel (e.g. Razorpay Hackathon / Risk Panel).

---

## 1. Executive Opening (1 Minute)
> "Good morning, panel. Modern payment gateways face a fundamental trade-off: stopping sophisticated, multi-accounting fraud syndicates without introducing unnecessary friction for legitimate high-value customers. SentinelRisk is a defense-only, real-time risk intelligence and fraud operations platform. It evaluates point-in-time behavioral signals across LightGBM ML, graph syndicate topologies, deterministic bot rules, and a quad-state policy engine."

---

## 2. Master CLI Execution
Run the automated end-to-end master demonstration:
```bash
python scripts/final_demo.py
```

### Script Narrative Flow:
1. **Step 1: Normal Legitimate Payment**
   - *Show*: Standard ₹450 checkout at grocery store.
   - *Outcome*: Frictionless `APPROVE` with sub-millisecond ($<0.05 \text{ ms}$) latency.
2. **Step 2: Mild Anomaly / Unrecognized Device (Stage 12 Innovation)**
   - *Show*: ₹3,200 payment on new phone token ($ML \in [0.05, 0.25)$).
   - *Outcome*: Automated `CHALLENGE` (`CHALLENGE_DEVICE_VERIFICATION`).
   - *Panel Point*: Avoids the ₹50 manual analyst review queue while preventing user abandonment.
3. **Step 3: Account Takeover Surge**
   - *Show*: Late-night ₹48,500 luxury spend from new IP/device ($7.5\times$ historical mean).
   - *Outcome*: Immediate `HOLD` ($ML = 0.985$).
4. **Step 4: Card Testing Bot Burst**
   - *Show*: 8 rapid micro-authorizations testing stolen BINs within 1 hour.
   - *Outcome*: Immediate `HOLD` via deterministic velocity override.
5. **Step 5: Coordinated Abuse Ring (Stage 6 Graph)**
   - *Show*: Collusive ring sharing hardware devices and cards across 6 customer accounts.
   - *Outcome*: Immediate `HOLD` on $\text{Graph Ring Score} = 0.88$.
6. **Step 6: Evidence-Grounded AI Investigation Agent**
   - *Show*: Structured LLM dossier with cited atomic evidence IDs (`EVID-003`) and zero hallucinations.
7. **Step 7: Persistent Fraud Operations Center & Feedback Loop (Stage 13)**
   - *Show*: Case assignment to analyst, note attachment, and formal `CONFIRMED_FRAUD` resolution recording ground-truth feedback.
8. **Step 8: Merchant Risk Intelligence (Stage 14)**
   - *Show*: Deterministic weighted merchant risk score ($0.95 \text{ HIGH}$) with additive driver attributions and active anomaly alerts.
9. **Step 9: Incident Command Center ("What Broke at 2 AM?")**
   - *Show*: Real-time replay of 2:00 AM card testing attack with 18 automated holds and containment playbook.
10. **Step 10: Statistical Model/Data Drift Monitoring (Stage 13)**
    - *Show*: Population Stability Index (PSI) feature table detecting real distribution shifts.
11. **Step 11: Authoritative Benchmark Comparison**
    - *Show*: Frozen 10,179 synthetic test set ($98.47\%$ recall, $36.8\%$ cost reduction) and 316,197 Fraud Handbook replay ($29.1\%$ cost reduction).

---

## 3. UI Dashboard Walkthrough (http://localhost:8000/dashboard)
- **🏛️ Executive Overview**: Live financial loss prevented counter, approval/challenge/review/hold distribution.
- **⚡ Live Authorization Feed**: Real-time event streaming with step-up challenge badges and signal inspectors.
- **🔍 Fraud Operations Center**: Kanban case queue, analyst assignment, notes, and feedback metrics.
- **🏢 Merchant Risk Intelligence**: Merchant rankings, risk drivers breakdown, and alert management.
- **📈 Model Health**: Live PSI drift monitoring across feature distributions.
- **🚨 Incident Center**: Single-click "What Broke at 2 AM" incident replay and recovery timeline.
- **📊 Authoritative Benchmarks**: Side-by-side comparison across all system tiers.
