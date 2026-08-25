# SentinelRisk — 5–7 Minute Panel Demonstration Script

> Structured, timed demonstration script walking through problem statement, multi-layered architecture, real-time risk authorization, AI investigation, and 2 AM incident recovery.

---

## Demo Timeline Overview

| Timestamp | Segment | Key Demo Action / Screen | Talking Point |
|---|---|---|---|
| **0:00 – 0:45** | **The Payment Risk Trilemma** | Opening remarks / Architecture Diagram | Direct fraud loss vs. False decline friction vs. Analyst overload. Why rules alone miss 78% of fraud. |
| **0:45 – 1:30** | **Multi-Signal Architecture** | `docs/production-architecture.md` | Unified evaluation: ML probabilities + Graph link topology + Hard velocity overrides under a deterministic policy engine. |
| **1:30 – 2:30** | **Legitimate Flow (Frictionless)** | `python scripts/demo.py --scenario LEGITIMATE_TRANSACTION` | Approved in 0.05ms without human intervention (98.27% of volume). |
| **2:30 – 3:30** | **ATO & Bot Burst Detection** | `python scripts/demo.py --scenario ACCOUNT_TAKEOVER` | Instant `HOLD` on novel hardware + spending surge. AI agent creates grounded dossier with citations (`EVID-xxx`). |
| **3:30 – 4:30** | **Coordinated Syndicate Rings** | `python scripts/demo.py --scenario COORDINATED_ABUSE_RING` | Multi-account device sharing flagged by entity graph ring score (0.88), catching collusive rings invisible to single-txn models. |
| **4:30 – 5:30** | **Flagship: "What Broke at 2 AM?"** | `python scripts/demo.py --scenario WHAT_BROKE_AT_2AM` | Simulated bot attack replay: traffic spike, automatic containment recommendations, and incident recovery playbooks. |
| **5:30 – 6:30** | **AI Investigation & Analyst Queue** | Web Dashboard (`/review-queue`) | Structured findings, hypotheses with confidence levels, benign signal balancing, zero hallucination. |
| **6:30 – 7:00** | **Business Impact & Wrap-up** | `docs/business-impact.md` | ₹26.3k loss vs. ₹641k on rules (95.9% reduction), 108 automated tests, ready for panel Q&A. |

---

## Detailed Step-by-Step Execution

### Step 1: Open Terminal & Run Bootstrap Check
```bash
python scripts/setup_demo.py
```
*Voiceover*: "SentinelRisk is completely self-contained. All synthetic datasets, pre-computed point-in-time features, graph structures, and trained LightGBM models verify immediately."

### Step 2: Demonstrate Normal Daytime Authorization
```bash
python scripts/demo.py --scenario LEGITIMATE_TRANSACTION
```
*Voiceover*: "For legitimate daytime cardholders, authorization completes in sub-millisecond in-process time with zero customer friction."

### Step 3: Trigger High-Risk Account Takeover
```bash
python scripts/demo.py --scenario ACCOUNT_TAKEOVER
```
*Voiceover*: "When an attacker accesses a victim's account from a brand-new device token and attempts a ₹24,500 electronics purchase at 2 AM, the LightGBM model outputs a 0.985 calibrated fraud probability. The Stage 7 policy immediately freezes the transaction as a HOLD, and asynchronously hands off the context to our AI investigation layer."

### Step 4: Trigger Coordinated Syndicate Detection
```bash
python scripts/demo.py --scenario COORDINATED_ABUSE_RING
```
*Voiceover*: "Single-transaction ML models often miss collusive rings because individual transactions look moderate. But our heterogeneous entity graph identifies that 6 accounts share the same physical device token, triggering a severe ring score of 0.88 and stopping the syndicate."

### Step 5: Run Flagship "What Broke at 2 AM?" Replay
```bash
python scripts/demo.py --scenario WHAT_BROKE_AT_2AM
```
*Voiceover*: "During a sudden 2 AM bot attack, our incident simulator tracks the rapid escalation of risk signals, creates targeted investigation cases, and produces non-destructive containment recommendations (such as token-level CAPTCHA challenges) to restore baseline operations."
