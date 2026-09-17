"""Per-day state update.

This module implements the simulation loop body from spec section 21:

    apply_weather -> update_soil_water -> update_crop_stage -> update_crop_stress
    -> update_crop_health -> update_irrigation_demand -> update_water_reserve
    -> update_yield_risk

Every transition is recorded as an explicit :class:`StateTransition`. The
simulation is deterministic for a fixed seed (no hidden randomness here).
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from datetime import datetime, timedelta
from typing import Any

from agricascade.physics.crop_stress import (
    advance_stage,
    crop_health_index,
    soil_water_deficit,
    water_stress,
)
from agricascade.physics.water_balance import resolve_soil_parameters, soil_water_update
from agricascade.schemas.state import AgriculturalState
from agricascade.schemas.transition import StateTransition
from agricascade.utils.io import load_crop_config, load_model_config


@dataclass
class WeatherDay:
    """Weather drivers for one simulated day."""

    day: int
    timestamp: datetime
    rainfall: float
    temperature: float
    humidity: float
    evapotranspiration: float
    source_type: str = "derived"
    source: str = ""

    def apply_modifiers(self, modifiers: dict[str, float]) -> "WeatherDay":
        """Return a copy with scenario disturbance modifiers applied."""
        rainfall = max(
            0.0,
            self.rainfall * float(modifiers.get("rainfall_multiplier", 1.0)),
        )
        temperature = self.temperature + float(modifiers.get("temperature_delta", 0.0))
        et = max(
            0.0,
            self.evapotranspiration * float(modifiers.get("et_multiplier", 1.0)),
        )
        humidity = float(
            max(0.0, min(100.0, self.humidity + modifiers.get("humidity_delta", 0.0)))
        )
        return WeatherDay(
            day=self.day,
            timestamp=self.timestamp,
            rainfall=rainfall,
            temperature=temperature,
            humidity=humidity,
            evapotranspiration=et,
            source_type=self.source_type,
            source=self.source,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "timestamp": self.timestamp.isoformat(),
            "rainfall": self.rainfall,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "evapotranspiration": self.evapotranspiration,
            "source_type": self.source_type,
            "source": self.source,
        }


@dataclass
class StepResult:
    """Outcome of one state-update step."""

    state: AgriculturalState
    transitions: list[StateTransition] = dc_field(default_factory=list)
    cumulative_weighted_stress: float = 0.0
    irrigation_requested: float = 0.0
    irrigation_applied: float = 0.0


def update_crop_stage(
    state: AgriculturalState,
    crop_config: dict[str, Any] | None = None,
) -> tuple[int, str, float]:
    """Advance crop stage by one day."""
    return advance_stage(state.day_of_season, crop_config)


def update_disease_pressure(
    previous: float,
    temperature: float,
    humidity: float,
    config: dict[str, Any],
    disease_delta: float = 0.0,
) -> float:
    """Rice-blast-like pressure increases under humid, warm conditions."""
    import math

    cfg = config["disease"]
    hum_norm = max(0.0, min(1.0, humidity / 100.0))
    optimum = float(cfg["temperature_optimum_c"])
    tolerance = float(cfg["temperature_tolerance_c"])
    temp_factor = math.exp(-((temperature - optimum) ** 2) / (2.0 * tolerance**2))
    favourable = hum_norm * temp_factor
    growth = float(cfg["growth_rate"]) * favourable
    value = previous + growth + disease_delta - 0.01  # slow natural decline
    return float(max(0.0, min(1.0, value)))


def update_nutrient_status(
    previous: float,
    rainfall: float,
    config: dict[str, Any],
) -> float:
    """Nutrient proxy declines through leaching under heavy rain."""
    cfg = config["nutrient"]
    threshold = float(cfg["leaching_rainfall_threshold_mm"])
    if rainfall > threshold:
        loss = float(cfg["leaching_rate"]) * (rainfall - threshold) / max(threshold, 1e-6)
        value = previous - loss
    else:
        value = previous - 0.001
    return float(max(0.0, min(1.0, value)))


def update_irrigation_demand(
    state: AgriculturalState,
    theta_fc: float,
    theta_wp: float,
    config: dict[str, Any],
) -> float:
    """Irrigation demand (mm/day) from root-zone deficit and stage sensitivity."""
    deficit = soil_water_deficit(state.soil_moisture_root, theta_fc, theta_wp)
    demand = float(config["irrigation"]["max_daily_demand_mm"]) * deficit
    demand *= state.crop_stage_sensitivity
    return float(max(0.0, demand))


def step_state(
    state: AgriculturalState,
    weather: WeatherDay,
    soil_properties: dict[str, float] | None = None,
    *,
    config: dict[str, Any] | None = None,
    crop_config: dict[str, Any] | None = None,
    irrigation_capacity: float | None = None,
    extra_irrigation_mm: float = 0.0,
    cumulative_weighted_stress: float = 0.0,
    disease_delta: float = 0.0,
) -> StepResult:
    """Advance the canonical state by exactly one day."""
    cfg = config or load_model_config()
    crop_cfg = crop_config or load_crop_config()
    soil_props = soil_properties if soil_properties is not None else {}

    params = resolve_soil_parameters(soil_props, cfg)
    theta_fc = params["theta_fc"]
    theta_wp = params["theta_wp"]
    critical_theta = float(cfg["soil"]["critical_theta"])

    transitions: list[StateTransition] = []
    day = int(weather.day)

    # --- 1. Crop stage ---
    new_day_of_season, stage, sensitivity = update_crop_stage(state, crop_cfg)

    # --- 2. Irrigation demand (uses previous moisture) ---
    capacity = (
        state.irrigation_available
        if irrigation_capacity is None
        else float(irrigation_capacity)
    )
    demand = update_irrigation_demand(state, theta_fc, theta_wp, cfg)

    # --- 3. Water balance ---
    requested = demand * capacity + max(0.0, extra_irrigation_mm)
    available_mm = max(0.0, state.water_reserve_mm)
    applied = min(requested, available_mm)

    sw = soil_water_update(
        previous_state=state,
        rainfall=weather.rainfall,
        irrigation=applied,
        evapotranspiration=weather.evapotranspiration,
        soil_properties=soil_props,
        config=cfg,
    )
    transitions.append(
        StateTransition(
            source_state="soil_water_surface",
            target_state="soil_water_root",
            function_name="soil_water_update",
            inputs={
                "rainfall": weather.rainfall,
                "irrigation": applied,
                "evapotranspiration": weather.evapotranspiration,
            },
            parameters={
                "infiltration_fraction": cfg["soil"]["infiltration_fraction"],
                "root_transfer_fraction": cfg["soil"]["root_transfer_fraction"],
                "deep_drainage_fraction": cfg["soil"]["deep_drainage_fraction"],
            },
            output=sw.root_zone_moisture,
            uncertainty=float(cfg["uncertainty"]["default_state_sigma"]),
            day=day,
        )
    )

    # --- 4. Crop water stress ---
    stress = water_stress(sw.root_zone_moisture, critical_theta, theta_wp)
    deficit = soil_water_deficit(sw.root_zone_moisture, theta_fc, theta_wp)
    transitions.append(
        StateTransition(
            source_state="soil_water_root",
            target_state="crop_stress",
            function_name="water_stress",
            inputs={"soil_moisture_root": sw.root_zone_moisture},
            parameters={
                "critical_theta": critical_theta,
                "wilting_theta": theta_wp,
            },
            output=stress,
            uncertainty=0.05,
            day=day,
        )
    )

    # --- 5. Water reserve and secondary stress ---
    irrig_cfg = cfg["irrigation"]
    reserve_total = float(irrig_cfg["reserve_total_mm"])
    reserve_recharge = max(0.0, weather.rainfall) * float(
        irrig_cfg["reserve_recharge_fraction"]
    )
    reserve_mm = state.water_reserve_mm - applied + reserve_recharge
    reserve_mm = float(max(0.0, min(reserve_total, reserve_mm)))
    reserve_fraction = reserve_mm / reserve_total if reserve_total > 0 else 0.0

    sec_threshold = float(irrig_cfg["secondary_stress_reserve_threshold"])
    unmet = max(0.0, requested - applied)
    demand_norm = min(
        1.0, demand / max(float(irrig_cfg["max_daily_demand_mm"]), 1e-6)
    )
    if reserve_fraction < sec_threshold:
        shortfall = (sec_threshold - reserve_fraction) / max(sec_threshold, 1e-6)
        target = max(0.0, min(1.0, shortfall)) * max(stress, demand_norm, min(1.0, unmet / 4.0))
        secondary = 0.5 * state.secondary_stress + 0.5 * target
    else:
        secondary = state.secondary_stress * 0.7
    secondary = float(max(0.0, min(1.0, secondary)))

    transitions.append(
        StateTransition(
            source_state="irrigation_demand",
            target_state="water_reserve",
            function_name="update_water_reserve",
            inputs={
                "irrigation_demand": demand,
                "irrigation_applied": applied,
                "rainfall": weather.rainfall,
            },
            parameters={
                "reserve_total_mm": reserve_total,
                "recharge_fraction": irrig_cfg["reserve_recharge_fraction"],
            },
            output=reserve_fraction,
            uncertainty=0.05,
            day=day,
        )
    )
    transitions.append(
        StateTransition(
            source_state="water_reserve",
            target_state="secondary_stress",
            function_name="update_secondary_stress",
            inputs={"water_reserve": reserve_fraction, "unmet_demand": unmet},
            parameters={"secondary_stress_threshold": sec_threshold},
            output=secondary,
            uncertainty=0.05,
            day=day,
        )
    )

    # --- 6. Crop health / biomass ---
    health_cfg = cfg["crop_health"]
    ndvi_lo, ndvi_hi = health_cfg["ndvi_range"]
    ndmi_lo, ndmi_hi = health_cfg["ndmi_range"]
    growth = float(health_cfg["biomass_growth_rate"]) * (1.0 - 0.8 * stress) * (
        1.0 - 0.3 * secondary
    )
    senescence = float(health_cfg["biomass_senescence"]) * (stress + secondary)
    biomass = float(max(0.0, min(1.0, state.biomass_proxy + growth - senescence)))

    ndvi_proxy = ndvi_lo + biomass * (ndvi_hi - ndvi_lo)
    moisture_norm = float(
        max(0.0, min(1.0, (sw.root_zone_moisture - theta_wp) / max(theta_fc - theta_wp, 1e-6)))
    )
    ndmi_proxy = ndmi_lo + moisture_norm * (ndmi_hi - ndmi_lo)
    health = crop_health_index(ndvi_proxy, ndmi_proxy, max(stress, secondary), cfg)

    transitions.append(
        StateTransition(
            source_state="crop_stress",
            target_state="crop_health",
            function_name="crop_health_index",
            inputs={"crop_water_stress": stress, "secondary_stress": secondary},
            parameters=dict(health_cfg["weights"]),
            output=health,
            uncertainty=0.05,
            day=day,
        )
    )
    transitions.append(
        StateTransition(
            source_state="crop_health",
            target_state="biomass",
            function_name="update_biomass",
            inputs={"crop_health_index": health},
            parameters={
                "growth_rate": float(health_cfg["biomass_growth_rate"]),
                "senescence": float(health_cfg["biomass_senescence"]),
            },
            output=biomass,
            uncertainty=0.05,
            day=day,
        )
    )

    # --- 7. Nutrient / disease proxies ---
    nutrient = update_nutrient_status(state.nutrient_status_proxy, weather.rainfall, cfg)
    disease = update_disease_pressure(
        state.disease_pressure_proxy,
        weather.temperature,
        weather.humidity,
        cfg,
        disease_delta=disease_delta,
    )
    transitions.append(
        StateTransition(
            source_state="disease_pressure",
            target_state="crop_health",
            function_name="update_disease_pressure",
            inputs={"temperature": weather.temperature, "humidity": weather.humidity},
            parameters={"growth_rate": float(cfg["disease"]["growth_rate"])},
            output=disease,
            uncertainty=0.1,
            day=day,
        )
    )
    transitions.append(
        StateTransition(
            source_state="nutrient_status",
            target_state="crop_health",
            function_name="update_nutrient_status",
            inputs={"rainfall": weather.rainfall},
            parameters={"leaching_rate": float(cfg["nutrient"]["leaching_rate"])},
            output=nutrient,
            uncertainty=0.1,
            day=day,
        )
    )

    # --- 8. Yield risk (emergent cumulative, stage-weighted) ---
    weighted = stress * sensitivity
    cumulative = cumulative_weighted_stress + weighted
    yield_risk = float(
        max(0.0, min(1.0, cumulative / float(cfg["yield_risk"]["cumulative_stress_scale"])))
    )
    transitions.append(
        StateTransition(
            source_state="crop_stress",
            target_state="yield_risk",
            function_name="update_yield_risk",
            inputs={"crop_water_stress": stress, "stage_sensitivity": sensitivity},
            parameters={
                "cumulative_stress_scale": float(
                    cfg["yield_risk"]["cumulative_stress_scale"]
                )
            },
            output=yield_risk,
            uncertainty=0.08,
            day=day,
        )
    )

    new_state = state.with_updates(
        timestamp=weather.timestamp,
        soil_moisture_surface=sw.surface_moisture,
        soil_moisture_root=sw.root_zone_moisture,
        soil_moisture_deep=sw.deep_zone_moisture,
        soil_temperature=0.8 * state.soil_temperature + 0.2 * weather.temperature,
        soil_water_deficit=deficit,
        rainfall=weather.rainfall,
        temperature=weather.temperature,
        evapotranspiration=sw.actual_et,
        humidity=weather.humidity,
        crop_stage=stage,
        crop_stage_sensitivity=sensitivity,
        day_of_season=new_day_of_season,
        crop_health_index=health,
        biomass_proxy=biomass,
        ndvi_proxy=ndvi_proxy,
        ndmi_proxy=ndmi_proxy,
        crop_water_stress=stress,
        secondary_stress=secondary,
        irrigation_available=capacity,
        irrigation_demand=demand,
        irrigation_applied=applied,
        nutrient_status_proxy=nutrient,
        disease_pressure_proxy=disease,
        water_reserve=reserve_fraction,
        water_reserve_mm=reserve_mm,
        yield_risk=yield_risk,
        runoff=sw.runoff,
        drainage=sw.drainage,
        source_type="derived",
    )

    return StepResult(
        state=new_state,
        transitions=transitions,
        cumulative_weighted_stress=cumulative,
        irrigation_requested=requested,
        irrigation_applied=applied,
    )


def next_timestamp(previous: datetime) -> datetime:
    return previous + timedelta(days=1)