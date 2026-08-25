"""
SentinelRisk — Feature Preprocessing Pipelines

Provides fit-on-train preprocessing transformers for Logistic Regression and LightGBM.
Ensures zero data leakage from validation or test partitions into feature scaling or encoding.
"""

import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder


CATEGORICAL_COLS = [
    "hour_of_day",
    "day_of_week",
    "merchant_category_idx",
    "pi_type_idx",
]

BINARY_COLS = [
    "is_weekend",
    "is_night",
    "cust_is_first_txn",
    "device_is_new_for_cust",
]


def build_logistic_preprocessor(feature_names: list[str]) -> ColumnTransformer:
    """
    Build scikit-learn ColumnTransformer for Logistic Regression:
      - Continuous features -> StandardScaler
      - Categorical indices -> OneHotEncoder(handle_unknown='ignore', sparse_output=False)
      - Binary flags -> Passthrough
    """
    continuous_cols = [
        c for c in feature_names
        if c not in CATEGORICAL_COLS and c not in BINARY_COLS
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), continuous_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_COLS),
            ("bin", "passthrough", BINARY_COLS),
        ],
        remainder="drop",
    )
    return preprocessor
