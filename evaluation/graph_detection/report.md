# SentinelRisk — Stage 6: Graph Detection & Ring Scoring Report

## 1. Executive Summary
The heterogeneous entity graph and coordinated abuse ring detector were benchmarked against all 15 ground-truth synthetic fraud syndicates.

- **Ground-Truth Rings Present**: 15
- **Rings Successfully Detected**: **15 / 15** (100.00% Case-Level Recall)
- **Transaction-Level Precision**: **100.00%**
- **Transaction-Level Recall**: **78.57%**
- **Transaction-Level F1 Score**: **88.00%**

---

## 2. Graph Structural Statistics
- **Total Entity Nodes**: 78,759
  - Customers: 24,442
  - Devices: 26,076
  - Payment Instruments: 26,743
  - Merchants: 1,498
- **Total Relationship Edges**: 186,020
- **Connected Components**: 1
- **Largest Component Size**: 78,759 nodes
- **Average Node Degree**: 4.72
- **Max Node Degree**: 640

---

## 3. Ground-Truth Ring Evaluation (All 15 Rings)

| Ring ID | Activity Window | Customers | Devices | PIs | Merchants | Total Txns | Flagged Txns | Max Ring Score | Status |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| RING_014 | 2025-02-10 to 2025-02-12 | 5 | 1 | 1 | 4 | 15 | 12 | 1.00 | **DETECTED** |
| RING_009 | 2025-02-19 to 2025-02-21 | 8 | 1 | 1 | 3 | 24 | 22 | 1.00 | **DETECTED** |
| RING_015 | 2025-02-20 to 2025-02-22 | 5 | 1 | 1 | 4 | 15 | 12 | 1.00 | **DETECTED** |
| RING_012 | 2025-03-07 to 2025-03-09 | 3 | 1 | 1 | 2 | 9 | 7 | 0.82 | **DETECTED** |
| RING_002 | 2025-03-08 to 2025-03-10 | 8 | 1 | 1 | 4 | 24 | 22 | 1.00 | **DETECTED** |
| RING_004 | 2025-03-19 to 2025-03-21 | 3 | 1 | 1 | 2 | 9 | 5 | 0.82 | **DETECTED** |
| RING_005 | 2025-03-28 to 2025-03-29 | 3 | 1 | 1 | 2 | 9 | 3 | 0.82 | **DETECTED** |
| RING_010 | 2025-03-31 to 2025-04-02 | 5 | 1 | 1 | 3 | 15 | 13 | 1.00 | **DETECTED** |
| RING_008 | 2025-04-04 to 2025-04-05 | 3 | 1 | 1 | 4 | 9 | 7 | 0.82 | **DETECTED** |
| RING_007 | 2025-04-12 to 2025-04-14 | 5 | 1 | 1 | 3 | 15 | 13 | 1.00 | **DETECTED** |
| RING_001 | 2025-04-12 to 2025-04-14 | 5 | 1 | 1 | 4 | 15 | 12 | 1.00 | **DETECTED** |
| RING_013 | 2025-04-15 to 2025-04-16 | 3 | 1 | 1 | 3 | 9 | 6 | 0.82 | **DETECTED** |
| RING_003 | 2025-04-24 to 2025-04-26 | 3 | 1 | 1 | 3 | 9 | 6 | 0.82 | **DETECTED** |
| RING_006 | 2025-05-19 to 2025-05-21 | 8 | 1 | 1 | 3 | 24 | 21 | 1.00 | **DETECTED** |
| RING_011 | 2025-05-22 to 2025-05-24 | 3 | 1 | 1 | 1 | 9 | 4 | 0.82 | **DETECTED** |

---

## 4. Stage 5 Test Period Transparency Audit
- **Held-Out Test Window**: 2025-06-11 to 2025-06-30 (10,179 transactions)
- **Ground-Truth Rings Present**: 0 cases
- **False Alarm Rings Generated**: 0 cases (100% Specificity)
- **Finding**: Preserved the sacred Stage 5 test period without data contamination.
