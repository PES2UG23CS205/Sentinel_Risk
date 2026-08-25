"""
SentinelRisk — Point-in-Time Feature Engineering Package

Exposes:
  - FeatureConfig
  - FeaturePipeline
  - LeakageChecker
  - LeakageDetectedError
  - run_deliberate_leakage_test
"""

from ml.features.config import FeatureConfig
from ml.features.feature_pipeline import FeaturePipeline
from ml.features.leakage_checks import (
    LeakageChecker,
    LeakageDetectedError,
    run_deliberate_leakage_test,
)

__all__ = [
    "FeatureConfig",
    "FeaturePipeline",
    "LeakageChecker",
    "LeakageDetectedError",
    "run_deliberate_leakage_test",
]
