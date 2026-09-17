"""Scenario and disturbance schema.

A scenario applies controlled shocks to the state transitions. It NEVER
directly assigns an outcome such as ``yield_loss = 17%`` — yield risk must
emerge from the state transitions (spec section 17).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

DISTURBANCE_TYPES = (
    "heatwave",
    "rainfall_deficit",
    "heavy_rain",
    "irrigation_failure",
    "water_reserve_reduction",
    "disease_pressure",
    "compound_shock",
)


@dataclass
class Disturbance:
    """A controlled shock applied to one or more state drivers."""

    type: str
    start_time: int                 # day index relative to scenario start
    duration: int                   # days
    intensity: float = 1.0          # 0..1 normalised severity of the disturbance
    affected_state: tuple[str, ...] = ()
    spatial_scope: str = "region"

    # Driver modifiers. 1.0 = no change. These are scenario assumptions.
    rainfall_multiplier: float = 1.0
    temperature_delta: float = 0.0
    et_multiplier: float = 1.0
    irrigation_capacity_multiplier: float = 1.0
    humidity_delta: float = 0.0
    disease_pressure_delta: float = 0.0
    reserve_drain_delta: float = 0.0

    def __post_init__(self) -> None:
        if self.type not in DISTURBANCE_TYPES:
            raise ValueError(
                f"Unknown disturbance type {self.type!r}. "
                f"Expected one of {DISTURBANCE_TYPES}"
            )
        if self.duration < 0:
            raise ValueError("duration must be >= 0")
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError("intensity must be within [0, 1]")

    def is_active(self, day: int) -> bool:
        return self.start_time <= day < self.start_time + self.duration

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["affected_state"] = list(self.affected_state)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Disturbance":
        payload = dict(data)
        if payload.get("affected_state"):
            payload["affected_state"] = tuple(payload["affected_state"])
        return cls(**payload)


@dataclass
class Scenario:
    """A named, reproducible cascade scenario."""

    scenario_id: str
    name: str
    description: str = ""
    disturbances: list[Disturbance] = field(default_factory=list)
    horizon_days: int = 14
    seed: int = 42
    start_of_season_day: int = 60
    initial_overrides: dict[str, float] = field(default_factory=dict)
    source_type: str = "synthetic"

    def __post_init__(self) -> None:
        if not isinstance(self.horizon_days, int) or self.horizon_days < 1:
            raise ValueError(
                f"horizon_days must be a positive integer, got {self.horizon_days!r}")
        if self.start_of_season_day < 0:
            raise ValueError("start_of_season_day must be >= 0")
        for d in self.disturbances:
            if d.start_time < 0:
                raise ValueError("disturbance start_time must be >= 0")

    def active_disturbances(self, day: int) -> list[Disturbance]:
        return [d for d in self.disturbances if d.is_active(day)]

    def modifiers_for_day(self, day: int) -> dict[str, float]:
        """Combine all active disturbances into per-day driver modifiers."""
        rainfall = 1.0
        temperature = 0.0
        et = 1.0
        irrigation = 1.0
        humidity = 0.0
        disease = 0.0
        reserve_drain = 0.0

        for d in self.active_disturbances(day):
            rainfall *= d.rainfall_multiplier
            temperature += d.temperature_delta
            et *= d.et_multiplier
            irrigation *= d.irrigation_capacity_multiplier
            humidity += d.humidity_delta
            disease += d.disease_pressure_delta
            reserve_drain += d.reserve_drain_delta

        return {
            "rainfall_multiplier": rainfall,
            "temperature_delta": temperature,
            "et_multiplier": et,
            "irrigation_capacity_multiplier": irrigation,
            "humidity_delta": humidity,
            "disease_pressure_delta": disease,
            "reserve_drain_delta": reserve_drain,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "disturbances": [d.to_dict() for d in self.disturbances],
            "horizon_days": self.horizon_days,
            "seed": self.seed,
            "start_of_season_day": self.start_of_season_day,
            "initial_overrides": dict(self.initial_overrides),
            "source_type": self.source_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        payload = dict(data)
        payload["disturbances"] = [
            Disturbance.from_dict(d) for d in payload.get("disturbances", [])
        ]
        return cls(**payload)