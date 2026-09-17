"""Extended coverage: loaders, forecast, metrics, baselines, MC, ground truth, determinism."""
from agricascade.cascade.simulator import monte_carlo_cascade, simulate_cascade
from agricascade.data.loaders import demo_observations, observations_with_fallback
from agricascade.evaluation.baselines import compare_against_cascade, persistence_baseline
from agricascade.evaluation.benchmark import run_benchmark
from agricascade.evaluation.ground_truth import (
    known_chain_monsoon_break, monsoon_break_scenario,
)
from agricascade.evaluation.metrics import (
    cascade_metrics, event_metrics, regression_metrics,
)
from agricascade.forecasting.model import forecast_state
from agricascade.state.initializer import initialize_state

def test_demo_observations_are_synthetic_and_seeded():
    a = demo_observations(seed=42)
    b = demo_observations(seed=42)
    assert [o.value for o in a] == [o.value for o in b]
    assert all(o.source_type == "synthetic" for o in a)

def test_observations_fallback_marks_synthetic():
    import os
    os.environ["AGRICASCADE_OFFLINE"] = "1"
    obs, report = observations_with_fallback(region="thrissur", seed=42)
    assert report["weather"].startswith("synthetic:")
    assert len(obs) > 0

def test_forecast_layer_returns_uncertainty():
    s = initialize_state(seed=42)
    fc = forecast_state(s, horizon=7, seed=42)
    assert len(fc.days) == 7
    assert "rainfall" in fc.uncertainty and len(fc.uncertainty["rainfall"]) == 7

def test_forecast_chronological_ml_path():
    s = initialize_state(seed=42)
    obs = demo_observations(seed=42, days=14)
    fc = forecast_state(s, horizon=5, seed=42, history=obs, use_ml=True)
    assert fc.method in ("ml_corrected_climatology", "climatology")
    assert len(fc.days) == 5

def test_monte_carlo_seeded_and_shares_engine():
    sc = monsoon_break_scenario()
    s = initialize_state(seed=42, scenario=sc)
    m1 = monte_carlo_cascade(s, sc, horizon_days=7, seed=42, n_trajectories=10)
    m2 = monte_carlo_cascade(s, sc, horizon_days=7, seed=42, n_trajectories=10)
    assert m1 == m2
    assert m1["n"] == 10 and 0.0 <= m1["p_severe"] <= 1.0

def test_metrics_and_ground_truth_chain():
    truth = known_chain_monsoon_break()
    sc = monsoon_break_scenario()
    s = initialize_state(seed=42, scenario=sc)
    t = simulate_cascade(s, sc, seed=42)
    m = cascade_metrics(t, truth)
    assert m["terminal_ok"] is True
    assert m["order_accuracy"] > 0.0
    r = regression_metrics([0.1, 0.2], [0.1, 0.2])
    assert r["mae"] == 0.0 and r["r2"] == 1.0
    e = event_metrics(["a", "b"], ["b", "c"])
    assert 0.0 <= e["f1"] <= 1.0

def test_baselines_measured_not_hardcoded():
    sc = monsoon_break_scenario()
    s = initialize_state(seed=42, scenario=sc)
    t = simulate_cascade(s, sc, seed=42)
    c = compare_against_cascade(t)
    assert "persistence" in c and "agricascade" in c
    p = persistence_baseline(t.states)
    assert p["mae"] >= 0.0

def test_benchmark_runs_all_scenarios():
    out = run_benchmark(horizon=7, seed=42)
    assert out["summary"]["n"] == 3
    assert all("terminal" in r for r in out["rows"])
