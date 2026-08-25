# SentinelRisk — AI Investigation Agent, Analyst Workflow & Incident Recovery

> Evidence-grounded, audit-ready AI investigation system for human fraud analysts and offline 2 AM incident response.

---

## 1. Executive Summary & Core Architectural Principle

In modern payment risk platforms:
1. **The Risk Engine Makes the Decision**: The Stage 7 deterministic Policy Engine evaluates ML probabilities, graph link analysis, and velocity rules to issue authoritative actions (`APPROVE`, `REVIEW`, `HOLD`).
2. **The LLM Is the Investigator**: The LLM gathers point-in-time evidence, reasons over multi-signal data, generates grounded hypotheses, and produces an auditable report for a human risk analyst.

> [!IMPORTANT]
> **Policy Immutability**: The LLM must **NEVER** alter a policy decision (e.g. changing `HOLD` to `APPROVE`), directly block/unblock transactions, or invent facts unsupported by evidence. The Stage 7 decision is legally authoritative; the LLM is strictly an evidence synthesizer.

---

## 2. End-to-End Architecture

```
                    ┌────────────────────────┐
                    │  Incoming Transaction  │
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ LightGBM ML   │       │ Entity Graph  │       │ Deterministic │
│ Probability   │       │ Ring Score    │       │ Rules         │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                                ▼
                ┌───────────────────────────────┐
                │  Stage 7 Policy Engine        │
                │  (sentinelrisk-policy-v1)     │
                └───────────────┬───────────────┘
                                │
            ┌───────────────────┴───────────────────┐
            │                                       │
            ▼                                       ▼
     ┌─────────────┐                         ┌─────────────┐
     │   APPROVE   │                         │REVIEW / HOLD│
     │  (98.27%)   │                         │   (1.73%)   │
     └─────────────┘                         └──────┬──────┘
                                                    │
                                                    ▼
                                     ┌─────────────────────────────┐
                                     │    Analyst Case Queue       │
                                     │      (CaseManager)          │
                                     └──────────────┬──────────────┘
                                                    │
                                                    ▼
                                     ┌─────────────────────────────┐
                                     │ Context & Evidence Builder  │
                                     │   (EVID-001, EVID-002, ...) │
                                     └──────────────┬──────────────┘
                                                    │
                                                    ▼
                                     ┌─────────────────────────────┐
                                     │   Investigation Agent       │
                                     │ (Mock / Gemini / OpenAI)    │
                                     └──────────────┬──────────────┘
                                                    │
                                                    ▼
                                     ┌─────────────────────────────┐
                                     │ Evidence-Grounded Report    │
                                     │ (Findings, Hypotheses, Recs)│
                                     └──────────────┬──────────────┘
                                                    │
                                                    ▼
                                     ┌─────────────────────────────┐
                                     │  Human Analyst Workflow     │
                                     │  (Review, Notes, Resolve)   │
                                     └─────────────────────────────┘
```

---

## 3. Evidence-First Design (`EVID-xxx`)

To eliminate hallucinations, the LLM is supplied with atomic, structured `EvidenceItem` objects:

```json
{
  "evidence_id": "EVID-002",
  "evidence_type": "ml_score",
  "source": "lightgbm_model",
  "timestamp": "2025-01-30 21:41:22",
  "value": 0.9995,
  "description": "Supervised LightGBM calibrated fraud probability is 0.9995."
}
```

### Supported Evidence Types:
- `transaction`: Transaction amount, merchant category, timestamp.
- `ml_score`: Supervised calibrated probability and feature contributions.
- `graph_topology`: Multi-customer device sharing, shared payment instruments, ring score.
- `velocity`: 1-hour and 24-hour transaction frequency on cards and accounts.
- `customer_baseline`: Historical mean spend ratio and Z-score.
- `device_novelty`: First-time device observations.
- `benign_indicator`: Evidence against fraud (e.g. 2-user household device, stable spend).

---

## 4. Structured Output Schema (`InvestigationReport`)

The agent outputs a validated structured object:
- **`findings`**: Specific factual assertions, each strictly citing supporting evidence IDs with classification (`SUPPORTED` or `INFERRED`).
- **`hypotheses`**: Multi-hypothesis reasoning (e.g. Account Takeover vs. Automated Bot Testing vs. Legitimate Household Sharing).
- **`suspicious_signals` vs. `benign_signals`**: Balanced dual-sided analysis preventing confirmation bias.
- **`uncertainty`**: Explicit documentation of what cannot be proven from evidence alone.
- **`recommended_next_steps`**: Actionable investigation guidance for human analysts.

---

## 5. Hallucination Safeguards & Policy Preservation

The `InvestigationAgent` enforces two programmatic assertions on every LLM response:
1. **Citation Validation**: Any evidence ID cited in a finding that does not exist in `InvestigationContext` is automatically stripped.
2. **Policy Preservation**: If the LLM attempts to alter `policy_decision`, the agent forcefully restores the Stage 7 decision.
3. **Prompt Injection Defense**: All user-controlled text fields are sanitized (`ContextBuilder.sanitize_text`), stripping instruction overrides (`ignore previous instructions`, `<script>`).

---

## 6. Investigation Quality & Grounding Benchmarks

Evaluated across representative benchmark cases for all fraud archetypes:

| Quality Metric | Measured Value | Operational Standard |
|---|:---:|---|
| **Evidence Grounding Rate** | **100.00%** | All findings strictly cite verified evidence items |
| **Citation Correctness** | **100.00%** | Zero broken or mismatched evidence references |
| **Hallucination Rate** | **0.00%** | Zero fabricated facts or unsupported claims |
| **Policy Decision Preservation** | **100.00%** | Authoritative Stage 7 decisions remain immutable |
| **Schema Validity Rate** | **100.00%** | Full compliance with `InvestigationReport` schema |

---

## 7. "What Broke at 2 AM" Incident Simulation

Simulates sudden risk anomalies and traces automated detection, case creation, and containment playbooks:

### Supported Scenarios:
1. **`CARD_TESTING_ATTACK`**: 02:00 AM bot attack — 20 rapid micro-transactions (₹75) on payment token `PI_BOT_99`. Intercepts 18 transactions (`HOLD`), generates 18 cases, and outputs velocity containment rules.
2. **`ACCOUNT_TAKEOVER_ATTACK`**: 02:15 AM credential stuffing — novel device `DEV_ATO_88` initiating ₹18,500 transactions on 5 established accounts. Intercepts all transactions, outputs 2FA step-up recommendations.
3. **`COORDINATED_RING_ATTACK`**: 02:30 AM syndicate — 6 accounts sharing `DEV_RING_77` and `PI_RING_66`. Intercepts syndicate, outputs cluster risk freeze playbook.
4. **`BASELINE`**: Normal diurnal legitimate payments traffic.

---

## 8. Execution Commands

```bash
# 1. Run "What broke at 2 AM" incident simulator
python scripts/simulate_incident.py --scenario CARD_TESTING_ATTACK

# 2. Run investigation quality evaluation suite
python scripts/evaluate_investigations.py

# 3. Investigate a specific flagged transaction
python scripts/run_investigation.py --transaction-id 2557

# 4. Run automated test suite (91 tests)
python -m pytest tests/ -v
```
