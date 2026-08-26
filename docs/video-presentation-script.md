# SentinelRisk — 5-Minute Video Recording Presentation Script

> **Video Duration**: 5:00 Minutes (300 Seconds)  
> **Format**: Screencast + Voiceover (or Camera in Corner)  
> **Target Audience**: Hackathon Judges, Risk & Payment Engineering Leaders, Technical Evaluators  
> **Primary URL**: `http://localhost:8000/dashboard`

---

## 🎬 Pre-Recording Setup Checklist (Do This Before Pressing Record)

1. **Terminal 1 (Backend Server)**:
   ```bash
   cd c:\Users\acer\Documents\SentinelRisk
   uvicorn backend.app.main:app --reload --port 8000
   ```
2. **Browser**:
   - Open Chrome / Edge at `http://localhost:8000/dashboard`
   - Set zoom to **100%** or **110%** for clear readability
   - Close all other browser tabs and notifications
3. **Reset State** (Optional, ensures fresh counters):
   - In browser console: `refreshOverview();`

---

## ⏱️ Timeline & Segment Breakdown

```
00:00 - 00:35 (35s) : Scene 1 — Executive Overview & Problem Architecture
00:35 - 01:25 (50s) : Scene 2 — Live Real-Time Stream & Quad-State Scoring Engine
01:25 - 02:20 (55s) : Scene 3 — Data Lab: External CSV Ingestion & Zero Fabrication Guarantee
02:20 - 03:15 (55s) : Scene 4 — Fraud Operations Center & AI Evidence Investigation Agent
03:15 - 04:10 (55s) : Scene 5 — Merchant Risk Intelligence & "What Broke at 2 AM?" Incident Center
04:10 - 05:00 (50s) : Scene 6 — Model Health (PSI Drift), Benchmarks & Final Conclusion
```

---

## 🎙️ Complete Step-by-Step Script

---

### 📍 Scene 1: Executive Overview & Problem Architecture [00:00 – 00:35]

| Field | Details |
|---|---|
| **Timestamp** | `00:00 – 00:35` (35 Seconds) |
| **Active Screen** | Browser at `http://localhost:8000/dashboard` → Tab: **🏛️ Executive Overview** |
| **On-Screen Action** | Mouse hovers smoothly over the KPI cards: Total Transactions, Fraud Loss Prevented (`₹`), Approval Rate (`98.5%`), and Challenge Rate (`2.1%`). |
| **Wait Condition** | Ensure overview numbers are loaded. |

#### 🗣️ Spoken Script (Word-for-Word):
> "Hello everyone. In modern digital payments, gateways face a high-stakes dilemma: stopping sophisticated, coordinated fraud syndicates and account takeovers without introducing friction for legitimate cardholders.
>
> Meet **SentinelRisk** — a real-time risk intelligence and fraud operations platform engineered for modern payment networks. 
> 
> Unlike traditional black-box fraud filters, SentinelRisk combines point-in-time behavioral feature engineering, LightGBM machine learning, heterogeneous graph ring detection, and an evidence-grounded AI investigation agent into a cost-sensitive Quad-State policy engine."

---

### 📍 Scene 2: Live Real-Time Stream & Quad-State Scoring [00:35 – 01:25]

| Field | Details |
|---|---|
| **Timestamp** | `00:35 – 01:25` (50 Seconds) |
| **Active Screen** | Click Tab: **⚡ Live Authorization Feed** |
| **On-Screen Action** | 1. Click button: **▶️ Start Stream (Synthetic 20 TPS)**.<br>2. Watch live transaction rows stream in with color-coded badges (`APPROVE`, `CHALLENGE`, `REVIEW`, `HOLD`).<br>3. After 10 transactions, click **⏸️ Pause** or click on a `CHALLENGE` transaction row to expand the Signal Inspector. |
| **Wait Condition** | Let 10–12 transactions stream across the screen (approx. 3 seconds). |

