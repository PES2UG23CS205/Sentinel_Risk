# SentinelRisk — Risk-Based Friction Demo Walkthrough (Razorpay Panel)

## 1. Demo Narrative: "Least-Friction Risk Orchestration"

When presenting SentinelRisk to the Razorpay buildathon panel, emphasize the shift from **blunt enforcement** to **cost-sensitive intelligent friction orchestration**.

---

## 2. Interactive Step-by-Step Demo Flow

### Step 1: Open Operations Console
- Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard) in your browser.
- Point out the **Quad-State KPI Tiles** in the Live Session Counter:
  - 🟢 `APPROVE` (Frictionless Zero-Friction)
  - 🟡 `CHALLENGE` (Automated Step-Up Verification)
  - 🟠 `REVIEW` (Human Analyst Queue)
  - 🔴 `HOLD` (Platform Protection)

### Step 2: Compare Pre-Loaded Scenarios (Tab: 🎯 Pre-Loaded Demo Scenarios)

1. **Scenario 1: Legitimate Payment (`APPROVE`)**
   - Click `🟢 Legitimate Payment (APPROVE)`.
   - **Signal**: Daytime grocery spend from known device token.
   - **Decision**: `APPROVE` with zero friction.

2. **Scenario 2: Moderate Anomaly (`CHALLENGE`)**
   - Click `⚡ Step-Up Device Challenge (Stage 12)`.
   - **Signal**: ₹3,450 electronics purchase on a brand-new device hardware token.
   - **Observation**:
     - Decision is `CHALLENGE` (Sky-blue badge).
     - Challenge box displays: `CHALLENGE_DEVICE_VERIFICATION (LOW Friction)`.
     - Highlight: *"Instead of declining this high-value customer or dumping them into a 4-hour analyst queue, SentinelRisk triggers automated device biometric verification, saving ₹215 in friction cost."*

3. **Scenario 3: Complex Syndicate Ring (`REVIEW` / `HOLD`)**
   - Click `🔴 Coordinated Ring (HOLD + Graph)`.
   - **Signal**: 6 accounts sharing identical hardware fingerprint and payment token.
   - **Decision**: `HOLD` + Graph Ring Score $0.88$.
   - **Observation**: Creates high-priority analyst case `CASE-001` with AI Investigation Dossier.

---

## 3. Flagship Scenario: "What Broke at 2 AM?" Escalation Sequence

- Click `⚡ Flagship: "What Broke at 2 AM?"`.
- Observe the incident progression timeline:
  1. **02:00:00 (Normal Traffic)**: Payments approved frictionless (`APPROVE`).
  2. **02:02:15 (Attack Onset)**: Card velocity begins climbing $\rightarrow$ System triggers `CHALLENGE (CHALLENGE_PAYMENT_REAUTH)`.
  3. **02:04:30 (Burst Attack)**: Bot burst velocity $\ge 5$ txns/hr $\rightarrow$ Escalates to `HOLD (Platform Protection)`.
  4. **02:05:00 (Triage & Containment)**: Syndicate cluster placed in `REVIEW` and investigated.
- **Key Insight for Panel**: SentinelRisk throttles and dampens early anomaly vectors before they compound into full-scale system incidents.

---

## 4. Live Dataset Replay (Tab: 📚 Fraud Detection Handbook)

- Switch to `📚 Fraud Detection Handbook` tab.
- Click `⚡ Load 1,000 Transactions`.
- Click `▶ Start Stream`.
- Watch the scrolling live feed:
  - Transactions dynamically split across `APPROVE` (Green), `CHALLENGE` (Sky Blue), `REVIEW` (Amber), and `HOLD` (Red).
  - Ground-truth evaluation metrics update live in real-time.
