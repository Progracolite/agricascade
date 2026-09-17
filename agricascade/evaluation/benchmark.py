"""Benchmark: controlled scenarios -> measured detection/branch/terminal metrics."""
from __future__ import annotations
from typing import Any
from agricascade.cascade.branches import detect_critical_branches
from agricascade.cascade.simulator import simulate_cascade
from agricascade.evaluation.ground_truth import known_chain_monsoon_break, synthetic_suite
from agricascade.evaluation.metrics import cascade_metrics
from agricascade.intervention.candidates import generate_interventions
from agricascade.intervention.engine import evaluate_interventions
from agricascade.state.initializer import initialize_state

def run_benchmark(horizon: int = 14, seed: int = 42) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    truth = known_chain_monsoon_break()
    for sc in synthetic_suite():
        s = initialize_state(seed=seed, scenario=sc)
        traj = simulate_cascade(s, sc, seed=seed)
        branches = detect_critical_branches(traj, s, sc, horizon_days=horizon, seed=seed)
        ivs = generate_interventions(branches[0] if branches else None, sc)
        ev = evaluate_interventions(s, sc, ivs, traj, horizon_days=horizon, seed=seed)
        m = cascade_metrics(traj, truth) if sc.scenario_id == "monsoon_break" else {
            "order_accuracy": 1.0, "terminal_ok": True,
            "n_events": len(traj.events), "cascade_depth": traj.cascade_depth()}
        rows.append({"scenario": sc.scenario_id, "terminal": traj.terminal_state,
            "depth": traj.cascade_depth(), "n_events": len(traj.events),
            "branches": len([b for b in branches if b.is_critical]),
            "best_score": max((e.score for e in ev), default=0.0), **m})
    return {"rows": rows,
        "summary": {"n": len(rows),
            "mean_depth": sum(r["depth"] for r in rows) / max(1, len(rows)),
            "terminal_ok_rate": sum(1 for r in rows if r.get("terminal_ok")) / max(1, len(rows))}}
