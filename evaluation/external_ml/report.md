# External Fraud Detection Handbook — LightGBM Benchmark Report

> Dedicated schema-adaptive risk model trained on 1.75M transactions across 183 daily partitions.

## 1. Split & Dataset Summary
- **Total Transactions**: 1,754,155
- **Total Frauds**: 14,681 (0.837% base prevalence)
- **Train Set (Days 0-119)**: 1,150,370 rows (9,293 frauds)
- **Validation Set (Days 120-149)**: 287,588 rows (2,564 frauds)
- **Test Set (Days 150-182)**: 316,197 rows (2,824 frauds)

## 2. Model Performance on Untouched Test Set
| Metric | Value |
|---|---|
| **Precision** | **55.90%** |
| **Recall** | **32.19%** |
| **F1-Score** | **40.85%** |
| **PR-AUC** | **32.81%** |
| **ROC-AUC** | **65.21%** |
| **False Positive Rate** | 0.23% (717 non-fraud flagged) |
| **False Negative Rate** | 67.81% (1,915 missed frauds) |
| **Review Rate** | 0.51% |

## 3. Confusion Matrix
| | Predicted Legitimate | Predicted Fraud |
|---|---|---|
| **Actual Legitimate** | 312,656 | 717 |
| **Actual Fraud** | 1,915 | 909 |

## 4. Top 10 Features by Split Importance
- **terminal_amount_mean_prev**: 599 splits
- **terminal_txn_count_prev**: 484 splits
- **cust_amount_mean_prev**: 447 splits
- **terminal_unique_cust_prev**: 444 splits
- **cust_amount_max_prev**: 400 splits
- **cust_amount_ratio**: 322 splits
- **amount**: 251 splits
- **cust_amount_zscore**: 211 splits
- **terminal_velocity_7d**: 201 splits
- **cust_amount_std_prev**: 198 splits
