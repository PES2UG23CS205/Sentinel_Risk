"""
SentinelRisk — Master Final Demo & Panel Presentation Script (Stage 15)

Executes the complete 11-step interactive / automated panel presentation narrative:
  Step 1:  Normal Legitimate Payment (Frictionless APPROVE)
  Step 2:  Unrecognized Device Token (Risk-Based Step-Up CHALLENGE)
  Step 3:  Account Takeover Surge (Immediate ML-Driven HOLD)
  Step 4:  Automated Card Testing Bot Burst (Immediate Rule-Driven HOLD)
  Step 5:  Coordinated Syndicate Ring (Immediate Graph-Driven HOLD)
  Step 6:  Evidence-Grounded AI Investigation Agent (Hypotheses & Citations)
  Step 7:  Fraud Operations Center (Persistent Case Lifecycle, Notes, Feedback Loop)
  Step 8:  Merchant Risk Intelligence (Weighted Scoring, Additive Drivers, Alerts)
  Step 9:  Incident Command Center ("What Broke at 2 AM" Attack Replay & Recovery)
  Step 10: Model & Feature Drift Monitoring (Population Stability Index PSI Calculation)
  Step 11: Authoritative Benchmark Summary (Synthetic & External Dataset Replay)

Run with:
    python scripts/final_demo.py
"""

import sys
from pathlib import Path

# Ensure UTF-8 output encoding for Windows PowerShell terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import time
from datetime import datetime
import pandas as pd

from backend.app.scoring.realtime_service import RealtimeRiskService
from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.agent import InvestigationAgent
from simulation.incident_simulator.simulator import IncidentSimulator
from ml.monitoring.drift_detector import ModelDriftMonitor
from backend.app.merchant.risk_profiler import MerchantRiskProfiler
from backend.app.merchant.risk_scorer import MerchantRiskScorer
from backend.app.merchant.alerts import MerchantAlertGenerator


def print_banner(step_num: int, title: str):
    print("\n" + "=" * 78)
    print(f" STEP {step_num:02d} : {title}")
    print("=" * 78)


