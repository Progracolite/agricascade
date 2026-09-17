"""Data package: observation loaders with offline fallback."""
from agricascade.data.loaders import (
    demo_observations, fetch_open_meteo, fetch_soilgrids, kerala_statistics,
    observations_with_fallback, soil_properties_with_fallback,
)
__all__ = ["demo_observations", "fetch_open_meteo", "fetch_soilgrids",
    "kerala_statistics", "observations_with_fallback", "soil_properties_with_fallback"]

