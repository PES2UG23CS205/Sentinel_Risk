# SentinelRisk — Stage 5: Machine Learning Baselines Report

## 1. Executive Summary & Controlled Benchmark

We trained and evaluated **Logistic Regression** and **LightGBM** on the exact same point-in-time features and chronological split as the frozen Stage 4 Rules Baseline.

### Definitive Test Performance Comparison:

| Metric | Rules Baseline (Stage 4) | Logistic Regression | LightGBM |
|---|:---:|:---:|:---:|
| **Precision** | 44.44% | 63.68% | 97.73% |
| **Recall** | 21.37% | 92.37% | 98.47% |
| **F1 Score** | 28.87% | 75.39% | 98.10% |
| **PR-AUC** | -- | 93.36% | 99.92% |
| **ROC-AUC** | -- | 99.80% | 100.00% |
| **False Positive Rate (FPR)** | 0.35% | 0.69% | 0.03% |
| **False Negative Rate (FNR)** | 78.63% | 7.63% | 1.53% |
| **Review Rate** | 0.62% | 1.87% | 1.30% |
| **Expected Financial Loss** | **INR 641,079.22** | **INR 85,394.91** | **INR 16,255.32** |
| **Loss Reduction vs Rules** | Baseline (0.0%) | 86.68% reduction | 97.46% reduction |

---

## 2. Fraud Archetype Recall Breakdown (Test Set)

| Fraud Archetype | Rules Recall | Logistic Regression Recall | LightGBM Recall | Key Architectural Insight |
|---|:---:|:---:|:---:|---|
| **Card Testing Velocity** | 80.65% | 100.00% | 100.00% | Strong across both rules and ML due to prominent velocity spike signals. |
| **Account Takeover (ATO)** | 3.00% | 90.00% | 98.00% | ML captures non-linear interactions across device novelty, spending ratios, and customer age. |
| **Coordinated Abuse Rings** | 0.00% | 0.00% | 0.00% | Blind spot for single-transaction classifiers; motivates graph detection in Stage 6. |

---

## 3. Top Feature Insights

### LightGBM Top 5 Features (by Gain Importance):
1. **pi_age_days** (Gain: 1,743,668.45)
2. **device_age_days** (Gain: 140,234.53)
3. **pi_type_idx** (Gain: 77,689.35)
4. **cust_age_days** (Gain: 48,210.1)
5. **device_velocity_count_24h** (Gain: 36,303.09)

### Logistic Regression Top 5 Positive Risk Coefficients (Increase Log-Odds of Fraud):
1. **device_velocity_count_24h** (+6.0287)
2. **device_is_new_for_cust** (+5.7062)
3. **pi_velocity_count_24h** (+4.9833)
4. **cust_txn_count_prev** (+4.6111)
5. **pi_type_idx_1** (+3.2122)

---

## 4. Business Cost & Financial Impact
- **Rules Baseline Expected Loss**: INR 641,079.22
- **Logistic Regression Expected Loss**: INR 85,394.91
- **LightGBM Expected Loss**: INR 16,255.32
- **Fraud Prevented by LightGBM**: **INR 655,639.31**
