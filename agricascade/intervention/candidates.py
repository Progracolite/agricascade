"""Candidate intervention enumeration (spec sections 27-30)."""
from __future__ import annotations
from typing import Any
from agricascade.cascade.branches import BranchCandidate
from agricascade.schemas.intervention import Intervention
from agricascade.schemas.scenario import Scenario
from agricascade.utils.io import load_objective_config

def generate_interventions(branch: BranchCandidate | None = None,
        scenario: Scenario | None = None,
        config: dict[str, Any] | None = None) -> list[Intervention]:
    cfg = config or load_objective_config()
    iv = cfg.get("intervention", {})
    partial = float(iv.get("partial_irrigation_mm", 15.0))
    full = float(iv.get("full_irrigation_mm", 30.0))
    delayed = float(iv.get("delayed_irrigation_mm", 20.0))
    delay = int(iv.get("delay_days", 2))
    alloc_frac = float(iv.get("allocation_reserve_fraction", 0.15))
    app_days = int(iv.get("application_days", 2))
    cost_mm = float(iv.get("cost_per_mm", 0.02))
    day = int(branch.day) if branch is not None else 5
    cands = [
        Intervention(intervention_id="A-partial", type="partial_irrigation",
            start_time=day, duration=app_days, magnitude=partial,
            cost=partial * cost_mm, resource_requirement=partial,
            disruption_score=float(iv.get("disruption_partial", 0.15)),
            label=f"Simulated partial irrigation {partial:.0f} mm at day {day}"),
        Intervention(intervention_id="B-full", type="full_irrigation",
            start_time=day, duration=app_days, magnitude=full,
            cost=full * cost_mm, resource_requirement=full,
            disruption_score=float(iv.get("disruption_full", 0.35)),
            label=f"Simulated full irrigation {full:.0f} mm at day {day}"),
        Intervention(intervention_id="C-delayed", type="irrigation_delay",
            start_time=day + delay, duration=app_days, magnitude=delayed,
            cost=delayed * cost_mm, resource_requirement=delayed,
            disruption_score=float(iv.get("disruption_delay", 0.10)),
            label=f"Simulated delayed irrigation {delayed:.0f} mm at day {day + delay}"),
        Intervention(intervention_id="D-allocation", type="water_allocation",
            start_time=day, duration=app_days, magnitude=alloc_frac * 120.0,
            cost=alloc_frac * 120.0 * cost_mm, resource_requirement=alloc_frac * 120.0,
            disruption_score=float(iv.get("disruption_allocation", 0.05)),
            label=f"Simulated reserve allocation {alloc_frac:.0%} at day {day}"),
    ]
    return cands