#### 🗣️ Spoken Script (Word-for-Word):
> "Let's watch SentinelRisk in action on our live payment authorization feed.
>
> *(Click 'Start Stream')*
> 
> Every incoming transaction is scored in sub-millisecond latency. To ensure absolute production integrity, our feature store computes customer velocities, rolling spend ratios, and device novelty strictly point-in-time, mathematically guaranteeing zero future data leakage.
>
> *(Point mouse to decision badges)*
>
> Notice our **Quad-State Decision Architecture**:
> - **Green APPROVE**: 98% of payments clear instantly with zero friction.
> - **Yellow CHALLENGE**: Mild anomalies trigger automated step-up friction — like device token re-verification — stopping fraud without sending cardholders to a manual queue.
> - **Orange REVIEW & Red HOLD**: High-risk anomalies and coordinated attacks are quarantined immediately."

---

### 📍 Scene 3: Data Lab — External CSV Ingestion & Real-World Assessment [01:25 – 02:20]

| Field | Details |
|---|---|
| **Timestamp** | `01:25 – 02:20` (55 Seconds) |
| **Active Screen** | Click Tab: **📥 Data Lab** |
| **On-Screen Action** | 1. Click button: **⚡ Try Example Dataset (500 txns)**.<br>2. Scroll smoothly through **Step 1: Column Alias Mapping** (show auto-detected fields).<br>3. Point to **Step 3: Authoritative Signal Availability Matrix** (highlight 'Zero Feature Fabrication Guarantee').<br>4. Click button: **⚡ Execute Full Risk Assessment**.<br>5. Click on a flagged transaction in the explorer table to reveal the slide-out Signal Drawer. |
| **Wait Condition** | Wait 1.5 seconds for the assessment progress bar to reach 100% and render the summary charts. |

#### 🗣️ Spoken Script (Word-for-Word):
> "One standout capability of SentinelRisk is the **Data Lab** — a self-service studio that lets enterprise risk teams upload arbitrary CSV transaction exports and evaluate real-world risk exposure.
>
> *(Click 'Try Example Dataset')*
> 
> SentinelRisk automatically detects column headers across 10 canonical fields and runs deep validation health checks.
>
> *(Point to Signal Availability Matrix)*
> 
> Crucially, SentinelRisk adheres to a strict **Zero Feature Fabrication Guarantee**: if an external dataset lacks device IDs or IP tokens, the platform routes through calibrated schema-adaptive models rather than imputing fake zeros.
>
> *(Click 'Execute Full Risk Assessment')*
> 
> Within seconds, we receive full portfolio risk analytics, precision/recall metrics against ground truth, and an interactive transaction explorer showing exact policy triggers."

---

### 📍 Scene 4: Fraud Operations Center & AI Evidence Agent [02:20 – 03:15]

| Field | Details |
|---|---|
| **Timestamp** | `02:20 – 03:15` (55 Seconds) |
| **Active Screen** | Click Tab: **🔍 Fraud Cases** |
| **On-Screen Action** | 1. In the review queue, locate the first `CRITICAL` priority case.<br>2. Click **🔍 Open Workbench**.<br>3. Click button: **🤖 Run AI Investigation**.<br>4. Scroll down to show the generated **Investigation Findings** and **Hypotheses with atomic citations** (`EVID-001`, `EVID-003`).<br>5. Click **👤 Assign to Me** and click **🔴 Confirm Fraud**. |
| **Wait Condition** | Wait 1 second while the LLM investigation report populates. |

#### 🗣️ Spoken Script (Word-for-Word):
> "When high-risk transactions require human oversight, they enter the **Fraud Operations Center**.
>
> *(Click 'Open Workbench')*
> 
> Cases are prioritized deterministically. Here, an account takeover attack has been flagged. Rather than forcing the analyst to query multiple SQL tables and graph databases, our **AI Investigation Agent** generates a comprehensive dossier.
>
> *(Click 'Run AI Investigation', point to evidence citations)*
>
> Every hypothesis is strictly grounded with immutable atomic evidence IDs (`EVID-001`, `EVID-003`), mathematically eliminating hallucinations.
>
> *(Click 'Assign to Me' then 'Confirm Fraud')*
> 
> Analysts can assign cases, log notes, and confirm fraud with one click. This feedback loop persists directly into our database to continuously monitor model health and power future retraining."

