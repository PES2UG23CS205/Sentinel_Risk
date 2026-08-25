# SentinelRisk — Stage 4: Rules Baseline Evaluation Report

## 1. Executive Summary
The deterministic, rules-only fraud baseline was evaluated on a temporally held-out test set (final 15% chronological split).

- **Precision**: 44.44%
- **Recall**: 21.37%
- **F1 Score**: 28.87%
- **Review Rate**: 0.62%
- **Expected Financial Loss**: INR 641,079.22
- **Fraud Loss Avoided**: INR 30,865.41

---

## 2. Chronological Split Setup
- **Train Period (70%)**: 2025-01-01 13:29:23 to 2025-05-23 09:43:04 (47,500 txns, 545 fraud, 1.15%)
- **Validation Period (15%)**: 2025-05-23 09:44:15 to 2025-06-11 18:02:49 (10,179 txns, 44 fraud, 0.43%)
- **Held-Out Test Period (15%)**: 2025-06-11 18:06:20 to 2025-06-30 23:58:38 (10,179 txns, 131 fraud, 1.29%)

---

## 3. Confusion Matrix (Held-Out Test Set)

```
                 Actual
              Legitimate       Fraud
Predicted
Legitimate    TN: 10013      FN: 103       
Fraud         FP: 35         TP: 28        
```

---

## 4. Rule Trigger Contribution Analysis

| Rule Name | Trigger Count | Trigger Rate | True Positives Caught | Rule Precision |
|---|---|---|---|---|
| Customer Amount Anomaly | 195 | 1.92% | 3 | 1.54% |
| Customer Velocity | 25 | 0.25% | 25 | 100.00% |
| Device Novelty Compound | 48 | 0.47% | 20 | 41.67% |
| Payment Instrument Velocity | 25 | 0.25% | 25 | 100.00% |
| Merchant Relative Anomaly | 71 | 0.70% | 0 | 0.00% |
| Off-Hour Anomaly | 29 | 0.28% | 13 | 44.83% |

---

## 5. Fraud Archetype Breakdown (Test Set)

| Fraud Archetype | Total Cases | Caught Cases | Missed Cases | Recall |
|---|---|---|---|---|
| Account Takeover (ATO) | 100 | 3 | 97 | 3.00% |
| Card Testing Velocity | 31 | 25 | 6 | 80.65% |
| Coordinated Abuse Rings | 0 | 0 | 0 | 0.00% |

---

## 6. Business Cost Analysis
- **False Negative Fraud Loss**: INR 633,979.22 (103 missed fraud events)
- **False Positive Friction Cost**: INR 5,250.0 (35 legitimate users impacted @ INR 150.0/each)
- **Manual Review Overhead**: INR 1,850.0
- **Total Expected Loss**: **INR 641,079.22**
- **Fraud Prevented (Benefit)**: **INR 30,865.41**