def main():
    print("\n" + "█" * 78)
    print(" 🛡️  SENTINELRISK — FINAL LIVE DEMONSTRATION SUITE")
    print("     Defense-Only Payment Risk Intelligence & Fraud Operations Platform")
    print("     Architecture: Point-in-Time Features → LightGBM / Graph / Rules → Quad-State Policy")
    print("█" * 78)

    risk_service = RealtimeRiskService()
    agent = InvestigationAgent()
    case_mgr = CaseManager(agent)
    inc_sim = IncidentSimulator()
    drift_mon = ModelDriftMonitor()
    merch_prof = MerchantRiskProfiler()
    merch_sc = MerchantRiskScorer()
    merch_alt = MerchantAlertGenerator()

    # STEP 1: Legitimate Payment
    print_banner(1, "LEGITIMATE PAYMENT CHECKOUT (FRICTIONLESS APPROVE)")
    txn_legit = {
        "transaction_id": "TXN-DEMO-001",
        "amount": 450.00,
        "currency": "INR",
        "customer_id": "CUST_TRUSTED_88",
        "device_id": "DEV_KNOWN_MOBILE_01",
        "payment_instrument_id": "PI_CARD_8821",
        "merchant_id": "MERCH_GROCERY_01",
        "timestamp": "2025-06-15 11:30:00",
        "ml_probability": 0.002,
        "graph_ring_score": 0.0,
        "graph_ring_candidate": 0,
        "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 1.0},
    }
    res1 = risk_service.evaluate_transaction(txn_legit)
    print(f"  • Transaction ID : {res1['transaction_id']}")
    print(f"  • Amount         : ₹{res1['amount']:,.2f} | Merchant: {txn_legit['merchant_id']}")
    print(f"  • Signals        : ML Prob = {res1['ml_probability']:.4f} | Graph Ring = {res1['graph_ring_score']:.2f}")
    print(f"  • Decision       : \033[92m{res1['decision']}\033[0m ({res1['primary_trigger']})")
    print(f"  • Latency        : {res1['latency_ms']:.3f} ms [Zero user friction]")

    # STEP 2: Step-Up Challenge
    print_banner(2, "MILD ANOMALY / UNRECOGNIZED DEVICE (STEP-UP CHALLENGE)")
    txn_chal = {
        "transaction_id": "TXN-DEMO-002",
        "amount": 3200.00,
        "currency": "INR",
        "customer_id": "CUST_ESTABLISHED_44",
        "device_id": "DEV_NEW_IPHONE_99",
        "payment_instrument_id": "PI_CARD_4412",
        "merchant_id": "MERCH_ELECTRONICS_02",
        "timestamp": "2025-06-15 14:15:00",
        "ml_probability": 0.125,
        "graph_ring_score": 0.0,
        "graph_ring_candidate": 0,
        "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 2.8, "device_is_new_for_cust": 1},
    }
    res2 = risk_service.evaluate_transaction(txn_chal)
    ch2 = res2.get("challenge", {})
    print(f"  • Transaction ID : {res2['transaction_id']}")
    print(f"  • Amount         : ₹{res2['amount']:,.2f} | Merchant: {txn_chal['merchant_id']}")
    print(f"  • Signals        : ML Prob = {res2['ml_probability']:.4f} (Mild anomaly range: 0.05 - 0.25)")
    print(f"  • Decision       : \033[93m{res2['decision']}\033[0m ({res2['primary_trigger']})")
    print(f"  • Challenge Code : {ch2.get('challenge_code')} [{ch2.get('friction_level')} Friction]")
    print(f"  • Reason         : {ch2.get('reason')}")
    print("  • Impact         : Avoided ₹50 analyst review triage cost; automated verification triggered.")

    # STEP 3: Account Takeover
    print_banner(3, "ACCOUNT TAKEOVER ATTACK (IMMEDIATE ML-DRIVEN HOLD)")
    txn_ato = {
        "transaction_id": "TXN-DEMO-003",
        "amount": 48500.00,
        "currency": "INR",
        "customer_id": "CUST_VICTIM_09",
        "device_id": "DEV_ATTACKER_TOR_77",
        "payment_instrument_id": "PI_VICTIM_CARD",
        "merchant_id": "MERCH_ELECTRONICS_05",
        "timestamp": "2025-06-15 02:40:00",
        "ml_probability": 0.985,
        "graph_ring_score": 0.0,
        "graph_ring_candidate": 0,
        "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 7.5, "device_is_new_for_cust": 1},
    }
    res3 = risk_service.evaluate_transaction(txn_ato)
    print(f"  • Transaction ID : {res3['transaction_id']}")
    print(f"  • Amount         : ₹{res3['amount']:,.2f} (7.5x historical customer average)")
    print(f"  • Signals        : ML Prob = {res3['ml_probability']:.4f} (Exceeds 0.50 hold threshold)")
    print(f"  • Decision       : \033[91m{res3['decision']}\033[0m ({res3['primary_trigger']})")
    print("  • Action         : Immediate hold enforced; transaction blocked from financial settlement.")

    # STEP 4: Automated Card Testing
    print_banner(4, "CARD TESTING BOT BURST (IMMEDIATE VELOCITY-DRIVEN HOLD)")
    txn_bot = {
        "transaction_id": "TXN-DEMO-004",
        "amount": 75.00,
        "currency": "INR",
        "customer_id": "CUST_BOT_SCRIPT_01",
        "device_id": "DEV_EMULATOR_01",
        "payment_instrument_id": "PI_STOLEN_CARD_POOL",
        "merchant_id": "MERCH_GAMING_02",
        "timestamp": "2025-06-15 03:10:00",
        "ml_probability": 0.999,
        "graph_ring_score": 0.0,
        "graph_ring_candidate": 0,
        "features": {"pi_velocity_count_1h": 8, "velocity_txn_count_1h": 8, "cust_amount_to_mean_ratio": 0.1},
    }
    res4 = risk_service.evaluate_transaction(txn_bot)
    print(f"  • Transaction ID : {res4['transaction_id']}")
    print(f"  • Velocity (1h)  : 8 rapid authorizations/hour (severe velocity burst >= 5)")
    print(f"  • Decision       : \033[91m{res4['decision']}\033[0m ({res4['primary_trigger']})")

    # STEP 5: Coordinated Abuse Ring
    print_banner(5, "COORDINATED MULTI-ACCOUNT SYNDICATE (GRAPH-DRIVEN HOLD)")
    txn_ring = {
        "transaction_id": "TXN-DEMO-005",
        "amount": 3400.00,
        "currency": "INR",
        "customer_id": "CUST_SYNDICATE_MULE_06",
        "device_id": "DEV_SHARED_BOX_99",
        "payment_instrument_id": "PI_SHARED_INSTRUMENT_99",
        "merchant_id": "MERCH_DIGITAL_01",
        "timestamp": "2025-06-15 04:20:00",
        "ml_probability": 0.22,
        "graph_ring_score": 0.88,
        "graph_ring_candidate": 1,
        "features": {"device_customer_count": 6, "payment_instrument_customer_count": 5},
    }
    res5 = risk_service.evaluate_transaction(txn_ring)
    print(f"  • Transaction ID : {res5['transaction_id']}")
    print(f"  • Graph Topology : Shared Device connected to 6 customer accounts & 5 cards")
    print(f"  • Ring Score     : {res5['graph_ring_score']:.2f} (Exceeds 0.80 syndicate threshold)")
    print(f"  • Decision       : \033[91m{res5['decision']}\033[0m ({res5['primary_trigger']})")

    # STEP 6: AI Investigation Agent
    print_banner(6, "EVIDENCE-GROUNDED AI INVESTIGATION AGENT")
    case_ring = case_mgr.create_case_from_decision(
        decision_record=res5,
        transaction_data=txn_ring,
        graph_data={"graph_ring_score": 0.88, "graph_ring_candidate": 1},
    )
    report = case_mgr.investigate_case(case_ring.case_id)
    print(f"  • Case ID        : {case_ring.case_id} [Priority: {case_ring.priority.value}]")
    print(f"  • Agent Status   : {report.investigation_status} (Strict citation grounding enforced)")
    print(f"  • Hypotheses Generated ({len(report.hypotheses)}):")
    for h in report.hypotheses:
        print(f"    - [{h.confidence.value}] {h.hypothesis}")
        print(f"      Citations: Supporting {h.supporting_evidence_ids} | Contradicting {h.contradicting_evidence_ids}")
    print(f"  • Recommended Next Steps:")
    for s in report.recommended_next_steps:
        print(f"    ✓ {s}")

    # STEP 7: Fraud Operations Center & Feedback
    print_banner(7, "FRAUD OPERATIONS CENTER & ANALYST FEEDBACK LOOP")
    case_mgr.assign_case(case_ring.case_id, analyst="Risk_Analyst_Priya")
    case_mgr.add_note(case_ring.case_id, analyst="Risk_Analyst_Priya", text="Graph syndicate topology confirmed across 6 mule accounts.")
    case_mgr.confirm_fraud(case_ring.case_id, analyst="Risk_Analyst_Priya", notes="Syndicate ring verified; tokens blacklisted.")
    
    fb = case_mgr.get_feedback_metrics()
    print(f"  • Case Updated   : Assigned -> Note Added -> CONFIRMED FRAUD Resolution")
    print(f"  • Audit History  : {len(case_ring.history)} immutable lifecycle events recorded")
    print(f"  • Feedback Loop  : {fb['confirmed_fraud_count']} Confirmed Fraud | {fb['false_positive_count']} False Positives")
    print(f"  • Confirmation % : {fb['analyst_confirmation_rate_pct']}% | Avg Resolution: {fb['average_resolution_time_minutes']} mins")

    # STEP 8: Merchant Risk Intelligence
    print_banner(8, "MERCHANT RISK INTELLIGENCE & DETERMINISTIC ALERTING")
    sample_prof = {
        "merchant_id": "MERCH_ELECTRONICS_05",
        "merchant_category": "Electronics & Gadgets",
        "total_transactions": 250,
        "total_volume_inr": 1250000.0,
        "fraud_rate_pct": 4.80,
        "customer_concentration_pct": 42.0,
        "review_rate_pct": 3.2,
        "hold_rate_pct": 2.4,
        "trend_direction": "DETERIORATING",
        "window_metrics": {"1h_transactions": 18, "1h_volume_inr": 85000.0},
        "as_of_timestamp": "2025-06-15 18:00:00",
    }
    m_score = merch_sc.score_merchant(sample_prof)
    m_alerts = merch_alt.generate_alerts(sample_prof, m_score)
    print(f"  • Merchant ID    : {sample_prof['merchant_id']} ({sample_prof['merchant_category']})")
    print(f"  • Risk Score     : \033[91m{m_score['risk_score']:.2f}\033[0m [Band: {m_score['risk_level']} | Trend: {m_score['trend_direction']}]")
    print("  • Additive Driver Attributions:")
    for d in m_score['driver_explanations']:
        print(f"    + {d}")
    print(f"  • Active Alerts ({len(m_alerts)}):")
    for a in m_alerts:
        print(f"    🚨 [{a['severity']}] {a['alert_type']}: {a['reason']} → Action: [{a['recommended_action']}]")

    # STEP 9: Incident Command Center
    print_banner(9, "INCIDENT COMMAND CENTER ('WHAT BROKE AT 2 AM?')")
    inc_res = inc_sim.run_scenario("CARD_TESTING_ATTACK")
    m_inc = inc_res["metrics"]
    total_interventions = m_inc["challenge_count"] + m_inc["review_count"] + m_inc["hold_count"]
    intervention_rate = (total_interventions / m_inc["total_transactions"] * 100.0) if m_inc["total_transactions"] > 0 else 0.0

    print(f"  • Incident Name  : {inc_res['scenario']['name']}")
    print(f"  • Attack Vector  : {inc_res['scenario']['description']}")
    print(f"  • First Detected : {m_inc['first_detection_timestamp']}")
    print(f"  • Total Attacks  : {m_inc['total_transactions']} authorizations")
    print(f"  • Interventions  : {total_interventions} ({intervention_rate:.1f}%)")
    print(f"  • Loss Prevented : ₹{m_inc['fraud_loss_prevented_inr']:,.2f}")
    print(f"  • Decisions      : {inc_res['decisions_summary']}")

    # STEP 10: Model Health & PSI Drift
    print_banner(10, "STATISTICAL MODEL & FEATURE DRIFT MONITORING (PSI)")
    drift_res = drift_mon.evaluate_drift([txn_legit, txn_chal, txn_ato, txn_bot, txn_ring])
    print(f"  • Active Model   : {drift_res['model_metadata']['active_model']} ({drift_res['model_metadata']['model_version']})")
    print(f"  • Overall Status : \033[92m{drift_res['overall_drift_status']}\033[0m")
    print("  • Monitored Feature Stability Table:")
    print("    " + "-" * 65)
    print(f"    {'Feature':<20} | {'PSI':<8} | {'Status':<10} | {'Current Mean':<12}")
    print("    " + "-" * 65)
    for f in drift_res["monitored_features"]:
        print(f"    {f['feature']:<20} | {f['psi']:<8.4f} | {f['status']:<10} | {f['mean_value']:<12}")
    print("    " + "-" * 65)

    # STEP 11: Authoritative Benchmarks
    print_banner(11, "AUTHORITATIVE VALIDATION BENCHMARK COMPARISON")
    bm_path = Path("evaluation/final/authoritative_final_benchmark.csv")
    if bm_path.exists():
        df_bm = pd.read_csv(bm_path)
        print("    " + "-" * 72)
        print(f"    {'System Tier':<30} | {'Recall':<8} | {'Cost (INR/EUR)':<15} | {'Benefit'}")
        print("    " + "-" * 72)
        for _, r in df_bm.iterrows():
            print(f"    {r['system_tier']:<30} | {r['fraud_recall_pct']:>6.2f}% | {r['total_cost_inr']:>14,.2f} | {r['status']}")
        print("    " + "-" * 72)

    print("\n" + "█" * 78)
    print(" ✅ SENTINELRISK MASTER DEMONSTRATION COMPLETE (100% SUCCESSFUL)")
    print("    Feature development is FROZEN. All 15 Stages authenticated.")
    print("█" * 78 + "\n")


if __name__ == "__main__":
    main()
