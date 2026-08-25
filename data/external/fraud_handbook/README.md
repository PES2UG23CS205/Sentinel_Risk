# External Dataset: Fraud Detection Handbook

## Overview
This directory is designated for the simulated transaction benchmark dataset from the **Fraud Detection Handbook** (*Reproducible Machine Learning for Credit Card Fraud Detection - Practical Handbook* by Le Borgne et al., Université Libre de Bruxelles / Machine Learning Group).

- **Official Source**: [Fraud-Detection-Handbook/simulated-data-raw](https://github.com/Fraud-Detection-Handbook/simulated-data-raw)
- **Dataset Span**: April 1, 2018 – September 30, 2018 (183 daily `.pkl` files, 1.75M transactions, ~102 MB total)
- **Zero Leakage Handling**: The `TX_FRAUD` label is strictly isolated for post-decision evaluation and is never passed to feature extractors, LightGBM models, or policy logic.

---

## Storage & Git Optimization
Because this external dataset consists of 184 individual binary `.pkl` files totaling ~102 MB, the raw `.pkl` data files are excluded from Git version control via `.gitignore` to maintain a lightweight, fast-cloning repository.

The repository includes all data loaders, schema normalizers, external LightGBM models (`ml/models/external_fraud/model.joblib`), evaluation scripts, and pre-computed benchmark results.

---

## How to Download the Dataset

You can easily download the benchmark dataset using the included script:

```bash
# Download the full 183-day dataset
python scripts/download_fraud_handbook.py

# Or download a subset (e.g. first 5 days) for rapid testing
python scripts/download_fraud_handbook.py 5
```

Alternatively, you can manually clone or place the `.pkl` files into:
`data/external/fraud_handbook/data/*.pkl`

---

## Running Verification & Replay

Once downloaded, you can replay external transactions through SentinelRisk:

```bash
# Replay 1,000 transactions through the live streaming pipeline
python scripts/replay_fraud_handbook.py --limit 1000

# Run external LightGBM benchmark evaluation
python scripts/replay_external_ml.py
```