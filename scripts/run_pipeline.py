"""CLI: end-to-end pipeline run (no Streamlit required)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agricascade.evaluation.ground_truth import monsoon_break_scenario
from agricascade.pipeline import analyze_agricultural_cascade
from agricascade.schemas.scenario import Scenario

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", default="monsoon_break")
    p.add_argument("--horizon", type=int, default=14)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--mc", type=int, default=1000)
    a = p.parse_args()
    sc = monsoon_break_scenario(a.horizon, a.seed) if a.scenario == "monsoon_break" else Scenario(
        scenario_id=a.scenario, name=a.scenario, horizon_days=a.horizon, seed=a.seed)
    r = analyze_agricultural_cascade(scenario=sc, horizon_days=a.horizon,
        seed=a.seed, mc_trajectories=a.mc)
    print(json.dumps({"baseline": r["baseline"].summary(),
        "counterfactual": r["counterfactual"]["comparison"],
        "monte_carlo": {k: v for k, v in r["monte_carlo"].items() if k != "terminals"},
        "events": r["explanations"]["events"],
        "branch": r["explanations"]["branch"],
        "counterfactual_expl": r["explanations"]["counterfactual"]}, indent=2, default=str))

if __name__ == "__main__":
    main()
