"""CLI: benchmark across the synthetic suite (measured metrics only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agricascade.evaluation.benchmark import run_benchmark

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--horizon", type=int, default=14)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    print(json.dumps(run_benchmark(a.horizon, a.seed), indent=2, default=str))

if __name__ == "__main__":
    main()
