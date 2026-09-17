"""State initialization.

Reconstructs the current agricultural state from observations where available
and from a reproducible synthetic field where not. The synthetic field is
anchored to config values (realism calibration, spec section 71) and is
explicitly marked synthetic.

Same seed reproduces the same field (spec section 70).
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from datetime import datetime
from typing import Any, Iterable

from agricascade.features.soil_features import (
    default_soil_properties,
    soil_properties_from_texture,
)
from agricascade.physics.crop_stress import (
    crop_health_index,
    soil_water_deficit,
    stage_for_day,
    stage_water_sensitivity,
    water_stress,
)
from agricascade.physics.water_balance import resolve_soil_parameters
from agricascade.schemas.observation import Observation, Provenance
from agricascade.schemas.scenario import Scenario
from agricascade.schemas.state import AgriculturalState
from agricascade.utils.io import load_crop_config, load_model_config
from agricascade.utils.random import make_rng

# Monsoon-season start used as the default scenario anchor.
DEFAULT_START_DATE = datetime(2026, 6, 1)

# Climatological fallbacks for Kerala rice-growing areas (assumed, not observed).
DEFAULT_TEMPERATURE_C = 27.0
DEFAULT_HUMIDITY_PCT = 80.0
DEFAULT_RAINFALL_MM = 8.0
DEFAULT_ET_MM = 4.0
DEFAULT_NDVI = 0.65
DEFAULT_NDMI = 0.15


@dataclass
class SyntheticField:
    """A reproducible, explicitly synthetic field definition."""

    field_id: str
    region: str
    crop: str
    crop_stage: str
    soil_type: str
    soil_properties: dict[str, float]
    area_ha: float
    initial_moisture: dict[str, float]
    water_reserve_mm: float
    irrigation_capacity: float
    management: dict[str, Any]
    provenance: dict[str, str] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_id": self.field_id,
            "region": self.region,
            "crop": self.crop,
            "crop_stage": self.crop_stage,
            "soil_type": self.soil_type,
            "soil_properties": dict(self.soil_properties),
            "area_ha": self.area_ha,
            "initial_moisture": dict(self.initial_moisture),
            "water_reserve_mm": self.water_reserve_mm,
            "irrigation_capacity": self.irrigation_capacity,
            "management": dict(self.management),
            "provenance": dict(self.provenance),
            "source_type": "synthetic",
        }


def generate_field(
    seed: int = 42,
    soil_type: str | None = None,
    area: float | None = None,
    crop: str = "rice",
    crop_stage: str = "flowering",
    initial_moisture: dict[str, float] | None = None,
    region: str = "thrissur",
    config: dict[str, Any] | None = None,
) -> SyntheticField:
    """Generate a synthetic field deterministically from a seed.

    Values are anchored to historical rainfall ranges, soil properties and
    config defaults (spec section 71), not chosen arbitrarily.
    """
    cfg = config or load_model_config()
    rng = make_rng(seed)

    textures = ["sandy_loam", "loam", "silt_loam", "clay_loam", "clay"]
    chosen_texture = soil_type or textures[int(rng.integers(0, len(textures)))]
    soil_properties = soil_properties_from_texture(chosen_texture)

    soil = cfg["soil"]
    irrig = cfg["irrigation"]
    theta_fc = resolve_soil_parameters(soil_properties, cfg)["theta_fc"]
    theta_wp = soil["wilting_point_theta"]
    # Healthy start: midway between critical and field capacity.
    healthy_root = 0.5 * (soil["critical_theta"] + theta_fc)
    if initial_moisture is None:
        root = float(rng.uniform(healthy_root - 0.01, healthy_root + 0.01))
        moisture = {
            "surface": root + 0.02,
            "root": root,
            "deep": root - 0.01,
        }
    else:
        moisture = {
            "surface": float(initial_moisture.get("surface", initial_moisture.get("root", healthy_root) + 0.02)),
            "root": float(initial_moisture.get("root", healthy_root)),
            "deep": float(initial_moisture.get("deep", initial_moisture.get("root", healthy_root) - 0.01)),
        }

    reserve_total = float(irrig["reserve_total_mm"])
    reserve_fraction = float(
        rng.uniform(
            irrig["reserve_start_fraction"] - 0.05,
            min(0.95, irrig["reserve_start_fraction"] + 0.10),
        )
    )

    field_id = f"SYN-{region.upper()[:3]}-{int(seed):04d}-{chosen_texture[:3].upper()}"

    return SyntheticField(
        field_id=field_id,
        region=region,
        crop=crop,
        crop_stage=crop_stage,
        soil_type=chosen_texture,
        soil_properties=soil_properties,
        area_ha=float(area if area is not None else rng.uniform(0.4, 2.5)),
        initial_moisture=moisture,
        water_reserve_mm=reserve_total * reserve_fraction,
        irrigation_capacity=float(rng.uniform(0.85, 1.0)),
        management={
            "irrigation_source": "synthetic_reserve",
            "reserve_total_mm": reserve_total,
            "note": "Synthetic field-operational state; not a real farm record.",
        },
        provenance={
            "source": "agricascade.synthetic_field_generator",
            "observed_or_estimated": "synthetic",
        },
    )


def _latest_observations(
    observations: Iterable[Observation] | dict[str, Any] | None,
) -> dict[str, Observation | dict[str, Any]]:
    """Reduce observations to the latest value per variable."""
    if observations is None:
        return {}
    if isinstance(observations, dict):
        return {k: {"value": v} for k, v in observations.items()}

    latest: dict[str, Observation] = {}
    for obs in observations:
        if not isinstance(obs, Observation):
            raise TypeError(
                "observations must be a list of Observation or a mapping"
            )
        current = latest.get(obs.variable)
        if current is None or obs.timestamp >= current.timestamp:
            latest[obs.variable] = obs
    return latest


def _obs_value(obs_map: dict[str, Any], *names: str, default: float) -> float:
    for name in names:
        if name in obs_map:
            entry = obs_map[name]
            if isinstance(entry, Observation):
                return float(entry.value)
            if isinstance(entry, dict) and "value" in entry:
                return float(entry["value"])
    return float(default)


def _obs_timestamp(obs_map: dict[str, Any]) -> datetime | None:
    stamps = [
        entry.timestamp
        for entry in obs_map.values()
        if isinstance(entry, Observation)
    ]
    return max(stamps) if stamps else None


def initialize_state(
    observations: Iterable[Observation] | dict[str, Any] | None = None,
    seed: int = 42,
    *,
    region: str | None = None,
    scenario: Scenario | None = None,
    crop_config: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    field: SyntheticField | None = None,
) -> AgriculturalState:
    """Initialize the canonical state from observations and a synthetic field."""
    cfg = config or load_model_config()
    crop_cfg = crop_config or load_crop_config()
    obs_map = _latest_observations(observations)

    obs_region = None
    for entry in obs_map.values():
        if isinstance(entry, Observation) and entry.region:
            obs_region = entry.region
            break
    chosen_region = region or obs_region or "thrissur"

    if field is None:
        texture_obs = None
        sand = None
        clay = None
        if "soil_sand" in obs_map:
            sand = _obs_value(obs_map, "soil_sand", default=0.45)
        if "soil_clay" in obs_map:
            clay = _obs_value(obs_map, "soil_clay", default=0.20)
        if sand is not None and clay is not None:
            from agricascade.features.soil_features import texture_from_sand_clay

            texture_obs = texture_from_sand_clay(sand, clay)
        field = generate_field(
            seed=seed,
            soil_type=texture_obs,
            region=chosen_region,
            crop="rice",
            crop_stage=stage_for_day(
                int(cfg["simulation"]["start_of_season_day"]), crop_cfg
            ),
            config=cfg,
        )

    overrides: dict[str, float] = {}
    if scenario is not None:
        overrides = dict(scenario.initial_overrides)

    # Weather drivers: prefer observations, else climatological fallback.
    temperature = _obs_value(obs_map, "temperature", default=DEFAULT_TEMPERATURE_C)
    humidity = _obs_value(obs_map, "humidity", "relative_humidity", default=DEFAULT_HUMIDITY_PCT)
    rainfall = _obs_value(obs_map, "rainfall", "precipitation", default=DEFAULT_RAINFALL_MM)
    et = _obs_value(obs_map, "evapotranspiration", "et", default=DEFAULT_ET_MM)

    ndvi = _obs_value(obs_map, "ndvi", default=DEFAULT_NDVI)
    ndmi = _obs_value(obs_map, "ndmi", default=DEFAULT_NDMI)

    # Moisture: scenario override > field initial state.
    root_moisture = float(
        overrides.get("soil_moisture_root", field.initial_moisture["root"])
    )
    surface_moisture = float(
        overrides.get("soil_moisture_surface", field.initial_moisture["surface"])
    )
    deep_moisture = float(
        overrides.get("soil_moisture_deep", field.initial_moisture["deep"])
    )

    start_of_season = int(
        scenario.start_of_season_day
        if scenario is not None
        else cfg["simulation"]["start_of_season_day"]
    )
    start_date = _obs_timestamp(obs_map) or DEFAULT_START_DATE

    stage = stage_for_day(start_of_season, crop_cfg)
    sensitivity = stage_water_sensitivity(stage, crop_cfg)

    params = resolve_soil_parameters(field.soil_properties, cfg)
    theta_fc = params["theta_fc"]
    theta_wp = params["theta_wp"]
    critical = float(cfg["soil"]["critical_theta"])

    stress = water_stress(root_moisture, critical, theta_wp)
    deficit = soil_water_deficit(root_moisture, theta_fc, theta_wp)

    # Biomass anchored to observed/assumed NDVI.
    health_cfg = cfg["crop_health"]
    ndvi_lo, ndvi_hi = health_cfg["ndvi_range"]
    biomass = float(max(0.0, min(1.0, (ndvi - ndvi_lo) / (ndvi_hi - ndvi_lo))))
    health = crop_health_index(ndvi, ndmi, stress, cfg)

    reserve_total = float(cfg["irrigation"]["reserve_total_mm"])
    reserve_fraction = float(
        overrides.get(
            "water_reserve",
            field.water_reserve_mm / reserve_total if reserve_total > 0 else 0.0,
        )
    )
    reserve_mm = reserve_fraction * reserve_total

    state = AgriculturalState(
        timestamp=start_date,
        soil_moisture_surface=surface_moisture,
        soil_moisture_root=root_moisture,
        soil_moisture_deep=deep_moisture,
        soil_temperature=temperature,
        soil_water_deficit=deficit,
        rainfall=rainfall,
        temperature=temperature,
        evapotranspiration=et,
        humidity=humidity,
        crop_stage=stage,
        crop_stage_sensitivity=sensitivity,
        day_of_season=start_of_season,
        crop_health_index=health,
        biomass_proxy=biomass,
        ndvi_proxy=ndvi,
        ndmi_proxy=ndmi,
        crop_water_stress=stress,
        secondary_stress=float(overrides.get("secondary_stress", 0.0)),
        irrigation_available=field.irrigation_capacity,
        irrigation_demand=0.0,
        irrigation_applied=0.0,
        nutrient_status_proxy=float(cfg["nutrient"]["start_proxy"]),
        disease_pressure_proxy=float(cfg["disease"]["start_proxy"]),
        water_reserve=reserve_fraction,
        water_reserve_mm=reserve_mm,
        yield_risk=float(overrides.get("yield_risk", 0.0)),
        runoff=0.0,
        drainage=0.0,
        source_type="derived",
    )
    return state


def state_provenance(state: AgriculturalState) -> dict[str, Provenance]:
    """Document the provenance of the main state groups."""
    return {
        "weather": Provenance(
            source="Open-Meteo (or scenario fallback)",
            processing_step="initialize_state",
            observed_or_estimated="derived",
        ),
        "soil_moisture": Provenance(
            source="bucket water balance constrained by SoilGrids texture",
            processing_step="initialize_state",
            observed_or_estimated="derived",
        ),
        "field_operational_state": Provenance(
            source="synthetic field generator",
            processing_step="generate_field",
            observed_or_estimated="synthetic",
        ),
    }