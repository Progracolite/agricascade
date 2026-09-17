"""Lightweight soil-water balance.

    S_{t+1} = S_t + P_t + I_t - ET_t - R_t - D_t

Storage is tracked in millimetres per layer; the canonical state exposes
volumetric water content (m3/m3). Depth layers are model states, not
satellite measurements (spec section 9).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agricascade.physics.drainage import deep_drainage, redistribute_excess
from agricascade.physics.infiltration import partition_incoming
from agricascade.utils.io import load_model_config


@dataclass
class SoilWaterState:
    """Volumetric moisture plus fluxes for one water-balance step."""

    surface_moisture: float
    root_zone_moisture: float
    deep_zone_moisture: float

    surface_storage_mm: float
    root_storage_mm: float
    deep_storage_mm: float

    runoff: float
    drainage: float
    actual_et: float
    infiltration: float


def layer_thicknesses(config: dict[str, Any] | None = None) -> tuple[float, float, float]:
    cfg = config or load_model_config()
    layers = cfg["soil_layers"]
    return (
        float(layers["surface"]["depth_mm"]),
        float(layers["root"]["depth_mm"]),
        float(layers["deep"]["depth_mm"]),
    )


def resolve_soil_parameters(
    soil_properties: dict[str, float] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Resolve field capacity / wilting point, applying texture scaling."""
    cfg = config or load_model_config()
    soil_cfg = cfg["soil"]

    theta_fc = float(soil_cfg["field_capacity_theta"])
    theta_wp = float(soil_cfg["wilting_point_theta"])
    theta_sat = float(soil_cfg["saturation_theta"])
    theta_res = float(soil_cfg["residual_theta"])

    if soil_properties and soil_cfg.get("texture_scaling", True):
        sand = soil_properties.get("sand_fraction")
        if sand is not None:
            reference = float(soil_cfg.get("reference_sand_fraction", 0.45))
            sensitivity = float(soil_cfg.get("field_capacity_sand_sensitivity", 0.30))
            theta_fc = theta_fc - sensitivity * (float(sand) - reference)
            theta_fc = max(theta_wp + 0.03, min(theta_sat - 0.01, theta_fc))

    return {
        "theta_fc": theta_fc,
        "theta_wp": theta_wp,
        "theta_sat": theta_sat,
        "theta_res": theta_res,
    }


def _clip_theta(theta: float, params: dict[str, float]) -> float:
    return float(max(params["theta_res"], min(params["theta_sat"], theta)))


def soil_water_update(
    previous_state: Any,
    rainfall: float,
    irrigation: float,
    evapotranspiration: float,
    soil_properties: dict[str, float] | None = None,
    config: dict[str, Any] | None = None,
) -> SoilWaterState:
    """Advance the three-layer bucket by one day.

    ``previous_state`` may be an :class:`AgriculturalState` or any object with
    ``soil_moisture_surface``, ``soil_moisture_root`` and ``soil_moisture_deep``.
    """
    cfg = config or load_model_config()
    soil_cfg = cfg["soil"]
    t_surf, t_root, t_deep = layer_thicknesses(cfg)
    params = resolve_soil_parameters(soil_properties, cfg)

    theta_fc = params["theta_fc"]
    theta_wp = params["theta_wp"]

    cap_surf = theta_fc * t_surf
    cap_root = theta_fc * t_root
    cap_deep = theta_fc * t_deep

    prev_s = float(previous_state.soil_moisture_surface) * t_surf
    prev_r = float(previous_state.soil_moisture_root) * t_root
    prev_d = float(previous_state.soil_moisture_deep) * t_deep

    infiltrated, runoff = partition_incoming(
        rainfall, irrigation, soil_properties, cfg
    )

    # Potential ET per layer, limited by available water (surface+root+deep).
    pe_s = max(0.0, float(evapotranspiration)) * float(soil_cfg["et_surface_fraction"])
    pe_r = max(0.0, float(evapotranspiration)) * float(soil_cfg["et_root_fraction"])
    pe_d = max(0.0, float(evapotranspiration)) * float(soil_cfg["et_deep_fraction"])
    total_pot = pe_s + pe_r + pe_d
    available = prev_s + prev_r + prev_d + infiltrated
    if total_pot > available > 0:
        scale = available / total_pot
        pe_s *= scale
        pe_r *= scale
        pe_d *= scale
    elif available <= 0:
        pe_s = pe_r = pe_d = 0.0
    actual_et = pe_s + pe_r + pe_d

    # --- Surface layer ---
    s_s = max(0.0, prev_s + infiltrated - pe_s)
    excess_s = max(0.0, s_s - cap_surf)
    transfer_s, perc_s, loss_s = redistribute_excess(excess_s, cfg, to_deep=False)
    s_s -= transfer_s + perc_s + loss_s

    # --- Root layer ---
    s_r = max(0.0, prev_r + transfer_s - pe_r)
    excess_r = max(0.0, s_r - cap_root)
    transfer_r, _perc_r, loss_r = redistribute_excess(excess_r, cfg, to_deep=True)
    s_r -= transfer_r + loss_r

    # --- Deep layer ---
    s_d = max(0.0, prev_d + perc_s + transfer_r - pe_d)
    drain_d = deep_drainage(s_d, cap_deep, cfg)
    s_d -= drain_d

    drainage = loss_s + loss_r + drain_d

    surface_moisture = _clip_theta(s_s / t_surf, params)
    root_moisture = _clip_theta(s_r / t_root, params)
    deep_moisture = _clip_theta(s_d / t_deep, params)

    return SoilWaterState(
        surface_moisture=surface_moisture,
        root_zone_moisture=root_moisture,
        deep_zone_moisture=deep_moisture,
        surface_storage_mm=s_s,
        root_storage_mm=s_r,
        deep_storage_mm=s_d,
        runoff=runoff,
        drainage=drainage,
        actual_et=actual_et,
        infiltration=infiltrated,
    )