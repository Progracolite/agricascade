"""Master pipeline (spec section 81)."""
from __future__ import annotations
from typing import Any
from agricascade.cascade.branches import detect_critical_branches, select_critical_branch
from agricascade.cascade.explain import explain_branch, explain_counterfactual, explain_events
from agricascade.cascade.simulator import (
    CascadeTrajectory, monte_carlo_cascade, simulate_cascade,
)
from agricascade.data.loaders import observations_with_fallback
from agricascade.evaluation.baselines import compare_against_cascade
from agricascade.evaluation.ground_truth import known_chain_monsoon_break
from agricascade.evaluation.metrics import cascade_metrics
from agricascade.forecasting.model import forecast_state
from agricascade.intervention.candidates import generate_interventions
from agricascade.intervention.engine import (
    evaluate_interventions, run_counterfactual, select_best_intervention,
)
from agricascade.schemas.scenario import Scenario
from agricascade.schemas.state import AgriculturalState
from agricascade.state.initializer import initialize_state
from agricascade.state.updater import WeatherDay
from agricascade.utils.io import load_model_config, load_scenario_registry

def analyze_agricultural_cascade(observation_window: Any = None,
        scenario: Scenario | None = None, horizon_days: int = 14, seed: int = 42,
        soil_properties: dict[str, float] | None = None,
        forecast: list[WeatherDay] | None = None,
        region: str = "thrissur", use_forecast_layer: bool = True,
        mc_trajectories: int = 1000, run_baselines: bool = True) -> dict[str, Any]:
    cfg = load_model_config()
    scenario = scenario or Scenario(scenario_id="normal", name="Normal",
        horizon_days=horizon_days, seed=seed)
    obs, obs_report = observations_with_fallback(region, seed)
    if observation_window is not None:
        obs = observation_window
    soil_props = soil_properties
    soil_report = "provided" if soil_props else "synthetic:field_generator"
    if soil_props is None:
        soil_props = None  # initializer resolves texture deterministically
    initial: AgriculturalState = initialize_state(
        observations=obs, scenario=scenario, seed=seed)
    if forecast is None and use_forecast_layer:
        fc = forecast_state(initial, horizon_days, seed, history=obs, use_ml=True)
        forecast = fc.days
        fc_info = {"method": fc.method, "uncertainty": fc.uncertainty}
    else:
        fc_info = {"method": "provided" if forecast else "engine_fallback"}
    baseline: CascadeTrajectory = simulate_cascade(initial, scenario, forecast,
        horizon_days, seed, soil_props, None, cfg)
    branches = detect_critical_branches(baseline, initial, scenario, forecast,
        horizon_days, seed, soil_props, cfg)
    critical = select_critical_branch(branches)
    interventions = generate_interventions(critical, scenario)
    evaluated = evaluate_interventions(initial, scenario, interventions, baseline,
        forecast, horizon_days, seed, soil_props, cfg)
    best = select_best_intervention(evaluated)
    counter = run_counterfactual(initial, scenario,
        best.intervention if best else None, baseline, forecast,
        horizon_days, seed, soil_props, cfg)
    mc = monte_carlo_cascade(initial, scenario, horizon_days, seed, mc_trajectories)
    baselines = compare_against_cascade(baseline) if run_baselines else {}
    cm = cascade_metrics(baseline, known_chain_monsoon_break()) \
        if scenario.scenario_id == "monsoon_break" else {}
    return {"initial_state": initial, "baseline": baseline, "branches": branches,
        "critical_branch": critical, "interventions": evaluated,
        "best_intervention": best, "counterfactual": counter,
        "monte_carlo": mc, "baselines": baselines, "cascade_metrics": cm,
        "forecast_info": fc_info, "observation_report": obs_report,
        "soil_report": soil_report, "scenario": scenario, "seed": seed,
        "explanations": {"events": explain_events(baseline),
            "branch": explain_branch(critical),
            "counterfactual": explain_counterfactual(baseline,
                counter["trajectory"], best)},
        "scenario_registry": load_scenario_registry()}
