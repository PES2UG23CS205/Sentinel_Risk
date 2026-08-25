# SentinelRisk — Stage 12 Risk-Based Friction & Challenge Evaluation Report

> **Comprehensive Cost-Sensitive Benchmark: Tri-State vs Quad-State Challenge Policy**  
> *Generated: 2026-08-25 00:50:55 • Status: Complete & Verified*

---

## 1. Executive Summary: The Business Tradeoff

| Benchmark / Policy | Approval Rate | Challenge Rate | Review Rate | Hold Rate | Recall | Total Expected Cost | Cost Reduction |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Synthetic: Stage 7 Tri-State** | 96.83% | 0.00% | 1.9% | 1.28% | 98.47% | ₹48,055.32 | Baseline |
| **Synthetic: Stage 12 Quad-State** | 96.74% | 1.16% | 0.83% | 1.28% | 98.47% | ₹30,385.32 | **36.8% Savings** |
| **External: Stage 7 Tri-State** | 56.12% | 0.00% | 37.81% | 6.07% | 60.52% | €28,414,720.83 | Baseline |
| **External: Stage 12 Quad-State** | 56.12% | 15.94% | 21.86% | 6.07% | 60.52% | €20,135,300.83 | **29.1% Savings** |

---

## 2. Key Findings & Strategic Significance

1. **Massive Reduction in Analyst Queue Overhead**:
   - In the synthetic benchmark, routing moderate anomalies to automated `CHALLENGE` reduces human analyst `REVIEW` volume from **1.9%** down to **0.83%**—a **drastic operational relief for fraud operations**.
2. **Preserved Fraud Recall**:
   - Fraud recall is preserved at **98.47%** while shifting false alarms into lightweight step-up verifications (₹35 friction) rather than high-friction declines (₹250) or costly manual investigations (₹200).
3. **Financial Loss Optimization**:
   - Total expected operational cost dropped significantly across both the first-party synthetic world and the third-party external dataset.
