"""Intervention simulation + scoring + ranking (spec 31-33, 38)."""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from typing import Any
from agricascade.cascade.simulator import CascadeTrajectory, simulate_cascade
from agricascade.schemas.intervention import Intervention
from agricascade.schemas.scenario import Scenario
from agricascade.schemas.state import AgriculturalState
from agricascade.state.updater import WeatherDay
from agricascade.utils.io import load_model_config, load_objective_config

@dataclass
class EvaluatedIntervention:
    intervention: Intervention
    trajectory: CascadeTrajectory
    damage_avoided: float = 0.0
    containment: float = 0.0
    score: float = 0.0
    def to_dict(self) -> dict[str, Any]:
        return {"intervention": self.intervention.to_dict(),
            "summary": self.trajectory.summary(), "damage_avoided": self.damage_avoided,
            "containment": self.containment, "score": self.score}

def containment_score(cm_base: float, cm_iv: float, eps: float = 1e-6) -> float:
    return float(1.0 - cm_iv / (cm_base + eps))

def score_intervention(damage_avoided: float, cost: float, resource_use: float,
        disruption: float, weights: dict[str, float]) -> float:
    return float(weights.get("damage_avoided", 1.0) * damage_avoided
        - weights.get("intervention_cost", 0.3) * cost
        - weights.get("resource_use", 0.2) * resource_use
        - weights.get("disruption", 0.1) * disruption)

def evaluate_interventions(initial_state: AgriculturalState, scenario: Scenario,
        interventions: list[Intervention], baseline: CascadeTrajectory,
        forecast: list[WeatherDay] | None = None, horizon_days: int = 14,
        seed: int = 42, soil_properties: dict[str, float] | None = None,
        config: dict[str, Any] | None = None) -> list[EvaluatedIntervention]:
    cfg = config or load_model_config()
    obj = load_objective_config()
    weights = obj.get("objective", {})
    reserve_total = float(cfg["irrigation"]["reserve_total_mm"])
    cm_base = baseline.cascade_magnitude()
    out: list[EvaluatedIntervention] = []
    for iv in interventions:
        traj = simulate_cascade(initial_state, scenario, forecast, horizon_days,
            seed, soil_properties, [iv], cfg)
        cm_iv = traj.cascade_magnitude()
        avoided = float((cm_base - cm_iv) / (cm_base + 1e-6))
        contained = containment_score(cm_base, cm_iv)
        resource = float(iv.resource_requirement / reserve_total) if reserve_total else 0.0
        score = score_intervention(avoided, iv.cost, resource, iv.disruption_score, weights)
        out.append(EvaluatedIntervention(iv, traj, avoided, contained, score))
    return out

def select_best_intervention(evaluated: list[EvaluatedIntervention]) -> EvaluatedIntervention | None:
    if not evaluated:
        return None
    return max(evaluated, key=lambda e: e.score)

def run_counterfactual(initial_state: AgriculturalState, scenario: Scenario,
        intervention: Intervention | None, baseline: CascadeTrajectory,
        forecast: list[WeatherDay] | None = None, horizon_days: int = 14,
        seed: int = 42, soil_properties: dict[str, float] | None = None,
        config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_model_config()
    ivs = [intervention] if intervention is not None else []
    traj = simulate_cascade(initial_state, scenario, forecast, horizon_days,
        seed, soil_properties, ivs, cfg)
    cm_base = baseline.cascade_magnitude(); cm_iv = traj.cascade_magnitude()
    b_last = baseline.states[-1]; c_last = traj.states[-1]
    return {"trajectory": traj, "containment": containment_score(cm_base, cm_iv),
        "intervention_value": float(cm_base - cm_iv),
        "comparison": {
            "baseline_peak": baseline.peak_severity(), "counterfactual_peak": traj.peak_severity(),
            "baseline_depth": baseline.cascade_depth(), "counterfactual_depth": traj.cascade_depth(),
            "baseline_reserve": b_last.water_reserve, "counterfactual_reserve": c_last.water_reserve,
            "baseline_yield_risk": b_last.yield_risk, "counterfactual_yield_risk": c_last.yield_risk,
            "baseline_terminal": baseline.terminal_state, "counterfactual_terminal": traj.terminal_state}}
