"""
SentinelRisk — Live Data Session & Streaming Manager

Coordinates real-time transaction streaming, incremental evaluation,
live session counters, external replay evaluation metrics (TP, FP, TN, FN, Precision, Recall, F1),
scrolling risk feed, and active incident detection.
"""

import time
from datetime import datetime
from typing import Any, Optional
import uuid
import numpy as np

from backend.app.ingestion.schema import NormalizedTransaction
from backend.app.ingestion.feature_builder import IncrementalFeatureBuilder
from backend.app.scoring.realtime_service import RealtimeRiskService
from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.agent import InvestigationAgent


class LiveSessionManager:
    """Stateful coordinator for real-time transaction sessions."""

    def __init__(self):
        self.feature_builder = IncrementalFeatureBuilder()
        self.risk_service = RealtimeRiskService()
        self.investigation_agent = InvestigationAgent()
        self.case_manager = CaseManager(self.investigation_agent)
        
        self.session_id: str = f"SESSION-{uuid.uuid4().hex[:8].upper()}"
        self.source_name: str = "SYNTHETIC_DATASET"
        self.status: str = "IDLE"  # IDLE, STREAMING, PAUSED, STOPPED
        self.speed: float = 1.0    # 1x, 2x, 5x, 10x
        
        self.dataset_buffer: list[NormalizedTransaction] = []
        self.current_index: int = 0
        
        # Live Session Counters (Isolated from Historical Benchmark)
        self.counters = {
            "total_processed": 0,
            "approved_count": 0,
            "challenged_count": 0,
            "review_count": 0,
            "hold_count": 0,
            "approval_rate_pct": 0.0,
            "challenge_rate_pct": 0.0,
            "frictionless_approval_rate_pct": 0.0,
            "fraud_loss_prevented_inr": 0.0,
            "avg_risk_score": 0.0,
            "total_risk_sum": 0.0,
            "avg_latency_ms": 0.048,
        }

        # External Replay Metrics (Confusion Matrix & Evaluation strictly on current session)
        self.replay_metrics = {
            "has_ground_truth": False,
            "ground_truth_fraud_count": 0,
            "ground_truth_legit_count": 0,
            "detected_fraud_count": 0,
            "tp": 0,
            "fp": 0,
            "tn": 0,
            "fn": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "accuracy": 0.0,
        }
        self.latencies_history: list[float] = []
        
        self.recent_events: list[dict[str, Any]] = []
        self.max_recent_events: int = 100
        
        self.active_incident: Optional[dict[str, Any]] = None
        self.recent_decisions_window: list[dict[str, Any]] = []

    def clear_session(self):
        """Reset all live session data, metrics, and privacy buffers."""
        self.session_id = f"SESSION-{uuid.uuid4().hex[:8].upper()}"
        self.status = "IDLE"
        self.dataset_buffer.clear()
        self.current_index = 0
        self.feature_builder.reset_state()
        self.counters = {
            "total_processed": 0,
            "approved_count": 0,
            "challenged_count": 0,
            "review_count": 0,
            "hold_count": 0,
            "approval_rate_pct": 0.0,
            "challenge_rate_pct": 0.0,
            "frictionless_approval_rate_pct": 0.0,
            "fraud_loss_prevented_inr": 0.0,
            "avg_risk_score": 0.0,
            "total_risk_sum": 0.0,
            "avg_latency_ms": 0.048,
        }
        self.replay_metrics = {
            "has_ground_truth": False,
            "ground_truth_fraud_count": 0,
            "ground_truth_legit_count": 0,
            "detected_fraud_count": 0,
            "tp": 0,
            "fp": 0,
            "tn": 0,
            "fn": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "accuracy": 0.0,
        }
        self.latencies_history.clear()
        self.recent_events.clear()
        self.active_incident = None
        self.recent_decisions_window.clear()

    def load_dataset(self, rows: list[NormalizedTransaction], source_name: str = "Uploaded CSV"):
        """Load validated normalized rows into the stream buffer."""
        self.clear_session()
        self.source_name = source_name
        self.dataset_buffer = rows
        self.status = "IDLE"
        self.current_index = 0

    def evaluate_normalized_transaction(self, txn: NormalizedTransaction) -> dict[str, Any]:
        """
        Incrementally extract point-in-time features, score transaction,
        execute policy engine with challenge orchestration, and stream state.
        """
        start_t = time.perf_counter()

        # 1. Incremental Point-in-Time Feature Extraction (strictly t < T)
        feat_res = self.feature_builder.extract_features(txn)
        
        # 2. Risk Evaluation via Real-Time Service
        eval_payload = {
            "transaction_id": txn.transaction_id,
            "timestamp": txn.timestamp,
            "amount": txn.amount,
            "currency": txn.currency,
            "customer_id": txn.customer_id,
            "merchant_id": txn.merchant_id,
            "device_id": txn.device_id,
            "payment_instrument_id": txn.payment_instrument_id,
            "ml_probability": feat_res["ml_probability"],
            "graph_ring_score": feat_res["graph_ring_score"],
            "graph_ring_candidate": feat_res["graph_ring_candidate"],
            "features": feat_res["features"],
        }
        
        eval_result = self.risk_service.evaluate_transaction(eval_payload)

        # 3. Investigation Case Queueing (For REVIEW / HOLD analyst queues)
        case_dict = None
        investigation_dict = None
        if eval_result.get("is_analyst_case") == 1 or eval_result.get("decision") in ("REVIEW", "HOLD"):
            case = self.case_manager.create_case_from_decision(
                decision_record=eval_result,
                transaction_data=eval_payload,
                graph_data={
                    "graph_ring_score": feat_res["graph_ring_score"],
                    "graph_ring_candidate": feat_res["graph_ring_candidate"],
                },
            )
            if case:
                case_dict = case.to_dict()

        latency_ms = round((time.perf_counter() - start_t) * 1000, 3)
        self.latencies_history.append(latency_ms)

        # 4. Update Live Counters
        dec = eval_result.get("decision", "APPROVE")
        self.counters["total_processed"] += 1
        if dec == "APPROVE":
            self.counters["approved_count"] += 1
        elif dec == "CHALLENGE":
            self.counters["challenged_count"] += 1
        elif dec == "REVIEW":
            self.counters["review_count"] += 1
        elif dec == "HOLD":
            self.counters["hold_count"] += 1
            self.counters["fraud_loss_prevented_inr"] += float(txn.amount)

        self.counters["total_risk_sum"] += float(feat_res["ml_probability"])
        n = self.counters["total_processed"]
        self.counters["avg_risk_score"] = round(self.counters["total_risk_sum"] / max(1, n), 4)
        self.counters["avg_latency_ms"] = round(
            ((self.counters["avg_latency_ms"] * (n - 1)) + latency_ms) / max(1, n), 3
        )
        self.counters["approval_rate_pct"] = round((self.counters["approved_count"] / max(1, n)) * 100, 2)
        self.counters["frictionless_approval_rate_pct"] = self.counters["approval_rate_pct"]
        self.counters["challenge_rate_pct"] = round((self.counters["challenged_count"] / max(1, n)) * 100, 2)

        # 5. External Replay Metrics Tracking (Isolated Ground Truth)
        gt = txn.ground_truth_fraud
        if gt is not None:
            self.replay_metrics["has_ground_truth"] = True
            is_gt_fraud = int(gt) == 1
            is_detected_fraud = dec in ("CHALLENGE", "REVIEW", "HOLD")

            if is_gt_fraud:
                self.replay_metrics["ground_truth_fraud_count"] += 1
            else:
                self.replay_metrics["ground_truth_legit_count"] += 1

            if is_detected_fraud:
                self.replay_metrics["detected_fraud_count"] += 1

            if is_gt_fraud and is_detected_fraud:
                self.replay_metrics["tp"] += 1
            elif not is_gt_fraud and is_detected_fraud:
                self.replay_metrics["fp"] += 1
            elif not is_gt_fraud and not is_detected_fraud:
                self.replay_metrics["tn"] += 1
            elif is_gt_fraud and not is_detected_fraud:
                self.replay_metrics["fn"] += 1

            tp = self.replay_metrics["tp"]
            fp = self.replay_metrics["fp"]
            tn = self.replay_metrics["tn"]
            fn = self.replay_metrics["fn"]

            p = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            r = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
            acc = ((tp + tn) / (tp + tn + fp + fn)) if (tp + tn + fp + fn) > 0 else 0.0

            self.replay_metrics["precision"] = round(p, 4)
            self.replay_metrics["recall"] = round(r, 4)
            self.replay_metrics["f1"] = round(f1, 4)
            self.replay_metrics["accuracy"] = round(acc, 4)

        # Format Ground Truth Display
        gt_label = (
            "FRAUD" if gt == 1
            else ("LEGITIMATE" if gt == 0 else "UNLABELED")
        )

        event_item = {
            "transaction_id": txn.transaction_id,
            "timestamp": txn.timestamp,
            "amount": txn.amount,
            "currency": txn.currency,
            "customer_id": txn.customer_id,
            "merchant_id": txn.merchant_id,
            "device_id": txn.device_id,
            "payment_instrument_id": txn.payment_instrument_id,
            "decision": dec,
            "primary_trigger": eval_result.get("primary_trigger", "APPROVED_BASELINE"),
            "challenge": eval_result.get("challenge"),
            "risk_score": eval_result.get("risk_score", feat_res["ml_probability"]),
            "ml_probability": feat_res["ml_probability"],
            "ml_status": feat_res.get("ml_status", "VALID"),
            "model_source": feat_res.get("model_source", "primary_synthetic_lightgbm"),
            "feature_schema": feat_res.get("feature_schema", "sentinelrisk_v1"),
            "available_signal_count": feat_res.get("available_signal_count", 47),
            "missing_signal_count": feat_res.get("missing_signal_count", 0),
            "missing_context": feat_res["missing_context"],
            "graph_ring_score": feat_res["graph_ring_score"],
            "features": feat_res["features"],
            "evaluation": eval_result,
            "case": case_dict,
            "investigation": investigation_dict,
            "latency_ms": latency_ms,
            "ground_truth_fraud": gt,
            "ground_truth_label": gt_label,
            "ground_truth_scenario": txn.ground_truth_scenario,
            "metadata": txn.metadata,
            "derived_fields": txn.metadata.get("derived_fields", {}),
        }

        # Add to scrolling feed (newest at front)
        self.recent_events.insert(0, event_item)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop()

        # 6. Live Incident Detection (Rolling Window Analysis)
        self.recent_decisions_window.append(event_item)
        if len(self.recent_decisions_window) > 10:
            self.recent_decisions_window.pop(0)

        recent_holds = sum(1 for e in self.recent_decisions_window if e["decision"] == "HOLD")
        max_vel = max((e["features"].get("pi_velocity_count_1h", 0) for e in self.recent_decisions_window), default=0)
        max_ring = max((e.get("graph_ring_score", 0.0) for e in self.recent_decisions_window), default=0.0)

        if recent_holds >= 3 or max_vel >= 5 or max_ring >= 0.50:
            pattern_name = (
                "CARD_TESTING_BOT_BURST" if max_vel >= 5
                else ("COORDINATED_RING_SURGE" if max_ring >= 0.50 else "ANOMALOUS_HOLD_SPIKE")
            )
            if not self.active_incident:
                self.active_incident = {
                    "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
                    "pattern": pattern_name,
                    "first_seen": txn.timestamp,
                    "affected_transactions": recent_holds,
                    "status": "ACTIVE",
                }
            else:
                self.active_incident["affected_transactions"] += 1
        elif self.active_incident and recent_holds == 0:
            self.active_incident["status"] = "RESOLVED"

        return event_item

    def step_stream(self) -> Optional[dict[str, Any]]:
        """Process the next transaction in the loaded dataset stream."""
        if self.current_index >= len(self.dataset_buffer):
            self.status = "STOPPED"
            return None

        txn = self.dataset_buffer[self.current_index]
        self.current_index += 1
        
        event = self.evaluate_normalized_transaction(txn)
        return event

    def get_state(self) -> dict[str, Any]:
        """Return complete live session status and latency percentiles."""
        total_rows = len(self.dataset_buffer)
        total_proc = self.counters["total_processed"]
        hold_rate = round((self.counters["hold_count"] / max(1, total_proc)) * 100, 2)
        review_rate = round((self.counters["review_count"] / max(1, total_proc)) * 100, 2)
        approve_rate = round((self.counters["approved_count"] / max(1, total_proc)) * 100, 2)

        # Compute latency percentiles
        if self.latencies_history:
            lats = np.array(self.latencies_history)
            p50 = float(np.percentile(lats, 50))
            p95 = float(np.percentile(lats, 95))
            p99 = float(np.percentile(lats, 99))
        else:
            p50, p95, p99 = 0.048, 0.085, 0.120

        # Determine active model schema
        if "Handbook" in self.source_name or "handbook" in self.source_name.lower():
            active_model = "external_handbook_lightgbm"
            active_schema = "fraud_handbook_v1"
            avail_signals = 24
            miss_signals = 23
        else:
            active_model = "primary_synthetic_lightgbm"
            active_schema = "sentinelrisk_v1"
            avail_signals = 47
            miss_signals = 0

        return {
            "session_id": self.session_id,
            "source_name": self.source_name,
            "status": self.status,
            "speed": self.speed,
            "active_model_source": active_model,
            "active_feature_schema": active_schema,
            "available_signal_count": avail_signals,
            "missing_signal_count": miss_signals,
            "progress": {
                "current_index": self.current_index,
                "total_rows": total_rows,
                "percent": round((self.current_index / max(1, total_rows)) * 100, 1) if total_rows > 0 else 0.0,
            },
            "counters": {
                **self.counters,
                "approve_rate_pct": approve_rate,
                "hold_rate_pct": hold_rate,
                "review_rate_pct": review_rate,
            },
            "replay_metrics": self.replay_metrics,
            "latency_percentiles_ms": {
                "p50": round(p50, 3),
                "p95": round(p95, 3),
                "p99": round(p99, 3),
            },
            "active_incident": self.active_incident,
            "recent_events": self.recent_events[:15],
        }

    @property
    def state(self) -> dict[str, Any]:
        """Convenience property for accessing current session state."""
        return self.get_state()
