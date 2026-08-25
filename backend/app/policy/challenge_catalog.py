"""
SentinelRisk — Deterministic Challenge Catalog & Friction Orchestrator

Defines standardized, simulated step-up challenge types and evidence-grounded
challenge selection logic.

Safety Boundary:
  This is a DEFENSE-ONLY risk simulation. No real payment blocking, 3DS authentication,
  or SMS/OTP delivery is executed. The challenge recommendation represents the optimal
  least-friction action to reduce expected fraud loss.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ChallengeCode(str, Enum):
    """Catalog of supported simulated step-up challenge mechanisms."""
    CHALLENGE_DEVICE_VERIFICATION = "CHALLENGE_DEVICE_VERIFICATION"
    CHALLENGE_CUSTOMER_CONFIRMATION = "CHALLENGE_CUSTOMER_CONFIRMATION"
    CHALLENGE_PAYMENT_REAUTH = "CHALLENGE_PAYMENT_REAUTH"


@dataclass
class ChallengeRecommendation:
    """Structured challenge recommendation attached to CHALLENGE decisions."""
    challenge_code: str
    name: str
    description: str
    friction_level: str  # LOW, MEDIUM, HIGH
    reason: str
    recommended_for: str

    def to_dict(self) -> dict[str, Any]:
        """Convert recommendation to JSON-serializable dictionary."""
        return {
            "challenge_code": self.challenge_code,
            "code": self.challenge_code,  # Alias for convenience
            "name": self.name,
            "description": self.description,
            "friction_level": self.friction_level,
            "reason": self.reason,
            "recommended_for": self.recommended_for,
        }


CHALLENGE_CATALOG: dict[ChallengeCode, ChallengeRecommendation] = {
    ChallengeCode.CHALLENGE_DEVICE_VERIFICATION: ChallengeRecommendation(
        challenge_code=ChallengeCode.CHALLENGE_DEVICE_VERIFICATION.value,
        name="Step-Up Device Verification",
        description="Secondary verification prompt (e.g. Device Token confirmation via email/push) for novel hardware.",
        friction_level="LOW",
        reason="Unrecognized hardware device signature with elevated transaction amount.",
        recommended_for="Unrecognized hardware device with moderate spend novelty.",
    ),
    ChallengeCode.CHALLENGE_CUSTOMER_CONFIRMATION: ChallengeRecommendation(
        challenge_code=ChallengeCode.CHALLENGE_CUSTOMER_CONFIRMATION.value,
        name="Customer Step-Up Confirmation",
        description="Out-of-band mobile notification or biometric verification for abnormal customer ticket sizes.",
        friction_level="LOW",
        reason="Unusual customer spending deviation exceeding historical average order value.",
        recommended_for="Spending deviation on established customer account.",
    ),
    ChallengeCode.CHALLENGE_PAYMENT_REAUTH: ChallengeRecommendation(
        challenge_code=ChallengeCode.CHALLENGE_PAYMENT_REAUTH.value,
        name="Payment Instrument Dynamic 3DS2 Challenge",
        description="Dynamic 3DS2 Step-Up authentication challenge (CVV/OTP) for velocity bursts.",
        friction_level="MEDIUM",
        reason="Elevated authorization frequency observed on payment instrument token.",
        recommended_for="Payment instrument velocity burst across merchant terminals.",
    ),
}


def select_challenge_type(
    feature_context: dict[str, Any] | None = None,
    signals_triggered: list[str] | None = None,
    amount: float = 0.0,
) -> ChallengeRecommendation:
    """
    Evidence-grounded deterministic challenge selection.
    Chooses the least-friction challenge that addresses the primary observed risk anomaly.
    """
    ctx = feature_context or {}
    signals = list(signals_triggered or [])

    dev_new = int(ctx.get("device_is_new_for_cust", 0))
    pi_vel_1h = int(ctx.get("pi_velocity_count_1h", 0))
    cust_ratio = float(ctx.get("cust_amount_to_mean_ratio", 1.0))
    is_new_term = int(ctx.get("is_new_terminal_for_cust", 0))

    # Priority 1: Unrecognized hardware device anomaly
    if dev_new == 1 or "NEW_DEVICE" in str(signals) or is_new_term == 1:
        base = CHALLENGE_CATALOG[ChallengeCode.CHALLENGE_DEVICE_VERIFICATION]
        return ChallengeRecommendation(
            challenge_code=base.challenge_code,
            name=base.name,
            description=base.description,
            friction_level=base.friction_level,
            reason=f"Unrecognized device token detected for transaction amount ₹{amount:.2f}.",
            recommended_for=base.recommended_for,
        )

    # Priority 2: Payment instrument velocity burst
    if pi_vel_1h >= 2 or "MODERATE_PI_VELOCITY" in signals or "VELOCITY" in str(signals):
        base = CHALLENGE_CATALOG[ChallengeCode.CHALLENGE_PAYMENT_REAUTH]
        return ChallengeRecommendation(
            challenge_code=base.challenge_code,
            name=base.name,
            description=base.description,
            friction_level=base.friction_level,
            reason=f"Payment instrument velocity ({pi_vel_1h} txns/hr) requires dynamic 3DS2 re-authentication.",
            recommended_for=base.recommended_for,
        )

    # Priority 3: Customer spending anomaly
    if cust_ratio >= 2.5 or "AMOUNT_ANOMALY" in str(signals):
        base = CHALLENGE_CATALOG[ChallengeCode.CHALLENGE_CUSTOMER_CONFIRMATION]
        return ChallengeRecommendation(
            challenge_code=base.challenge_code,
            name=base.name,
            description=base.description,
            friction_level=base.friction_level,
            reason=f"Ticket size (₹{amount:.2f}) is {cust_ratio:.1f}x customer historical mean.",
            recommended_for=base.recommended_for,
        )

    # Default baseline challenge
    base = CHALLENGE_CATALOG[ChallengeCode.CHALLENGE_CUSTOMER_CONFIRMATION]
    return ChallengeRecommendation(
        challenge_code=base.challenge_code,
        name=base.name,
        description=base.description,
        friction_level=base.friction_level,
        reason=f"Mild risk anomaly detected; step-up verification requested.",
        recommended_for=base.recommended_for,
    )
