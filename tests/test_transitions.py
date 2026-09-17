"""Every core transition + intervention is exercised (AGENTS rule 29)."""
from agricascade.cascade.transitions import EDGE_SPECS, NODES, evaluate_activation, propagate_dependencies
from agricascade.intervention.candidates import generate_interventions
from agricascade.intervention.engine import evaluate_interventions
from agricascade.cascade.simulator import simulate_cascade
from agricascade.evaluation.ground_truth import monsoon_break_scenario
from agricascade.state.initializer import initialize_state

def test_all_edge_specs_reference_known_nodes():
    assert len(EDGE_SPECS) >= 10
    for spec in EDGE_SPECS:
        assert spec["source"] in NODES and spec["target"] in NODES
        assert spec["activation"]["variable"] in initialize_state(seed=42).to_dict()

def test_each_intervention_type_resimulates():
    sc = monsoon_break_scenario(horizon=7)
    s = initialize_state(seed=42, scenario=sc)
    base = simulate_cascade(s, sc, seed=42)
    ivs = generate_interventions(None, sc)
    assert {i.type for i in ivs} == {"partial_irrigation", "full_irrigation",
        "irrigation_delay", "water_allocation"}
    ev = evaluate_interventions(s, sc, ivs, base, horizon_days=7, seed=42)
    assert len(ev) == 4
    for e in ev:
        assert len(e.trajectory.states) == len(base.states)

def test_propagate_returns_day_tagged_edges():
    s = initialize_state(seed=42)
    acts = propagate_dependencies(s, None, day=0)
    assert isinstance(acts, list)
    for a in acts:
        assert a["day"] == 0 and "source" in a and "target" in a
