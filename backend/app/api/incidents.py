"""
SentinelRisk — Incident Simulation & Recovery API

Provides endpoints to run offline "What broke at 2 AM" incident simulations
and retrieve containment & recovery recommendations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from simulation.incident_simulator.simulator import IncidentSimulator
from simulation.incident_simulator.scenarios import SCENARIOS

router = APIRouter(prefix="/incidents", tags=["Incidents"])
simulator = IncidentSimulator()


class IncidentSimulationRequest(BaseModel):
    scenario: str = Field("CARD_TESTING_ATTACK", json_schema_extra={"example": "CARD_TESTING_ATTACK"})


@router.get("/scenarios")
async def list_scenarios():
    """List available offline incident simulation scenarios."""
    return {
        "scenarios": [
            {
                "key": k,
                "name": v.name,
                "type": v.scenario_type,
                "description": v.description,
                "start_time": v.start_time,
                "attack_details": v.attack_description,
            }
            for k, v in SCENARIOS.items()
        ]
    }


@router.post("/simulate")
async def simulate_incident(req: IncidentSimulationRequest):
    """
    Run an offline incident simulation scenario and return detection trace,
    sample investigation report, and recovery recommendations.
    """
    if req.scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario '{req.scenario}'. Available: {list(SCENARIOS.keys())}"
        )
    return simulator.run_scenario(req.scenario)
