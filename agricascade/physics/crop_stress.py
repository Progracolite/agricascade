"""Crop water stress, stage progression and crop-health signal.

SCIENCE NOTES

* The water-stress index is a simplified simulation variable, not a universal
  physiological model (spec section 13).
* Crop-stage sensitivities are configuration values, documented in
  ``config/crop_rice.yaml`` (spec section 14).
* The crop-health index is a *simulation signal* built from NDVI, NDMI and
  stress. It is NOT labelled "actual plant health" (spec section 15).
"""

from __future__ import annotations

from typing import Any

from agricascade.utils.io import load_crop_config, load_model_config


def water_stress(
    theta_root: float,
    critical_theta: float,
    wilting_theta: float,
) -> float:
    """Normalised root-zone water stress in [0, 1].

    ``0`` = no stress (at/above critical), ``1`` = severe (at/below wilting).
    """
    denom = critical_theta - wilting_theta
    if denom <= 0:
        raise ValueError("critical_theta must exceed wilting_theta")
    raw = (critical_theta - float(theta_root)) / denom
    return float(max(0.0, min(1.0, raw)))


def soil_water_deficit(
    theta_root: float,
    field_capacity_theta: float,
    wilting_theta: float,
) -> float:
    """Deficit as a fraction of the available water range [0, 1]."""
    denom = field_capacity_theta - wilting_theta
    if denom <= 0:
        raise ValueError("field_capacity_theta must exceed wilting_theta")
    raw = (field_capacity_theta - float(theta_root)) / denom
    return float(max(0.0, min(1.0, raw)))


def stage_for_day(day_of_season: int, crop_config: dict[str, Any] | None = None) -> str:
    """Return the crop stage name for a day-of-season."""
    crop = (crop_config or load_crop_config())["crop"]
    stages = crop["stages"]
    ordered = sorted(stages.items(), key=lambda kv: kv[1]["start_day"])
    current = ordered[0][0]
    for name, spec in ordered:
        if day_of_season >= spec["start_day"]:
            current = name
        else:
            break
    return current


def stage_water_sensitivity(
    stage: str, crop_config: dict[str, Any] | None = None
) -> float:
    """Water sensitivity multiplier for a crop stage."""
    crop = (crop_config or load_crop_config())["crop"]
    stages = crop["stages"]
    if stage not in stages:
        raise KeyError(f"Unknown crop stage {stage!r}")
    return float(stages[stage]["water_sensitivity"])


def advance_stage(
    day_of_season: int, crop_config: dict[str, Any] | None = None
) -> tuple[int, str, float]:
    """Advance one day and return ``(new_day, stage, sensitivity)``."""
    new_day = int(day_of_season) + 1
    stage = stage_for_day(new_day, crop_config)
    sensitivity = stage_water_sensitivity(stage, crop_config)
    return new_day, stage, sensitivity


def crop_health_index(
    ndvi_proxy: float,
    ndmi_proxy: float,
    water_stress_value: float,
    config: dict[str, Any] | None = None,
) -> float:
    """Weighted crop-health simulation signal in [0, 1]."""
    cfg = (config or load_model_config())["crop_health"]
    weights = cfg["weights"]
    ndvi_lo, ndvi_hi = cfg["ndvi_range"]
    ndmi_lo, ndmi_hi = cfg["ndmi_range"]

    ndvi_norm = _normalize(ndvi_proxy, ndvi_lo, ndvi_hi)
    ndmi_norm = _normalize(ndmi_proxy, ndmi_lo, ndmi_hi)
    inverse_stress = 1.0 - max(0.0, min(1.0, water_stress_value))

    value = (
        weights["ndvi"] * ndvi_norm
        + weights["ndmi"] * ndmi_norm
        + weights["inverse_stress"] * inverse_stress
    )
    return float(max(0.0, min(1.0, value)))


def _normalize(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        raise ValueError("upper bound must exceed lower bound")
    return float(max(0.0, min(1.0, (float(value) - lo) / (hi - lo))))