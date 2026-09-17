"""Infiltration partitioning.

SCIENTIFIC ASSUMPTION: infiltration is represented by a constant
``infiltration_fraction`` with a texture adjustment, not by a Green-Ampt or
Richards solver. The remainder of incoming water (rain + irrigation) becomes
runoff. This is a deliberately lightweight bucket-model assumption.
"""

from __future__ import annotations

from typing import Any

from agricascade.utils.io import load_model_config


def effective_infiltration_fraction(
    rainfall: float,
    soil_properties: dict[str, float] | None = None,
    config: dict[str, Any] | None = None,
) -> float:
    """Return the fraction of incoming water that infiltrates.

    Heavy rainfall reduces infiltration (more runoff). Sandier soils infiltrate
    more readily, clayey soils less, relative to the reference texture.
    """
    soil_cfg = (config or load_model_config())["soil"]
    base = float(soil_cfg["infiltration_fraction"])

    # Heavy-rain penalty: rainfall above 40 mm/day reduces infiltration.
    if rainfall > 40.0:
        base -= min(0.25, (rainfall - 40.0) / 200.0)

    if soil_properties:
        sand = soil_properties.get("sand_fraction")
        reference = float(soil_cfg.get("reference_sand_fraction", 0.45))
        if sand is not None:
            # +0.1 sand fraction -> +0.02 infiltration (capped).
            base += max(-0.1, min(0.1, (float(sand) - reference) * 0.2))

    return float(max(0.05, min(0.98, base)))


def partition_incoming(
    rainfall: float,
    irrigation: float,
    soil_properties: dict[str, float] | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[float, float]:
    """Split incoming water into ``(infiltrated_mm, runoff_mm)``."""
    rainfall = max(0.0, float(rainfall))
    irrigation = max(0.0, float(irrigation))
    fraction = effective_infiltration_fraction(rainfall, soil_properties, config)
    incoming = rainfall + irrigation
    infiltrated = incoming * fraction
    runoff = incoming - infiltrated
    return infiltrated, runoff