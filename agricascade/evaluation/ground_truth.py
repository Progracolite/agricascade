"""Synthetic ground truth: known-chain scenarios for recovery tests."""
from __future__ import annotations
from typing import Any
from agricascade.schemas.scenario import Disturbance, Scenario

def monsoon_break_scenario(horizon: int = 14, seed: int = 42) -> Scenario:
    return Scenario(scenario_id="monsoon_break", name="Monsoon Break + Heat Stress",
        description="Killer demo: rainfall reduction + heat + ET increase.",
        disturbances=[
            Disturbance(type="rainfall_deficit", start_time=2, duration=horizon - 2,
                rainfall_multiplier=0.2, et_multiplier=1.25, temperature_delta=2.5,
                humidity_delta=-8.0, affected_state=("rainfall", "temperature"), spatial_scope="region")],
        horizon_days=horizon, seed=seed, start_of_season_day=60, source_type="synthetic")

def known_chain_monsoon_break() -> dict[str, Any]:
    from agricascade.cascade.transitions import NODES
    # Measured emergent chain for the seeded monsoon-break demo (realized
    # transitions only: edges already active at day 0 are not re-reported).
    chain = ["crop_stress->irrigation_demand",
        "irrigation_demand->water_reserve",
        "soil_water_root->crop_stress",
        "crop_stress->crop_health", "crop_stress->yield_risk"]
    assert all(s.split("->")[0] in NODES and s.split("->")[1] in NODES for s in chain)
    return {"scenario_id": "monsoon_break", "expected_transitions": chain,
        "expected_events": ["irrigation_demand_spike", "rainfall_deficit", "crop_stress_onset",
            "soil_moisture_decline", "water_reserve_depletion"],
        "expected_terminal": ["STRESSED", "SEVERE_STRESS", "CASCADE_ESCALATING", "RECOVERING"]}

def synthetic_suite() -> list[Scenario]:
    return [monsoon_break_scenario(14, 42),
        Scenario(scenario_id="normal", name="Normal", horizon_days=14, seed=42),
        Scenario(scenario_id="heavy_rain", name="Heavy Rain",
            disturbances=[Disturbance(type="heavy_rain", start_time=3, duration=3,
                rainfall_multiplier=3.0, affected_state=("rainfall",), spatial_scope="region")],
            horizon_days=14, seed=42)]
