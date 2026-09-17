"""Core cascade tests: deterministic replay, events, branches, interventions."""
from agricascade.cascade.simulator import simulate_cascade
from agricascade.cascade.branches import detect_critical_branches
from agricascade.intervention.candidates import generate_interventions
from agricascade.intervention.engine import evaluate_interventions, run_counterfactual
from agricascade.pipeline import analyze_agricultural_cascade
from agricascade.schemas.scenario import Disturbance, Scenario
from agricascade.state.initializer import initialize_state


def _dry_scenario(horizon=14):
    return Scenario(scenario_id="dry", name="Dry",
        disturbances=[Disturbance(type="rainfall_deficit", start_time=0,
            duration=horizon, rainfall_multiplier=0.2, temperature_delta=2.0)],
        horizon_days=horizon, seed=42)


def test_deterministic_replay():
    sc = _dry_scenario()
    s1 = initialize_state(seed=42, scenario=sc)
    s2 = initialize_state(seed=42, scenario=sc)
    t1 = simulate_cascade(s1, sc, seed=42)
    t2 = simulate_cascade(s2, sc, seed=42)
    assert t1.summary() == t2.summary()
    assert len(t1.states) == 15


def test_different_seed_may_differ_but_runs():
    sc = _dry_scenario()
    s = initialize_state(seed=42, scenario=sc)
    t = simulate_cascade(s, sc, seed=7)
    assert t.terminal_state in ("STABLE", "RECOVERING", "STRESSED",
        "SEVERE_STRESS", "CASCADE_CONTAINED", "CASCADE_ESCALATING")


def test_events_have_threshold_semantics():
    sc = _dry_scenario(21)
    s = initialize_state(seed=7, scenario=sc)
    t = simulate_cascade(s, sc, seed=7)
    for e in t.events:
        assert 0.0 <= e.severity <= 1.0
        assert e.day >= 0


def test_branch_detection_and_intervention_resimulation():
    sc = _dry_scenario(14)
    s = initialize_state(seed=42, scenario=sc)
    base = simulate_cascade(s, sc, seed=42)
    branches = detect_critical_branches(base, s, sc, horizon_days=14, seed=42)
    assert len(branches) > 0
    ivs = generate_interventions(branches[0] if branches else None, sc)
    assert len(ivs) == 4
    ev = evaluate_interventions(s, sc, ivs, base, horizon_days=14, seed=42)
    assert len(ev) == 4
    # every intervention re-simulated with same engine: trajectory length matches
    for e in ev:
        assert len(e.trajectory.states) == len(base.states)
    cf = run_counterfactual(s, sc, ev[0].intervention, base, horizon_days=14, seed=42)
    assert "comparison" in cf
    assert cf["comparison"]["counterfactual_terminal"] in (
        "STABLE", "RECOVERING", "STRESSED", "SEVERE_STRESS",
        "CASCADE_CONTAINED", "CASCADE_ESCALATING")


def test_pipeline_end_to_end():
    r = analyze_agricultural_cascade(horizon_days=14, seed=42)
    assert r["baseline"].summary()["days"] == 14
    assert r["best_intervention"] is not None
    r2 = analyze_agricultural_cascade(horizon_days=14, seed=42)
    assert r["baseline"].summary() == r2["baseline"].summary()