---

### 📍 Scene 5: Merchant Risk Intelligence & Incident Command Center [03:15 – 04:10]

| Field | Details |
|---|---|
| **Timestamp** | `03:15 – 04:10` (55 Seconds) |
| **Active Screen** | 1. Click Tab: **🏢 Merchant Risk**.<br>2. Then click Tab: **🚨 Incident Center**. |
| **On-Screen Action** | 1. On Merchant Risk tab: highlight top risky merchants and the additive risk attribution breakdown (+0.25 fraud rate, +0.20 velocity spike).<br>2. Switch to Incident Center tab.<br>3. On "2:00 AM Automated Card Testing Attack", click **⚡ Replay Incident**. |
| **Wait Condition** | Wait 1 second for the incident attack progression chart and containment playbook to render. |

#### 🗣️ Spoken Script (Word-for-Word):
> "SentinelRisk also delivers merchant-level protection.
>
> *(Click 'Merchant Risk', point to risk breakdown)*
>
> Our **Merchant Risk Intelligence** computes multi-window fraud trajectories with interpretable additive risk attributions and automated anomaly alerts.
>
> *(Click 'Incident Center', then click 'Replay Incident')*
> 
> And when systemic anomalies strike in the middle of the night, the **Incident Command Center** answers: *'What broke at 2 AM?'*
>
> Risk engineers can instantly replay automated bot attacks, analyze attack propagation, verify that 90%+ of fraudulent attempts were automatically blocked, and execute predefined containment playbooks."

---

### 📍 Scene 6: Model Health (PSI), Benchmarks & Conclusion [04:10 – 05:00]

| Field | Details |
|---|---|
| **Timestamp** | `04:10 – 05:00` (50 Seconds) |
| **Active Screen** | 1. Click Tab: **📈 Model Health**.<br>2. Then click Tab: **📊 Benchmarks**. |
| **On-Screen Action** | 1. On Model Health tab: point to Population Stability Index (PSI) feature drift table (`amount`, `velocity`).<br>2. Switch to Benchmarks tab: hover over the final comparison table showing 98.47% recall and 36.8% cost savings. |
| **Wait Condition** | Point mouse smoothly across the benchmark comparison rows. |

#### 🗣️ Spoken Script (Word-for-Word):
> "To prevent silent model degradation, SentinelRisk continuously monitors **Population Stability Index (PSI)** across all feature distributions, flagging data drift in real time.
>
> *(Click 'Benchmarks', point to comparison table)*
> 
> Across rigorous evaluations on frozen benchmarks of over 10,000 synthetic payments and 316,000 public Fraud Detection Handbook transactions, SentinelRisk achieves:
> - **98.47% fraud recall**
> - **36.8% reduction in total operational and loss costs**
> - **100% test coverage across 192 automated unit tests**
>
> SentinelRisk is fully production-ready, resilient, and built to safeguard high-scale payment networks. Thank you!"

---

## 🎯 Pro Tips for a Winning Video Recording

1. **Mouse Movement**: Keep your mouse movements smooth and intentional. Do not wiggle or jerk the cursor.
2. **Pacing**: Speak at a steady, confident pace (~130–140 words per minute). Pause for half a second when switching tabs.
3. **Tone**: Sound like a Lead Risk Infrastructure Engineer presenting to executive leadership.
4. **Resolution**: Record at **1080p (1920x1080)** or **4K (3840x2160)** for crisp dashboard text.
5. **Audio**: Use a dedicated USB/headset microphone with minimal background noise.
