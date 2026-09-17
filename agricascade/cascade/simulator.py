"""Deterministic cascade simulator (spec sections 20-21)."""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from datetime import timedelta
from typing import Any
import networkx as nx
from agricascade.cascade.events import detect_threshold_crossings
from agricascade.cascade.graph import build_cascade_graph
from agricascade.cascade.transitions import edge_depth, propagate_dependencies
from agricascade.schemas.event import CascadeEvent
from agricascade.schemas.intervention import Intervention
from agricascade.schemas.scenario import Scenario
from agricascade.schemas.state import AgriculturalState
from agricascade.schemas.transition import StateTransition
from agricascade.state.updater import WeatherDay, step_state
from agricascade.utils.io import load_crop_config, load_model_config
from agricascade.utils.random import child_seed, make_rng
TERMINAL_STATES = ("STABLE", "RECOVERING", "STRESSED", "SEVERE_STRESS",
    "CASCADE_CONTAINED", "CASCADE_ESCALATING")

@dataclass
class CascadeTrajectory:
    states: list[AgriculturalState] = dc_field(default_factory=list)
    activated_edges: list[dict[str, Any]] = dc_field(default_factory=list)
    events: list[CascadeEvent] = dc_field(default_factory=list)
    transitions: list[StateTransition] = dc_field(default_factory=list)
    terminal_state: str = "STABLE"
    seed: int = 42
    scenario_id: str = ""
    config: dict[str, Any] = dc_field(default_factory=dict)
    def cascade_depth(self) -> int:
        return edge_depth(self.activated_edges)
    def cascade_duration_days(self) -> int:
        if not self.events:
            return 0
        days = [e.day for e in self.events]
        return int(max(days) - min(days) + 1)
    def peak_severity(self) -> float:
        return float(max((e.severity for e in self.events), default=0.0))
    def cascade_magnitude(self, weights: dict[str, float] | None = None) -> float:
        mapping = {"crop_stress": "crop_water_stress", "secondary_stress": "secondary_stress",
            "yield_risk": "yield_risk", "nutrient_deficit": "nutrient_deficit",
            "disease_pressure": "disease_pressure"}
        w: dict[str, float] = {}
        for k, v in ((self.config.get("cascade_magnitude", {}) or {}).get("weights", {}) or {}).items():
            w[mapping.get(k, k)] = float(v)
        if weights:
            w.update(weights)
        return float(sum(s.aggregate_stress(w) for s in self.states[1:]))
    def summary(self) -> dict[str, Any]:
        last = self.states[-1] if self.states else None
        return {"scenario_id": self.scenario_id, "seed": self.seed,
            "days": len(self.states) - 1 if self.states else 0,
            "terminal_state": self.terminal_state, "cascade_depth": self.cascade_depth(),
            "cascade_duration_days": self.cascade_duration_days(),
            "peak_severity": self.peak_severity(),
            "cascade_magnitude": self.cascade_magnitude(), "n_events": len(self.events),
            "final_yield_risk": last.yield_risk if last else None,
            "final_crop_stress": last.crop_water_stress if last else None,
            "final_reserve": last.water_reserve if last else None}
    def to_dict(self) -> dict[str, Any]:
        return {"states": [s.to_dict() for s in self.states],
            "activated_edges": self.activated_edges,
            "events": [e.to_dict() for e in self.events],
            "transitions": [t.to_dict() for t in self.transitions],
            "terminal_state": self.terminal_state, "seed": self.seed,
            "scenario_id": self.scenario_id, "summary": self.summary()}


def _default_forecast(initial: AgriculturalState, horizon: int, seed: int) -> list[WeatherDay]:
    rng = make_rng(child_seed(seed, "forecast"))
    base_rain = max(0.0, float(initial.rainfall)); base_temp = float(initial.temperature)
    base_hum = float(initial.humidity); base_et = max(0.0, float(initial.evapotranspiration))
    out: list[WeatherDay] = []
    for d in range(horizon):
        out.append(WeatherDay(day=d, timestamp=initial.timestamp + timedelta(days=d + 1),
            rainfall=max(0.0, float(rng.normal(base_rain, max(1.0, base_rain * 0.3)))),
            temperature=float(rng.normal(base_temp, 0.8)),
            humidity=float(max(0.0, min(100.0, rng.normal(base_hum, 3.0)))),
            evapotranspiration=max(0.0, float(rng.normal(base_et, 0.4))),
            source_type="synthetic", source="climatological_fallback"))
    return out


def classify_terminal(states: list[AgriculturalState], config: dict[str, Any]) -> str:
    if len(states) < 2:
        return "STABLE"
    last = states[-1]; prev = states[max(0, len(states) - 4)]
    peak = max(s.crop_water_stress for s in states)
    improving = last.crop_water_stress < prev.crop_water_stress - 0.05
    if last.crop_water_stress >= 0.75 or last.yield_risk >= 0.75:
        return "SEVERE_STRESS"
    if last.secondary_stress >= 0.5 and last.water_reserve < 0.25:
        return "CASCADE_ESCALATING"
    if last.crop_water_stress >= 0.4 or last.yield_risk >= 0.4:
        return "RECOVERING" if improving else "STRESSED"
    if peak >= 0.4 and improving:
        return "CASCADE_CONTAINED"
    return "STABLE"



