"""Canonical agricultural state vector.

This is the shared interface every module uses. It intentionally holds only the
variables the simulation actually uses (see spec section 8).

Depth layers (surface/root/deep) are MODEL STATES, not direct satellite
measurements. Satellite and weather observations constrain them indirectly.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime
from typing import Any, Iterable

# Variables that behave like "stress" (0 = none, 1 = severe). Used for cascade
# magnitude, terminal-state classification and counterfactual comparison.
STRESS_VARIABLES = (
    "crop_water_stress",
    "secondary_stress",
    "yield_risk",
)

# Default cascade-magnitude weights if the config does not provide them.
DEFAULT_STRESS_WEIGHTS = {
    "crop_water_stress": 1.0,
    "secondary_stress": 1.0,
    "yield_risk": 1.0,
    "nutrient_deficit": 0.3,
    "disease_pressure": 0.3,
}


@dataclass
class AgriculturalState:
    """The canonical state vector for one simulation step."""

    timestamp: datetime

    # --- Water / soil (estimated model states) ---
    soil_moisture_surface: float
    soil_moisture_root: float
    soil_moisture_deep: float
    soil_temperature: float
    soil_water_deficit: float

    # --- Weather drivers ---
    rainfall: float
    temperature: float
    evapotranspiration: float
    humidity: float

    # --- Crop (estimated / simulated) ---
    crop_stage: str
    crop_stage_sensitivity: float
    day_of_season: int
    crop_health_index: float
    biomass_proxy: float
    ndvi_proxy: float
    ndmi_proxy: float
    crop_water_stress: float
    secondary_stress: float

    # --- Management (synthetic scenario variables) ---
    irrigation_available: float
    irrigation_demand: float
    irrigation_applied: float
    nutrient_status_proxy: float
    disease_pressure_proxy: float

    # --- Outcome / resource ---
    water_reserve: float
    water_reserve_mm: float
    yield_risk: float

    # --- Diagnostics for this step ---
    runoff: float = 0.0
    drainage: float = 0.0

    # Provenance contract (spec section 7). State is estimated from
    # observations then propagated by the simulator.
    source_type: str = "derived"

    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            out[f.name] = value
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgriculturalState":
        payload = dict(data)
        ts = payload.get("timestamp")
        if isinstance(ts, str):
            payload["timestamp"] = datetime.fromisoformat(ts)
        known = {f.name for f in fields(cls)}
        payload = {k: v for k, v in payload.items() if k in known}
        return cls(**payload)

    def with_updates(self, **updates: Any) -> "AgriculturalState":
        """Return a copy with the given fields replaced."""
        return replace(self, **updates)

    def copy(self) -> "AgriculturalState":
        return replace(self)

    def stress_vector(self, weights: dict[str, float] | None = None) -> dict[str, float]:
        """Return the weighted stress components used for cascade magnitude.

        ``nutrient_deficit`` and ``disease_pressure`` are expressed as deficits
        so that all components increase with damage.
        """
        w = dict(DEFAULT_STRESS_WEIGHTS)
        if weights:
            w.update(weights)
        return {
            "crop_water_stress": w["crop_water_stress"] * self.crop_water_stress,
            "secondary_stress": w["secondary_stress"] * self.secondary_stress,
            "yield_risk": w["yield_risk"] * self.yield_risk,
            "nutrient_deficit": w["nutrient_deficit"] * (1.0 - self.nutrient_status_proxy),
            "disease_pressure": w["disease_pressure"] * self.disease_pressure_proxy,
        }

    def aggregate_stress(self, weights: dict[str, float] | None = None) -> float:
        """Single scalar damage proxy for this state (sum of weighted stresses)."""
        return float(sum(self.stress_vector(weights).values()))

    def water_deficit_fraction(self) -> float:
        """Root-zone deficit as a fraction of the crop-available range."""
        return float(self.soil_water_deficit)


def states_to_records(
    states: Iterable[AgriculturalState],
) -> list[dict[str, Any]]:
    """Serialize an iterable of states to plain records."""
    return [s.to_dict() for s in states]