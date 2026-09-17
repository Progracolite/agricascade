"""Explanation engine: statements derived from simulation objects only. No LLM."""
from __future__ import annotations
from agricascade.cascade.branches import BranchCandidate
from agricascade.cascade.simulator import CascadeTrajectory
from agricascade.intervention.engine import EvaluatedIntervention

def explain_events(traj: CascadeTrajectory) -> list[str]:
    lines = []
    for e in traj.events:
        lines.append(f"Day {e.day}: {e.description} (cause: {e.cause}; severity {e.severity:.2f}).")
    return lines

def explain_branch(branch: BranchCandidate | None) -> list[str]:
    if branch is None:
        return ["No critical branch detected: small moisture perturbations did not diverge the future."]
    return [f"Day {branch.day}: branch became sensitive because small root-zone moisture changes "
        f"(root={branch.root_moisture:.2f}) produced divergent future outcomes "
        f"(drier->yield_risk {branch.alternate_outcomes.get('drier', 0):.2f}, "
        f"wetter->{branch.alternate_outcomes.get('wetter', 0):.2f}; sensitivity {branch.sensitivity:.2f})."]

def explain_counterfactual(base: CascadeTrajectory, cf: CascadeTrajectory,
        ev: EvaluatedIntervention | None) -> list[str]:
    b = base.summary(); c = cf.summary()
    name = ev.intervention.label if ev else "no intervention"
    return [f"Baseline terminal {b['terminal_state']} (magnitude {b['cascade_magnitude']:.2f}, peak {b['peak_severity']:.2f}).",
        f"Simulated intervention [{name}]: terminal {c['terminal_state']} "
        f"(magnitude {c['cascade_magnitude']:.2f}, peak {c['peak_severity']:.2f}).",
        f"Water reserve baseline {b['final_reserve']:.0%} vs counterfactual {c['final_reserve']:.0%}."]