def simulate_cascade(initial_state: AgriculturalState, scenario: Scenario | None = None,
        forecast: list[WeatherDay] | None = None, horizon_days: int = 14, seed: int = 42,
        soil_properties: dict[str, float] | None = None,
        interventions: list[Intervention] | None = None,
        config: dict[str, Any] | None = None, crop_config: dict[str, Any] | None = None,
        graph: nx.DiGraph | None = None) -> CascadeTrajectory:
    cfg = config or load_model_config(); crop_cfg = crop_config or load_crop_config()
    if graph is None:
        graph = build_cascade_graph(cfg)
    scenario = scenario or Scenario(scenario_id="normal", name="Normal")
    horizon = int(scenario.horizon_days or horizon_days)
    wx = list(forecast) if forecast is not None else _default_forecast(initial_state, horizon, seed)
    if len(wx) < horizon:
        wx = wx + _default_forecast(initial_state, horizon - len(wx), seed)
    wx = wx[:horizon]
    states: list[AgriculturalState] = [initial_state]
    activated: list[dict[str, Any]] = []; transitions: list[StateTransition] = []
    events: list[CascadeEvent] = []; cumulative = 0.0
    current = initial_state; previous: AgriculturalState | None = None
    for t in range(horizon):
        mods = scenario.modifiers_for_day(t)
        day_wx = wx[t].apply_modifiers(mods)
        extra = 0.0
        if interventions:
            for iv in interventions:
                extra += iv.daily_application(t, horizon)
        cap_mult = float(mods.get("irrigation_capacity_multiplier", 1.0))
        capacity = max(0.0, min(1.0, current.irrigation_available * cap_mult))
        result = step_state(current.with_updates(irrigation_available=capacity), day_wx,
            soil_properties, config=cfg, crop_config=crop_cfg, irrigation_capacity=capacity,
            extra_irrigation_mm=extra, cumulative_weighted_stress=cumulative,
            disease_delta=float(mods.get("disease_pressure_delta", 0.0)))
        new_state = result.state
        drain = float(mods.get("reserve_drain_delta", 0.0))
        if drain:
            total = float(cfg["irrigation"]["reserve_total_mm"])
            mm = max(0.0, new_state.water_reserve_mm - drain)
            new_state = new_state.with_updates(water_reserve_mm=mm,
                water_reserve=mm / total if total else 0.0)
        cumulative = result.cumulative_weighted_stress
        events.extend(detect_threshold_crossings(new_state, current, t, cfg, events))
        activated.extend(propagate_dependencies(new_state,
            previous if previous is not None else current, t))
        transitions.extend(result.transitions)
        states.append(new_state); previous = current; current = new_state
    return CascadeTrajectory(states=states, activated_edges=activated, events=events,
        transitions=transitions, terminal_state=classify_terminal(states, cfg),
        seed=seed, scenario_id=scenario.scenario_id, config=cfg)


def monte_carlo_cascade(initial_state: AgriculturalState, scenario: Scenario,
        horizon_days: int = 14, seed: int = 42, n_trajectories: int = 50,
        interventions: list[Intervention] | None = None,
        config: dict[str, Any] | None = None) -> dict[str, Any]:
    from agricascade.state.uncertainty import probability_of_exceedance
    cfg = config or load_model_config(); mc = cfg.get("monte_carlo", {})
    n = int(n_trajectories or mc.get("trajectories", 1000))
    base_rng = make_rng(child_seed(seed, "monte_carlo"))
    sig_rain = float(mc.get("rainfall_multiplier_sigma", 0.15))
    sig_et = float(mc.get("et_multiplier_sigma", 0.10))
    sig_root = float(mc.get("initial_root_moisture_sigma", 0.02))
    severe_thr = float(mc.get("severe_stress_threshold", 0.60))
    finals: list[float] = []; peaks: list[float] = []
    mags: list[float] = []; terms: list[str] = []
    for i in range(n):
        r = float(base_rng.normal(1.0, sig_rain)); e = float(base_rng.normal(1.0, sig_et))
        rs = float(base_rng.normal(0.0, sig_root))
        init = initial_state.with_updates(
            soil_moisture_root=float(max(0.05, min(0.45, initial_state.soil_moisture_root + rs))))
        fc = _default_forecast(init, horizon_days, child_seed(seed, "mc", i))
        for w in fc:
            w.rainfall = max(0.0, w.rainfall * r)
            w.evapotranspiration = max(0.0, w.evapotranspiration * e)
        traj = simulate_cascade(init, scenario, fc, horizon_days,
            child_seed(seed, "mc_traj", i), None, interventions, cfg)
        finals.append(traj.states[-1].crop_water_stress)
        peaks.append(max(s.crop_water_stress for s in traj.states))
        mags.append(traj.cascade_magnitude()); terms.append(traj.terminal_state)
    return {"n": n, "seed": seed, "p_severe": probability_of_exceedance(peaks, severe_thr),
        "p_cascade": probability_of_exceedance(mags, 2.0),
        "final_stress_mean": float(sum(finals) / max(1, len(finals))),
        "peak_mean": float(sum(peaks) / max(1, len(peaks))),
        "magnitude_mean": float(sum(mags) / max(1, len(mags))), "terminals": terms}
