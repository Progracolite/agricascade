"""Explicit cascade transitions and dependency propagation.

This module defines the cascade graph edges and the rule that decides whether
an edge is *activated* on a given day. Thresholds and sensitivities are
configurable model assumptions (spec sections 18-19).
"""

from __future__ import annotations

from typing import Any

from agricascade.schemas.state import AgriculturalState
from agricascade.schemas.transition import CascadeEdge

# Canonical cascade nodes.
NODE_WEATHER = "weather"
NODE_SOIL_SURFACE = "soil_water_surface"
NODE_SOIL_ROOT = "soil_water_root"
NODE_SOIL_DEEP = "soil_water_deep"
NODE_CROP_STRESS = "crop_stress"
NODE_CROP_HEALTH = "crop_health"
NODE_BIOMASS = "biomass"
NODE_IRRIGATION_DEMAND = "irrigation_demand"
NODE_WATER_RESERVE = "water_reserve"
NODE_SECONDARY_STRESS = "secondary_stress"
NODE_NUTRIENT = "nutrient_status"
NODE_DISEASE = "disease_pressure"
NODE_YIELD_RISK = "yield_risk"

NODES = (
    NODE_WEATHER,
    NODE_SOIL_SURFACE,
    NODE_SOIL_ROOT,
    NODE_SOIL_DEEP,
    NODE_CROP_STRESS,
    NODE_CROP_HEALTH,
    NODE_BIOMASS,
    NODE_IRRIGATION_DEMAND,
    NODE_WATER_RESERVE,
    NODE_SECONDARY_STRESS,
    NODE_NUTRIENT,
    NODE_DISEASE,
    NODE_YIELD_RISK,
)

# Edge specifications. ``activation`` names the observable state variable and
# the comparison that marks the edge as realized. ``lag_days`` is the assumed
# delay between cause and effect.
EDGE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "source": NODE_WEATHER, "target": NODE_SOIL_SURFACE,
        "relationship": "monotonic_increasing", "sensitivity": 0.90,
        "lag_days": 0, "threshold": 1.0, "uncertainty": 0.10,
        "activation": {"variable": "rainfall", "op": ">", "threshold": 1.0},
        "label": "rainfall to surface water",
    },
    {
        "source": NODE_SOIL_SURFACE, "target": NODE_SOIL_ROOT,
        "relationship": "monotonic_increasing", "sensitivity": 0.80,
        "lag_days": 1, "threshold": 0.10, "uncertainty": 0.10,
        "activation": {"variable": "soil_moisture_surface", "op": ">", "threshold": 0.18},
        "label": "surface water to root zone",
    },
    {
        "source": NODE_SOIL_ROOT, "target": NODE_SOIL_DEEP,
        "relationship": "monotonic_increasing", "sensitivity": 0.50,
        "lag_days": 1, "threshold": 0.30, "uncertainty": 0.15,
        "activation": {"variable": "soil_moisture_root", "op": ">", "threshold": 0.30},
        "label": "root drainage to deep zone",
    },
    {
        "source": NODE_SOIL_ROOT, "target": NODE_CROP_STRESS,
        "relationship": "monotonic_decreasing", "sensitivity": 0.80,
        "lag_days": 1, "threshold": 0.35, "uncertainty": 0.08,
        "activation": {"variable": "crop_water_stress", "op": ">", "threshold": 0.05},
        "label": "root water deficit to crop stress",
    },
    {
        "source": NODE_CROP_STRESS, "target": NODE_CROP_HEALTH,
        "relationship": "monotonic_decreasing", "sensitivity": 0.70,
        "lag_days": 1, "threshold": 0.30, "uncertainty": 0.08,
        "activation": {"variable": "crop_water_stress", "op": ">", "threshold": 0.10},
        "label": "crop stress to health decline",
    },
    {
        "source": NODE_CROP_STRESS, "target": NODE_YIELD_RISK,
        "relationship": "monotonic_increasing", "sensitivity": 0.90,
        "lag_days": 2, "threshold": 0.35, "uncertainty": 0.08,
        "activation": {"variable": "crop_water_stress", "op": ">", "threshold": 0.10},
        "label": "crop stress to yield risk",
    },
    {
        "source": NODE_CROP_STRESS, "target": NODE_IRRIGATION_DEMAND,
        "relationship": "monotonic_increasing", "sensitivity": 0.85,
        "lag_days": 0, "threshold": 0.30, "uncertainty": 0.08,
        "activation": {"variable": "irrigation_demand", "op": ">", "threshold": 0.5},
        "label": "crop stress to irrigation demand",
    },
    {
        "source": NODE_IRRIGATION_DEMAND, "target": NODE_WATER_RESERVE,
        "relationship": "monotonic_decreasing", "sensitivity": 0.80,
        "lag_days": 1, "threshold": 0.20, "uncertainty": 0.08,
        "activation": {"variable": "irrigation_applied", "op": ">", "threshold": 0.5},
        "label": "irrigation drawdown of reserve",
    },
    {
        "source": NODE_WATER_RESERVE, "target": NODE_SECONDARY_STRESS,
        "relationship": "monotonic_decreasing", "sensitivity": 0.90,
        "lag_days": 1, "threshold": 0.25, "uncertainty": 0.08,
        "activation": {"variable": "water_reserve", "op": "<", "threshold": 0.25},
        "label": "reserve depletion to secondary stress",
    },
    {
        "source": NODE_SECONDARY_STRESS, "target": NODE_CROP_STRESS,
        "relationship": "monotonic_increasing", "sensitivity": 0.70,
        "lag_days": 2, "threshold": 0.40, "uncertainty": 0.12,
        "activation": {"variable": "secondary_stress", "op": ">", "threshold": 0.20},
        "label": "secondary stress feedback",
    },
    {
        "source": NODE_DISEASE, "target": NODE_CROP_HEALTH,
        "relationship": "monotonic_decreasing", "sensitivity": 0.60,
        "lag_days": 2, "threshold": 0.30, "uncertainty": 0.15,
        "activation": {"variable": "disease_pressure_proxy", "op": ">", "threshold": 0.30},
        "label": "disease pressure to health",
    },
    {
        "source": NODE_NUTRIENT, "target": NODE_CROP_HEALTH,
        "relationship": "monotonic_decreasing", "sensitivity": 0.50,
        "lag_days": 3, "threshold": 0.20, "uncertainty": 0.15,
        "activation": {"variable": "nutrient_status_proxy", "op": "<", "threshold": 0.40},
        "label": "nutrient deficit to health",
    },
    {
        "source": NODE_CROP_HEALTH, "target": NODE_BIOMASS,
        "relationship": "monotonic_increasing", "sensitivity": 0.80,
        "lag_days": 1, "threshold": 0.0, "uncertainty": 0.08,
        "activation": {"variable": "crop_health_index", "op": ">", "threshold": 0.30},
        "label": "crop health to biomass",
    },
    {
        "source": NODE_BIOMASS, "target": NODE_YIELD_RISK,
        "relationship": "monotonic_decreasing", "sensitivity": 0.60,
        "lag_days": 2, "threshold": 0.50, "uncertainty": 0.10,
        "activation": {"variable": "biomass_proxy", "op": "<", "threshold": 0.50},
        "label": "biomass loss to yield risk",
    },
)


