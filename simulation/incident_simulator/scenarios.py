"""
SentinelRisk — Incident Simulation Scenarios

Defines realistic, deterministic attack scenarios for the "What broke at 2 AM" incident demo:
  1. BASELINE: Normal diurnal legitimate payments traffic.
  2. CARD_TESTING_ATTACK: 02:00 AM automated bot velocity burst testing stolen PANs.
  3. ACCOUNT_TAKEOVER_ATTACK: 02:15 AM high-value spending surge from unrecognized hardware.
  4. COORDINATED_RING_ATTACK: 02:30 AM multi-account syndicate reusing shared device & cards.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class IncidentScenario:
    name: str
    scenario_type: Literal["BASELINE", "CARD_TESTING_ATTACK", "ACCOUNT_TAKEOVER_ATTACK", "COORDINATED_RING_ATTACK"]
    description: str
    start_time: str
    attack_description: str
    target_entities: dict[str, str]


SCENARIOS: dict[str, IncidentScenario] = {
    "BASELINE": IncidentScenario(
        name="Baseline Normal Traffic",
        scenario_type="BASELINE",
        description="Standard legitimate daytime payments traffic with no malicious activity.",
        start_time="2025-06-15 14:00:00",
        attack_description="None (control baseline).",
        target_entities={},
    ),
    "CARD_TESTING_ATTACK": IncidentScenario(
        name="2:00 AM Automated Card Testing Attack",
        scenario_type="CARD_TESTING_ATTACK",
        description="Bot script initiates high-frequency micro-authorizations testing stolen card tokens.",
        start_time="2025-06-15 02:00:00",
        attack_description="25 rapid transactions (₹50-₹150) on payment instrument PI_BOT_99 within 10 minutes.",
        target_entities={"payment_instrument_id": "PI_BOT_99", "device_id": "DEV_BOT_01"},
    ),
    "ACCOUNT_TAKEOVER_ATTACK": IncidentScenario(
        name="2:15 AM Credential Stuffing & ATO Surge",
        scenario_type="ACCOUNT_TAKEOVER_ATTACK",
        description="Fraudster accesses established high-value customer accounts via novel unrecognized device.",
        start_time="2025-06-15 02:15:00",
        attack_description="Unrecognized device DEV_ATO_88 initiating ₹15,000-₹25,000 transactions on 5 established accounts.",
        target_entities={"device_id": "DEV_ATO_88"},
    ),
    "COORDINATED_RING_ATTACK": IncidentScenario(
        name="2:30 AM Distributed Coordinated Abuse Ring",
        scenario_type="COORDINATED_RING_ATTACK",
        description="Syndicate creates multiple synthetic identities sharing infrastructure across merchants.",
        start_time="2025-06-15 02:30:00",
        attack_description="6 customer accounts sharing device DEV_RING_77 and payment instrument PI_RING_66.",
        target_entities={"device_id": "DEV_RING_77", "payment_instrument_id": "PI_RING_66"},
    ),
}
