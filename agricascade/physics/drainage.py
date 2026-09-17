"""Drainage and inter-layer redistribution.

SCIENTIFIC ASSUMPTION: excess water above field capacity is split between
transfer to the layer below, deep percolation and a residual loss term using
configurable fractions. This is a simplified bucket model, not a
research-grade hydrological solver (spec sections 11-12).
"""

from __future__ import annotations

from typing import Any

from agricascade.utils.io import load_model_config


def redistribute_excess(
    excess_mm: float,
    config: dict[str, Any] | None = None,
    to_deep: bool = False,
) -> tuple[float, float, float]:
    """Split excess water above field capacity.

    Returns ``(transfer_mm, percolation_mm, loss_mm)``.

    * For the surface layer, ``transfer_mm`` moves into the root zone and
      ``percolation_mm`` moves straight to the deep layer.
    * For the root layer (``to_deep=True``), ``transfer_mm`` moves into the
      deep layer and ``percolation_mm`` is zero.
    """
    soil_cfg = (config or load_model_config())["soil"]
    if excess_mm <= 0:
        return 0.0, 0.0, 0.0

    root_transfer = float(soil_cfg["root_transfer_fraction"])
    deep_perc = float(soil_cfg["deep_drainage_fraction"])

    if to_deep:
        transfer = excess_mm * root_transfer
        percolation = 0.0
        loss = excess_mm - transfer
        return transfer, percolation, loss

    transfer = excess_mm * root_transfer
    percolation = excess_mm * deep_perc
    loss = excess_mm - transfer - percolation
    return transfer, percolation, loss


def deep_drainage(
    deep_storage_mm: float,
    deep_capacity_mm: float,
    config: dict[str, Any] | None = None,
) -> float:
    """Water leaving the deep layer when it exceeds field capacity."""
    if deep_storage_mm <= deep_capacity_mm:
        return 0.0
    return float(deep_storage_mm - deep_capacity_mm)