def make_edge(spec: dict[str, Any]) -> CascadeEdge:
    """Build a :class:`CascadeEdge` from an edge specification."""
    return CascadeEdge(
        source=spec["source"],
        target=spec["target"],
        relationship=spec["relationship"],
        sensitivity=spec["sensitivity"],
        lag_days=spec["lag_days"],
        threshold=spec["threshold"],
        uncertainty=spec["uncertainty"],
        activation_probability=1.0,
    )


def edge_specs() -> list[dict[str, Any]]:
    """Return a copy of all edge specifications."""
    return [dict(spec) for spec in EDGE_SPECS]


def _compare(value: float, op: str, threshold: float) -> bool:
    if op == ">":
        return value > threshold
    if op == ">=":
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == "<=":
        return value <= threshold
    raise ValueError(f"Unsupported comparison operator {op!r}")


def evaluate_activation(spec: dict[str, Any], state: AgriculturalState) -> bool:
    """Return whether an edge is realized in the given state."""
    rule = spec["activation"]
    value = getattr(state, rule["variable"])
    value = float(value)
    return _compare(value, rule["op"], float(rule["threshold"]))


def propagate_dependencies(
    state: AgriculturalState,
    previous_state: AgriculturalState | None,
    day: int,
) -> list[dict[str, Any]]:
    """Evaluate every edge against the state and return activated edges.

    An activated edge is one whose activation rule holds and that was not
    already active in the previous state (a realized transition, not a
    persistent condition).
    """
    activated: list[dict[str, Any]] = []
    for spec in EDGE_SPECS:
        now_active = evaluate_activation(spec, state)
        if not now_active:
            continue
        was_active = (
            evaluate_activation(spec, previous_state)
            if previous_state is not None
            else False
        )
        if was_active:
            continue
        edge = make_edge(spec)
        activated.append(
            {
                "edge": edge.to_dict(),
                "source": spec["source"],
                "target": spec["target"],
                "label": spec["label"],
                "day": day,
                "sensitivity": spec["sensitivity"],
                "lag_days": spec["lag_days"],
                "uncertainty": spec["uncertainty"],
            }
        )
    return activated


def edge_depth(activated_edges: list[dict[str, Any]]) -> int:
    """Cascade depth = number of distinct activated transitions."""
    return len({(e["source"], e["target"]) for e in activated_edges})