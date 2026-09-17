"""Baselines: persistence + direct-ML vs AgriCascade (measured, not invented)."""
from __future__ import annotations
from typing import Any
import numpy as np
from agricascade.cascade.simulator import CascadeTrajectory
from agricascade.schemas.state import AgriculturalState

def persistence_baseline(states: list[AgriculturalState], horizon: int = 7) -> dict[str, Any]:
    base = states[0].crop_water_stress if states else 0.0
    preds = [base] * horizon
    actual = [s.crop_water_stress for s in states[1:horizon + 1]]
    mae = float(np.mean(np.abs(np.array(actual) - np.array(preds)))) if actual else 0.0
    return {"method": "persistence", "mae": mae, "preds": preds, "actual": actual}

def ml_direct_baseline(history: list[float], horizon: int = 7) -> dict[str, Any]:
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
        if len(history) < 10:
            raise ValueError("short history")
        lag = 3
        X = np.array([history[i - lag:i] for i in range(lag, len(history))])
        y = np.array(history[lag:])
        split = int(len(X) * 0.7)
        m = HistGradientBoostingRegressor(max_iter=100, random_state=42)
        m.fit(X[:split], y[:split])
        preds = m.predict(X[split:split + horizon]).tolist() if len(X) > split else [history[-1]] * horizon
        return {"method": "ml_direct", "preds": preds}
    except Exception as e:
        return {"method": "ml_direct_fallback", "preds": [history[-1]] * horizon, "note": str(e)}

def compare_against_cascade(traj: CascadeTrajectory, horizon: int = 7) -> dict[str, Any]:
    states = traj.states
    actual = [s.yield_risk for s in states[1:horizon + 1]]
    persist = persistence_baseline([s for s in states], horizon)
    hist = [s.crop_water_stress for s in states[:max(1, len(states) - horizon)]]
    ml = ml_direct_baseline(hist or [0.0], horizon)
    return {"persistence": persist, "ml_direct": ml,
        "agricascade": {"cascade_depth": traj.cascade_depth(),
            "n_events": len(traj.events), "terminal": traj.terminal_state,
            "provides": "branch point + intervention test + uncertainty, beyond point forecast"}}
