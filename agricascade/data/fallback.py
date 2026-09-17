"""Dead-module guard: canonical loaders live in agricascade.data.loaders.

This module re-exports the canonical functions so legacy imports keep
working without duplicating schemas or logic (AGENTS.md rules 2-3).
"""
from __future__ import annotations
from agricascade.data.loaders import (
    demo_observations,
    kerala_statistics,
    observations_with_fallback,
    soil_properties_with_fallback,
)

__all__ = ["demo_observations", "kerala_statistics",
    "observations_with_fallback", "soil_properties_with_fallback"]
