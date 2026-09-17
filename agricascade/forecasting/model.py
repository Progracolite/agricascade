"""Forecasting: climatology + sklearn residual correction (estimation only).

Physics remains responsible for propagation; ML only estimates/forecasts
weather drivers. Temporal splits are chronological (no shuffling).
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
import numpy as np
from agricascade.schemas.observation import Observation
from agricascade.schemas.state import AgriculturalState
from agricascade.state.updater import WeatherDay
from agricascade.utils.random import make_rng

@dataclass
class ForecastResult:
    days: list[WeatherDay]
    method: str
    uncertainty: dict[str, list[tuple[float, float]]]
    def to_dict(self) -> dict[str, Any]:
        return {"method": self.method, "days": [d.to_dict() for d in self.days],
            "uncertainty": self.uncertainty}

def _history_matrix(obs: list[Observation], var: str) -> list[tuple]:
    rows = sorted([(o.timestamp, o.value) for o in obs if o.variable == var],
        key=lambda r: r[0])
    return rows

def climatology_forecast(state: AgriculturalState, horizon: int = 14,
        seed: int = 42, history: list[Observation] | None = None) -> ForecastResult:
    rng = make_rng(seed)
    base = {"rainfall": max(0.0, state.rainfall), "temperature": state.temperature,
        "humidity": state.humidity, "evapotranspiration": max(0.0, state.evapotranspiration)}
    if history:
        for var in base:
            rows = _history_matrix(history, var)
            if len(rows) >= 3:
                base[var] = float(np.mean([v for _, v in rows[-7:]]))
    days: list[WeatherDay] = []
    unc: dict[str, list[tuple[float, float]]] = {k: [] for k in base}
    sig = {"rainfall": max(1.0, base["rainfall"] * 0.3), "temperature": 0.8,
        "humidity": 3.0, "evapotranspiration": 0.4}
    for d in range(horizon):
        vals = {}
        for k in base:
            v = float(rng.normal(base[k], sig[k]))
            if k in ("rainfall", "evapotranspiration"):
                v = max(0.0, v)
            if k == "humidity":
                v = max(0.0, min(100.0, v))
            vals[k] = v
            unc[k].append((vals[k] - 1.645 * sig[k], vals[k] + 1.645 * sig[k]))
        days.append(WeatherDay(day=d, timestamp=state.timestamp + timedelta(days=d + 1),
            rainfall=vals["rainfall"], temperature=vals["temperature"],
            humidity=vals["humidity"], evapotranspiration=vals["evapotranspiration"],
            source_type="synthetic", source="climatology_forecast"))
    return ForecastResult(days, "climatology", unc)

def ml_corrected_forecast(state: AgriculturalState, history: list[Observation],
        horizon: int = 14, seed: int = 42) -> ForecastResult:
    """Chronological fit: HistGradientBoosting on lag features; fallback climatology."""
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
        rows: dict[str, list[float]] = {}
        for o in history:
            rows.setdefault(o.variable, []).append(float(o.value))
        if any(len(v) < 10 for v in rows.values()):
            raise ValueError("insufficient history")
        n = min(len(v) for v in rows.values())
        lag = 3
        X, y = [], []
        rain = rows.get("rainfall", [state.rainfall] * n)
        for i in range(lag, n):
            X.append(rain[i - lag:i])
            y.append(rain[i])
        X = np.array(X); y = np.array(y)
        split = int(len(X) * 0.7)  # chronological, no shuffle
        model = HistGradientBoostingRegressor(max_iter=100, random_state=seed)
        model.fit(X[:split], y[:split])
        preds = list(model.predict(X[split:]))
        last = rain[-lag:]
        nxt = float(model.predict([last])[0])
        base = climatology_forecast(state, horizon, seed, history)
        for d in base.days:
            d.rainfall = max(0.0, 0.5 * d.rainfall + 0.5 * max(0.0, nxt))
            d.source = "ml_corrected_climatology"
        base.method = "ml_corrected_climatology"
        return base
    except Exception:
        return climatology_forecast(state, horizon, seed, history)

def forecast_state(state: AgriculturalState, horizon: int = 14, seed: int = 42,
        history: list[Observation] | None = None, use_ml: bool = True) -> ForecastResult:
    if use_ml and history and len(history) >= 40:
        return ml_corrected_forecast(state, history, horizon, seed)
    return climatology_forecast(state, horizon, seed, history)
