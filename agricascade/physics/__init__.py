"""Physical core: lightweight water balance and crop stress."""

from agricascade.physics.crop_stress import (
    advance_stage,
    crop_health_index,
    soil_water_deficit,
    stage_for_day,
    stage_water_sensitivity,
    water_stress,
)
from agricascade.physics.drainage import deep_drainage, redistribute_excess
from agricascade.physics.infiltration import (
    effective_infiltration_fraction,
    partition_incoming,
)
from agricascade.physics.water_balance import (
    SoilWaterState,
    layer_thicknesses,
    resolve_soil_parameters,
    soil_water_update,
)

__all__ = [
    "SoilWaterState",
    "advance_stage",
    "crop_health_index",
    "deep_drainage",
    "effective_infiltration_fraction",
    "layer_thicknesses",
    "partition_incoming",
    "redistribute_excess",
    "resolve_soil_parameters",
    "soil_water_deficit",
    "soil_water_update",
    "stage_for_day",
    "stage_water_sensitivity",
    "water_stress",
]