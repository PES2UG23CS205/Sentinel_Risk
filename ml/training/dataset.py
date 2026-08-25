"""
SentinelRisk — ML Dataset Preparation & Chronological Splitting

Loads the Stage 3 point-in-time feature dataset, strictly separates features from
target/metadata/identifiers, enforces the exact Stage 4 chronological split,
and derives training class weighting.
"""

from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import numpy as np


@dataclass
class DatasetSplits:
    """Holds feature matrices and target arrays for chronological train, val, and test splits."""
    X_train: pd.DataFrame
    y_train: np.ndarray
    amounts_train: np.ndarray
    archetypes_train: np.ndarray

    X_val: pd.DataFrame
    y_val: np.ndarray
    amounts_val: np.ndarray
    archetypes_val: np.ndarray

    X_test: pd.DataFrame
    y_test: np.ndarray
    amounts_test: np.ndarray
    archetypes_test: np.ndarray

    feature_names: list[str]
    scale_pos_weight: float
    split_info: dict


def prepare_ml_dataset(
    csv_path: str | Path = "data/features/transaction_features.csv",
    train_fraction: float = 0.70,
    val_fraction: float = 0.15,
) -> DatasetSplits:
    """
    Load feature CSV, validate integrity, and create non-overlapping chronological splits.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Feature dataset not found at: {path.resolve()}")

    df = pd.read_csv(path)

    # 1. Verify expected columns
    target_col = "is_fraud_ground_truth"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' missing from dataset.")

    # 2. Strict exclusion of raw IDs and target/metadata columns from feature matrix X
    excluded_cols = {
        "transaction_id",
        "timestamp",
        "merchant_id",
        "customer_id",
        "device_id",
        "payment_instrument_id",
        "is_fraud",
        "is_fraud_ground_truth",
        "fraud_archetype",
        "fraud_case_id",
    }

    feature_cols = [c for c in df.columns if c not in excluded_cols]

    # Target isolation assertion: No target or ID column in feature_cols
    for col in excluded_cols:
        assert col not in feature_cols, f"Security Violation: '{col}' found in feature matrix!"

    # 3. Sort chronologically by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)
    n = len(df)

    idx_train = int(n * train_fraction)
    idx_val = int(n * (train_fraction + val_fraction))

    train_df = df.iloc[:idx_train].copy()
    val_df = df.iloc[idx_train:idx_val].copy()
    test_df = df.iloc[idx_val:].copy()

    # 4. Extract feature matrices and target arrays
    X_train = train_df[feature_cols].copy()
    y_train = train_df[target_col].astype(int).values
    amounts_train = train_df["amount"].values
    archetypes_train = train_df["fraud_archetype"].values

    X_val = val_df[feature_cols].copy()
    y_val = val_df[target_col].astype(int).values
    amounts_val = val_df["amount"].values
    archetypes_val = val_df["fraud_archetype"].values

    X_test = test_df[feature_cols].copy()
    y_test = test_df[target_col].astype(int).values
    amounts_test = test_df["amount"].values
    archetypes_test = test_df["fraud_archetype"].values

    # 5. Compute class imbalance scale factor strictly from training partition
    pos_train = int(y_train.sum())
    neg_train = len(y_train) - pos_train
    scale_pos_weight = neg_train / max(1, pos_train)

    split_info = {
        "train": {
            "count": len(train_df),
            "fraud_count": pos_train,
            "fraud_prevalence": f"{(pos_train / len(train_df))*100:.2f}%",
            "start_date": str(train_df["timestamp"].min()),
            "end_date": str(train_df["timestamp"].max()),
        },
        "validation": {
            "count": len(val_df),
            "fraud_count": int(y_val.sum()),
            "fraud_prevalence": f"{(y_val.sum() / len(val_df))*100:.2f}%",
            "start_date": str(val_df["timestamp"].min()),
            "end_date": str(val_df["timestamp"].max()),
        },
        "test": {
            "count": len(test_df),
            "fraud_count": int(y_test.sum()),
            "fraud_prevalence": f"{(y_test.sum() / len(test_df))*100:.2f}%",
            "start_date": str(test_df["timestamp"].min()),
            "end_date": str(test_df["timestamp"].max()),
        },
    }

    return DatasetSplits(
        X_train=X_train,
        y_train=y_train,
        amounts_train=amounts_train,
        archetypes_train=archetypes_train,
        X_val=X_val,
        y_val=y_val,
        amounts_val=amounts_val,
        archetypes_val=archetypes_val,
        X_test=X_test,
        y_test=y_test,
        amounts_test=amounts_test,
        archetypes_test=archetypes_test,
        feature_names=feature_cols,
        scale_pos_weight=scale_pos_weight,
        split_info=split_info,
    )
