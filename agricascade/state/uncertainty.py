"""Uncertainty representation.

Estimated and forecast values are reported as ranges/bands, never as false
precision (spec section 39). Bootstrap percentiles are used for ensembles
rather than a Bayesian deep model (spec section 67).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


@dataclass
class UncertaintyBand:
    """A value with a lower/upper range."""

    value: float
    lower: float
    upper: float
    label: str = "estimated"

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("lower bound must not exceed upper bound")

    @property
    def half_width(self) -> float:
        return (self.upper - self.lower) / 2.0

    def format(self, decimals: int = 3) -> str:
        return (
            f"{self.value:.{decimals}f} "
            f"[{self.lower:.{decimals}f}, {self.upper:.{decimals}f}]"
        )

    def to_dict(self) -> dict[str, float | str]:
        return {
            "value": self.value,
            "lower": self.lower,
            "upper": self.upper,
            "label": self.label,
        }


def symmetric_band(
    value: float,
    sigma: float,
    z: float = 1.645,
    label: str = "estimated",
) -> UncertaintyBand:
    """Build a symmetric band around a value (default ~90% interval)."""
    return UncertaintyBand(
        value=float(value),
        lower=float(value - z * sigma),
        upper=float(value + z * sigma),
        label=label,
    )


def percentile_band(
    samples: Sequence[float] | Iterable[float],
    value: float | None = None,
    p_low: float = 10.0,
    p_high: float = 90.0,
    label: str = "model forecast range",
) -> UncertaintyBand:
    """P10/P50/P90 band from an ensemble of samples."""
    arr = np.asarray(list(samples), dtype=float)
    if arr.size == 0:
        raise ValueError("cannot build a band from an empty sample")
    lower = float(np.percentile(arr, p_low))
    upper = float(np.percentile(arr, p_high))
    median = float(np.percentile(arr, 50.0))
    return UncertaintyBand(
        value=float(value if value is not None else median),
        lower=lower,
        upper=upper,
        label=label,
    )


def summarize_samples(
    samples: Sequence[float] | Iterable[float],
) -> dict[str, float]:
    """Mean/std/P10/P50/P90 summary for an ensemble."""
    arr = np.asarray(list(samples), dtype=float)
    if arr.size == 0:
        raise ValueError("cannot summarise an empty sample")
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "p10": float(np.percentile(arr, 10.0)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
        "n": int(arr.size),
    }


def probability_of_exceedance(
    samples: Sequence[float] | Iterable[float],
    threshold: float,
) -> float:
    """Fraction of samples above a threshold."""
    arr = np.asarray(list(samples), dtype=float)
    if arr.size == 0:
        return 0.0
    return float(np.mean(arr > threshold))