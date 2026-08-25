# SentinelRisk — Stage 8: Investigation Quality & Grounding Report

## 1. Quality & Grounding Benchmarks
- **Total Benchmark Cases Evaluated**: 4
- **Total Factual Findings Analyzed**: 8
- **Evidence Grounding Rate**: **100.00%**
- **Citation Correctness Rate**: **100.00%**
- **Hallucination Rate**: **0.00%** (0 unsupported citations)
- **Policy Decision Preservation**: **100.00%** (100% policy immutability)
- **Schema Validity**: **100.00%**

---

## 2. Benchmark Case Studies (All Archetypes)

### 1. Card Testing Attack Case (`BENCH-CARD-001`)
- **Flagged Trigger**: `RULE_SEVERE_PI_VELOCITY_BURST` (7 txns/hr on card) | **Decision**: `HOLD`
- **Primary Hypothesis**: Card Testing / Automated Velocity Attack.
- **Recommendations**: Rate-limit payment instrument `PI_STOLEN_88`, enforce CAPTCHA at checkout.

### 2. Account Takeover Case (`BENCH-ATO-002`)
- **Flagged Trigger**: `RULE_SEVERE_CUST_AMOUNT_ANOMALY` (5.4x mean spend) | **Decision**: `HOLD`
- **Primary Hypothesis**: Account Takeover (ATO): Unauthorized party on new device `DEV_ATTACKER_13`.
- **Recommendations**: Out-of-band customer verification, session revocation.

### 3. Coordinated Abuse Ring Case (`BENCH-RING-003`)
- **Flagged Trigger**: Graph Ring Score `0.85` | **Decision**: `HOLD`
- **Primary Hypothesis**: Coordinated Multi-Accounting Syndicate sharing `DEV_SHARED_RING_01` & `PI_SHARED_CARD_01`.
- **Recommendations**: Audit connected customer cluster in entity graph, inspect acquiring merchant terminals.

### 4. Legitimate Shared Household Device Case (`BENCH-LEGIT-004`)
- **Flagged Trigger**: Soft Review ($P=0.065$) | **Decision**: `REVIEW`
- **Primary Hypothesis**: Legitimate Activity (Shared household device with 2 users and normal spend).
- **Finding**: Correctly identified benign indicators, preventing confirmation bias.
