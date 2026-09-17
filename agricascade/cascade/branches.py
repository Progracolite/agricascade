"""Critical branch detection (spec sections 24-26)."""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from typing import Any
from agricascade.cascade.simulator import CascadeTrajectory, simulate_cascade
from agricascade.schemas.intervention import Intervention
from agricascade.schemas.scenario import Scenario
from agricascade.schemas.state import AgriculturalState
from agricascade.state.updater import WeatherDay

@dataclass
class BranchCandidate:
    day: int
    root_moisture: float
    sensitivity: float
    baseline_outcome: float
    alternate_outcomes: dict[str, float] = dc_field(default_factory=dict)
    branch_score: float = 0.0
    is_critical: bool = False
    reason: str = ""
    def to_dict(self) -> dict[str, Any]:
        return {"day": self.day, "root_moisture": self.root_moisture,
            "sensitivity": self.sensitivity, "baseline_outcome": self.baseline_outcome,
            "alternate_outcomes": dict(self.alternate_outcomes),
            "branch_score": self.branch_score, "is_critical": self.is_critical,
            "reason": self.reason}

def _outcome(trajectory: CascadeTrajectory) -> float:
    if not trajectory.states:
        return 0.0
    return float(trajectory.states[-1].yield_risk)

def branch_sensitivity(baseline: float, alternates: list[float], eps: float = 0.05) -> float:
    if not alternates:
        return 0.0
    return float((max(alternates) - min(alternates)) / (abs(baseline) + eps))

def detect_critical_branches(baseline: CascadeTrajectory,
        initial_state: AgriculturalState, scenario: Scenario,
        forecast: list[WeatherDay] | None = None, horizon_days: int = 14,
        seed: int = 42, soil_properties: dict[str, float] | None = None,
        config: dict[str, Any] | None = None) -> list[BranchCandidate]:
    """Probe each day: re-simulate tail with wetter/drier root state."""
    from agricascade.utils.io import load_model_config
    cfg = config or load_model_config()
    b_cfg = cfg.get("branches", {})
    thr = float(b_cfg.get("sensitivity_threshold", 0.25))
    min_day = int(b_cfg.get("min_day", 1))
    eps = float(b_cfg.get("baseline_epsilon", 0.05))
    out: list[BranchCandidate] = []
    base_outcome = _outcome(baseline)
    states = baseline.states
    for day in range(min_day, min(len(states) - 1, horizon_days)):
        st = states[day]
        # alternate initial states for remainder: +/- 0.04 root moisture
        cands: dict[str, float] = {}
        for label, delta in (("drier", -0.04), ("wetter", 0.04)):
            alt_init = st.with_updates(soil_moisture_root=float(
                max(0.05, min(0.45, st.soil_moisture_root + delta))))
            tail_len = horizon_days - day
            tail_scenario = Scenario(scenario_id=scenario.scenario_id + f"-tail-d{day}",
                name=scenario.name, disturbances=scenario.disturbances,
                horizon_days=tail_len, seed=seed,
                start_of_season_day=scenario.start_of_season_day + day)
            tail_fc = forecast[day:day + tail_len] if forecast else None
            if tail_fc is not None:
                for w in tail_fc:
                    w.day = w.day - day
            traj = simulate_cascade(alt_init, tail_scenario, tail_fc, tail_len,
                seed, soil_properties, None, cfg)
            cands[label] = _outcome(traj)
        alts = list(cands.values()) + [base_outcome]
        bs = branch_sensitivity(base_outcome, alts, eps)
        critical = bs > thr and st.crop_water_stress < 0.75
        out.append(BranchCandidate(day=day, root_moisture=st.soil_moisture_root,
            sensitivity=bs, baseline_outcome=base_outcome,
            alternate_outcomes=cands, branch_score=bs, is_critical=critical,
            reason=f"BS={bs:.2f} vs threshold {thr:.2f}; root={st.soil_moisture_root:.2f}"))
    return out

def select_critical_branch(cands: list[BranchCandidate]) -> BranchCandidate | None:
    crit = [c for c in cands if c.is_critical]
    if not crit:
        return None
    return max(crit, key=lambda c: c.sensitivity)
