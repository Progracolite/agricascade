"""Texture-derived soil properties.

SCIENTIFIC NOTE: these texture classes and their property values are
pedotransfer approximations used to anchor synthetic fields. Real SoilGrids
retrievals override them when available. SoilGrids is 250 m; these values are
NOT 10 m field measurements (spec section 69).
"""

from __future__ import annotations

from typing import Any

# Coarse texture classes (sand, clay, silt as fractions) with approximate
# bulk density (g/cm3), organic carbon (g/kg), pH and CEC (cmol/kg).
SOIL_TEXTURES: dict[str, dict[str, float]] = {
    "sand": {"sand": 0.90, "clay": 0.03, "silt": 0.07, "bulk_density": 1.60, "organic_carbon": 6.0, "ph": 6.5, "cec": 4.0},
    "sandy_loam": {"sand": 0.65, "clay": 0.10, "silt": 0.25, "bulk_density": 1.50, "organic_carbon": 9.0, "ph": 6.2, "cec": 7.0},
    "loam": {"sand": 0.45, "clay": 0.20, "silt": 0.35, "bulk_density": 1.40, "organic_carbon": 14.0, "ph": 6.0, "cec": 12.0},
    "silt_loam": {"sand": 0.20, "clay": 0.18, "silt": 0.62, "bulk_density": 1.35, "organic_carbon": 18.0, "ph": 5.9, "cec": 15.0},
    "clay_loam": {"sand": 0.33, "clay": 0.34, "silt": 0.33, "bulk_density": 1.38, "organic_carbon": 16.0, "ph": 5.8, "cec": 20.0},
    "clay": {"sand": 0.20, "clay": 0.55, "silt": 0.25, "bulk_density": 1.30, "organic_carbon": 20.0, "ph": 5.6, "cec": 28.0},
}


def soil_properties_from_texture(texture: str) -> dict[str, float]:
    """Return soil properties for a texture class name."""
    if texture not in SOIL_TEXTURES:
        raise KeyError(
            f"Unknown soil texture {texture!r}. Expected one of "
            f"{sorted(SOIL_TEXTURES)}"
        )
    props = dict(SOIL_TEXTURES[texture])
    props["sand_fraction"] = props["sand"]
    props["clay_fraction"] = props["clay"]
    props["silt_fraction"] = props["silt"]
    props["texture"] = texture
    return props


def texture_from_sand_clay(sand_fraction: float, clay_fraction: float) -> str:
    """Nearest texture class by Euclidean distance in (sand, clay) space."""
    sand = float(sand_fraction)
    clay = float(clay_fraction)
    best_name = "loam"
    best_dist = float("inf")
    for name, props in SOIL_TEXTURES.items():
        dist = (props["sand"] - sand) ** 2 + (props["clay"] - clay) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


def properties_from_soilgrids(
    sand_fraction: float,
    clay_fraction: float,
    silt_fraction: float | None = None,
    bulk_density: float | None = None,
    organic_carbon: float | None = None,
    ph: float | None = None,
    cec: float | None = None,
) -> dict[str, float]:
    """Build a soil-properties dict from SoilGrids-style fractions."""
    if silt_fraction is None:
        silt_fraction = max(0.0, 1.0 - sand_fraction - clay_fraction)
    props = {
        "sand": float(sand_fraction),
        "clay": float(clay_fraction),
        "silt": float(silt_fraction),
        "sand_fraction": float(sand_fraction),
        "clay_fraction": float(clay_fraction),
        "silt_fraction": float(silt_fraction),
        "texture": texture_from_sand_clay(sand_fraction, clay_fraction),
    }
    if bulk_density is not None:
        props["bulk_density"] = float(bulk_density)
    if organic_carbon is not None:
        props["organic_carbon"] = float(organic_carbon)
    if ph is not None:
        props["ph"] = float(ph)
    if cec is not None:
        props["cec"] = float(cec)
    return props


def default_soil_properties(config: dict[str, Any] | None = None) -> dict[str, float]:
    """Fallback loam properties derived from the model config reference texture."""
    return soil_properties_from_texture("loam")