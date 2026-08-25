"""
SentinelRisk — Incident Simulation & Recovery Engine

Simulates realistic offline fraud attacks ("What broke at 2 AM"), traces the end-to-end
detection and investigation pipeline, and generates containment & recovery recommendations.
"""

from datetime import datetime, timedelta
import pandas as pd

from simulation.incident_simulator.scenarios import SCENARIOS, IncidentScenario
from backend.app.policy.engine import PolicyEngine
from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.agent import InvestigationAgent


class IncidentSimulator:
    """Simulates operational risk incidents and traces detection, investigation, and recovery."""

    def __init__(self, policy_engine: PolicyEngine | None = None, agent: InvestigationAgent | None = None):
        self.policy_engine = policy_engine or PolicyEngine()
        self.agent = agent or InvestigationAgent()
        self.case_manager = CaseManager(self.agent)

    def run_scenario(self, scenario_key: str = "CARD_TESTING_ATTACK") -> dict:
        """
        Execute an end-to-end incident simulation.

        Returns:
            dict containing:
              - scenario_info
              - timeline_events
              - decision_summary
              - cases_created
              - sample_investigation_report
              - recovery_recommendations
              - incident_metrics
        """
        scenario = SCENARIOS.get(scenario_key, SCENARIOS["CARD_TESTING_ATTACK"])
        base_time = datetime.strptime(scenario.start_time, "%Y-%m-%d %H:%M:%S")

        transactions = []
        timeline = []

        # 1. Synthesize scenario-specific events
        if scenario.scenario_type == "BASELINE":
            for i in range(25):
                t_ts = (base_time + timedelta(minutes=i*2)).strftime("%Y-%m-%d %H:%M:%S")
                transactions.append({
                    "transaction_id": f"SIM-BASE-{i+1:03d}",
                    "timestamp": t_ts,
                    "amount": 450.0 + (i * 20),
                    "customer_id": f"CUST_LEGIT_{i+1}",
                    "device_id": f"DEV_LEGIT_{i+1}",
                    "payment_instrument_id": f"PI_LEGIT_{i+1}",
                    "merchant_id": f"MERCH_{(i%5)+1}",
                    "is_fraud": 0,
                    "ml_prob": 0.005,
                    "ring_score": 0.0,
                    "ring_cand": 0,
                    "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 1.0, "device_is_new_for_cust": 0},
                })

        elif scenario.scenario_type == "CARD_TESTING_ATTACK":
            # Rapid micro-authorization burst on single card token
            for i in range(20):
                t_ts = (base_time + timedelta(seconds=i*30)).strftime("%Y-%m-%d %H:%M:%S")
                is_fraud = 1
                vel = min(10, i + 1)
                ml_p = 0.02 if vel < 3 else 0.99
                transactions.append({
                    "transaction_id": f"SIM-BOT-{i+1:03d}",
                    "timestamp": t_ts,
                    "amount": 75.0,
                    "customer_id": f"CUST_BOT_{(i%3)+1}",
                    "device_id": "DEV_BOT_01",
                    "payment_instrument_id": "PI_BOT_99",
                    "merchant_id": f"MERCH_{(i%4)+1}",
                    "is_fraud": is_fraud,
                    "ml_prob": ml_p,
                    "ring_score": 0.0,
                    "ring_cand": 0,
                    "features": {"pi_velocity_count_1h": vel, "cust_amount_to_mean_ratio": 1.0, "device_is_new_for_cust": 1},
                })

        elif scenario.scenario_type == "ACCOUNT_TAKEOVER_ATTACK":
            # High-value transactions from novel unrecognized device on 5 established customers
            for i in range(10):
                t_ts = (base_time + timedelta(minutes=i*3)).strftime("%Y-%m-%d %H:%M:%S")
                transactions.append({
                    "transaction_id": f"SIM-ATO-{i+1:03d}",
                    "timestamp": t_ts,
                    "amount": 18500.0,
                    "customer_id": f"CUST_VICTIM_{(i%5)+1}",
                    "device_id": "DEV_ATO_88",
                    "payment_instrument_id": f"PI_VICTIM_{(i%5)+1}",
                    "merchant_id": f"MERCH_JEWELRY_{(i%2)+1}",
                    "is_fraud": 1,
                    "ml_prob": 0.95,
                    "ring_score": 0.0,
                    "ring_cand": 0,
                    "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 5.8, "cust_amount_zscore": 3.4, "device_is_new_for_cust": 1},
                })

        elif scenario.scenario_type == "COORDINATED_RING_ATTACK":
            # Syndicate of 6 accounts sharing device and payment token
            for i in range(15):
                t_ts = (base_time + timedelta(minutes=i*4)).strftime("%Y-%m-%d %H:%M:%S")
                transactions.append({
                    "transaction_id": f"SIM-RING-{i+1:03d}",
                    "timestamp": t_ts,
                    "amount": 3200.0,
                    "customer_id": f"CUST_MULE_{(i%6)+1}",
                    "device_id": "DEV_RING_77",
                    "payment_instrument_id": "PI_RING_66",
                    "merchant_id": f"MERCH_ECOM_{(i%3)+1}",
                    "is_fraud": 1,
                    "ml_prob": 0.22,
                    "ring_score": 0.85 if i >= 2 else 0.0,
                    "ring_cand": 1 if i >= 2 else 0,
                    "features": {"pi_velocity_count_1h": 2, "cust_amount_to_mean_ratio": 1.2, "device_is_new_for_cust": 0, "device_customer_count": 6, "payment_instrument_customer_count": 6},
                })

        # 2. Evaluate transactions through PolicyEngine and CaseManager
        decisions_list = []
        cases_created = []
        first_detection_time = None
        total_fraud_prevented = 0.0

        for t in transactions:
            dec_record = self.policy_engine.evaluate(
                transaction_id=t["transaction_id"],
                timestamp=t["timestamp"],
                amount=t["amount"],
                ml_probability=t["ml_prob"],
                graph_ring_score=t["ring_score"],
                graph_ring_candidate=t["ring_cand"],
                feature_context=t["features"],
            )

            d_dict = dec_record.to_dict()
            decisions_list.append(d_dict)

            # Create case if REVIEW or HOLD
            if dec_record.is_intervention:
                if first_detection_time is None and t["is_fraud"] == 1:
                    first_detection_time = t["timestamp"]
                total_fraud_prevented += t["amount"]

                case = self.case_manager.create_case_from_decision(
                    decision_record=d_dict,
                    transaction_data=t,
                    graph_data={"graph_ring_score": t["ring_score"], "graph_ring_candidate": t["ring_cand"]},
                )
                if case:
                    cases_created.append(case)

        # 3. Trigger investigation on the highest priority case
        sample_report = None
        if cases_created:
            lead_case = cases_created[0]
            sample_report = self.case_manager.investigate_case(lead_case.case_id)

        # 4. Formulate Actionable Recovery Recommendations
        recovery_recs = []
        if scenario.scenario_type == "CARD_TESTING_ATTACK":
            recovery_recs = [
                "Recommend temporary authorization rate-limit on payment instrument token PI_BOT_99.",
                "Enforce CAPTCHA challenge at merchant checkout for high-velocity payment tokens.",
                "Notify acquiring gateway to verify BIN-level authorization frequency.",
            ]
        elif scenario.scenario_type == "ACCOUNT_TAKEOVER_ATTACK":
            recovery_recs = [
                "Recommend session termination and password reset for victim accounts.",
                "Enforce mandatory step-up 2FA on unrecognized device hardware token DEV_ATO_88.",
                "Review recent authorization history across all 5 affected customer profiles.",
            ]
        elif scenario.scenario_type == "COORDINATED_RING_ATTACK":
            recovery_recs = [
                "Recommend placing temporary risk hold on connected entity cluster [DEV_RING_77, PI_RING_66].",
                "Audit merchant acquiring terminals for coordinated collusive cash-out patterns.",
                "Cross-reference KYC identity documents across the 6 linked customer profiles.",
            ]
        else:
            recovery_recs = ["No containment actions required; system operating within normal baseline parameters."]

        # 5. Compute Scenario Metrics
        n_txns = len(transactions)
        n_fraud = sum(1 for t in transactions if t["is_fraud"] == 1)
        n_appr = sum(1 for d in decisions_list if d["decision"] == "APPROVE")
        n_chal = sum(1 for d in decisions_list if d["decision"] == "CHALLENGE")
        n_rev = sum(1 for d in decisions_list if d["decision"] == "REVIEW")
        n_hold = sum(1 for d in decisions_list if d["decision"] == "HOLD")

        return {
            "scenario": {
                "name": scenario.name,
                "type": scenario.scenario_type,
                "description": scenario.description,
                "start_time": scenario.start_time,
                "attack_details": scenario.attack_description,
            },
            "metrics": {
                "total_transactions": n_txns,
                "fraud_transactions": n_fraud,
                "approved_count": n_appr,
                "challenge_count": n_chal,
                "review_count": n_rev,
                "hold_count": n_hold,
                "investigation_cases_created": len(cases_created),
                "first_detection_timestamp": first_detection_time or "N/A",
                "fraud_loss_prevented_inr": round(total_fraud_prevented, 2),
            },
            "decisions_summary": {
                "APPROVE": n_appr,
                "CHALLENGE": n_chal,
                "REVIEW": n_rev,
                "HOLD": n_hold,
            },
            "decisions": decisions_list,
            "sample_investigation_report": sample_report.to_dict() if sample_report else None,
            "recovery_recommendations": recovery_recs,
        }
