"""
SentinelRisk — Merchant Risk Intelligence API (Stage 14)

Provides endpoints for:
  - Listing merchant risk profiles and risk distributions
  - Retrieving detailed merchant risk scores with additive driver attributions
  - Querying deterministic merchant alerts
  - Performing deep drill-down into merchant transactions, top customers, and linked fraud cases
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
from pathlib import Path

from backend.app.merchant.risk_profiler import MerchantRiskProfiler
from backend.app.merchant.risk_scorer import MerchantRiskScorer
from backend.app.merchant.alerts import MerchantAlertGenerator
from backend.app.api.cases import case_manager

router = APIRouter(prefix="/merchants", tags=["Merchants"])

# Singleton instances
profiler = MerchantRiskProfiler()
scorer = MerchantRiskScorer()
alert_gen = MerchantAlertGenerator()

# Load historical database transactions into profiler on module load
def _load_initial_merchant_data():
    csv_path = Path("data/raw/synthetic/transactions.csv")
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            profiler.load_transactions(df)
        except Exception:
            pass

_load_initial_merchant_data()


@router.get("")
@router.get("/")
async def list_merchants(
    risk_level: Optional[str] = Query(None, description="Filter by risk level (HIGH, MEDIUM, LOW)"),
    category: Optional[str] = Query(None, description="Filter by merchant category"),
    limit: int = Query(25, description="Number of merchants to return"),
):
    """List merchant risk profiles, scores, and active alert counts."""
    if profiler.tx_df is None or profiler.tx_df.empty:
        # Return default top merchants list
        sample_ids = ["MERCH_ELECTRONICS_01", "MERCH_GAMING_02", "MERCH_DIGITAL_01", "MERCH_GROCERY_01", "MERCH_JEWELRY_01"]
        items = []
        for mid in sample_ids:
            prof = profiler.profile_merchant(mid)
            sc = scorer.score_merchant(prof)
            al = alert_gen.generate_alerts(prof, sc)
            items.append({**prof, **sc, "active_alerts_count": len(al)})
        return {"total_merchants": len(items), "merchants": items}

    unique_merchs = profiler.tx_df["merchant_id"].unique()
    merchants_list = []

    for mid in unique_merchs[:limit*2]:
        prof = profiler.profile_merchant(mid)
        sc = scorer.score_merchant(prof)
        al = alert_gen.generate_alerts(prof, sc)

        if risk_level and sc.get("risk_level") != risk_level.upper():
            continue
        if category and prof.get("merchant_category") != category:
            continue

        merchants_list.append({
            **prof,
            **sc,
            "active_alerts_count": len(al),
        })

        if len(merchants_list) >= limit:
            break

    # Sort by risk score descending
    merchants_list.sort(key=lambda x: x.get("risk_score", 0.0), reverse=True)
    return {
        "total_merchants": len(merchants_list),
        "merchants": merchants_list,
    }


@router.get("/{merchant_id}")
async def get_merchant_profile(merchant_id: str):
    """Retrieve detailed merchant profile and interpretable risk score breakdown."""
    prof = profiler.profile_merchant(merchant_id)
    sc = scorer.score_merchant(prof)
    al = alert_gen.generate_alerts(prof, sc)
    return {
        **prof,
        **sc,
        "alerts": al,
    }


@router.get("/{merchant_id}/alerts")
async def get_merchant_alerts(merchant_id: str):
    """Retrieve active and historical risk alerts for a specific merchant."""
    prof = profiler.profile_merchant(merchant_id)
    sc = scorer.score_merchant(prof)
    alerts = alert_gen.generate_alerts(prof, sc)
    return {
        "merchant_id": merchant_id,
        "total_alerts": len(alerts),
        "alerts": alerts,
    }


@router.get("/{merchant_id}/drilldown")
async def get_merchant_drilldown(merchant_id: str):
    """
    Retrieve full drill-down data for merchant operations:
    Recent transactions, top customers, risk signals, related devices, and linked fraud cases.
    """
    prof = profiler.profile_merchant(merchant_id)
    sc = scorer.score_merchant(prof)
    alerts = alert_gen.generate_alerts(prof, sc)

    recent_txns = []
    top_customers = []
    related_devices = []

    if profiler.tx_df is not None and not profiler.tx_df.empty:
        df = profiler.tx_df[profiler.tx_df["merchant_id"].astype(str) == str(merchant_id)]
        if not df.empty:
            recent_txns = df.tail(10).to_dict(orient="records")
            if "customer_id" in df.columns:
                top_customers = df["customer_id"].value_counts().head(5).to_dict()
            if "device_id" in df.columns:
                related_devices = list(df["device_id"].dropna().unique()[:5])

    # Linked investigation cases
    linked_cases = [c.to_dict() for c in case_manager.cases.values() if str(c.merchant_id) == str(merchant_id)]

    return {
        "merchant_id": merchant_id,
        "profile": prof,
        "risk_score": sc,
        "alerts": alerts,
        "recent_transactions": recent_txns,
        "top_customers": top_customers,
        "related_devices": related_devices,
        "open_cases": linked_cases,
    }
