"""
SentinelRisk — Dataset Status API

Provides:
  GET /dataset/status                  → Synthetic simulation dataset statistics from SQLite
  GET /dataset/external/fraud-handbook → External Fraud Detection Handbook metadata & stats
  GET /datasets/external/fraud-handbook → Alias for external dataset metadata
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db.database import get_db
from backend.app.db.models import (
    Merchant, Customer, Device, PaymentInstrument,
    Transaction, Dispute
)
from backend.app.external_data.fraud_handbook_loader import FraudHandbookLoader

router = APIRouter(prefix="", tags=["Dataset"])

fraud_loader = FraudHandbookLoader()


@router.get("/dataset/status")
def get_dataset_status(db: Session = Depends(get_db)):
    """
    Get current database statistics for the synthetic payments ecosystem.
    Computes actual metrics from SQLite tables.
    """
    num_merchants = db.query(func.count(Merchant.id)).scalar() or 0
    num_customers = db.query(func.count(Customer.id)).scalar() or 0
    num_devices = db.query(func.count(Device.id)).scalar() or 0
    num_pis = db.query(func.count(PaymentInstrument.id)).scalar() or 0
    num_txns = db.query(func.count(Transaction.id)).scalar() or 0
    num_disputes = db.query(func.count(Dispute.id)).scalar() or 0

    is_seeded = num_txns > 0

    fraud_gt = 0
    fraud_obs = 0
    ato_count = 0
    ct_count = 0
    ring_count = 0
    fraud_prev_str = "0.00%"

    if is_seeded:
        fraud_gt = db.query(func.count(Transaction.id)).filter(Transaction.is_fraud_ground_truth == True).scalar() or 0
        fraud_obs = db.query(func.count(Transaction.id)).filter(Transaction.is_fraud == True).scalar() or 0
        ato_count = db.query(func.count(Transaction.id)).filter(Transaction.fraud_archetype == "account_takeover").scalar() or 0
        ct_count = db.query(func.count(Transaction.id)).filter(Transaction.fraud_archetype == "card_testing").scalar() or 0
        ring_count = db.query(func.count(Transaction.id)).filter(Transaction.fraud_archetype == "coordinated_ring").scalar() or 0

        fraud_prev = (fraud_gt / num_txns) if num_txns > 0 else 0.0
        fraud_prev_str = f"{fraud_prev * 100:.2f}%"

    return {
        "status": "ready" if is_seeded else "empty",
        "dataset_type": "Synthetic Simulation Data",
        "disclaimer": "This dataset is synthetic and used strictly for development and evaluation.",
        "is_seeded": is_seeded,
        "metrics": {
            "num_merchants": num_merchants,
            "num_customers": num_customers,
            "num_devices": num_devices,
            "num_payment_instruments": num_pis,
            "num_transactions": num_txns,
            "num_disputes": num_disputes,
            "fraud_transactions_ground_truth": fraud_gt,
            "fraud_transactions_observed": fraud_obs,
            "fraud_prevalence": fraud_prev_str,
            "account_takeover_count": ato_count,
            "card_testing_count": ct_count,
            "coordinated_ring_count": ring_count,
        }
    }


@router.get("/dataset/external/fraud-handbook")
@router.get("/datasets/external/fraud-handbook")
@router.get("/datasets/external/fraud-handbook/stats")
def get_external_fraud_handbook_stats():
    """
    Get external Fraud Detection Handbook simulated dataset statistics.
    """
    return fraud_loader.get_dataset_metadata()
