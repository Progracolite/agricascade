"""Intervention schema.

Interventions operate on state variables and are always re-simulated with the
same cascade engine. They are reported as SIMULATED interventions, never as
autonomous prescriptions for farmers (spec section 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

INTERVENTION_TYPES = (
    "partial_irrigation",
    "full_irrigation",
    "irrigation_delay",
    "water_allocation",
    "drainage_intervention",
)


@dataclass
class Intervention:
    """A candidate intervention applied during cascade simulation."""

    intervention_id: str
    type: str
    start_time: int              # day index relative to the branch/decision day
    duration: int
    magnitude: float             # e.g. mm of irrigation
    affected_state: tuple[str, ...] = ("soil_moisture_root",)
    cost: float = 0.0            # normalised operational cost proxy (assumed)
    resource_requirement: float = 0.0  # irrigation demand in mm
    disruption_score: float = 0.0
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in INTERVENTION_TYPES:
            raise ValueError(
                f"Unknown intervention type {self.type!r}. "
                f"Expected one of {INTERVENTION_TYPES}"
            )
        if self.duration < 0:
            raise ValueError("duration must be >= 0")
        if not 0.0 <= self.disruption_score <= 1.0:
            raise ValueError("disruption_score must be within [0, 1]")

    def daily_application(self, day: int, total_days: int) -> float:
        """Return the amount (mm) applied on a given absolute day index.

        The intervention is spread evenly over its application window starting
        at ``start_time``.
        """
        if self.duration <= 0:
            return 0.0
        if self.start_time <= day < self.start_time + self.duration:
            return self.magnitude / self.duration
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["affected_state"] = list(self.affected_state)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Intervention":
        payload = dict(data)
        if payload.get("affected_state"):
            payload["affected_state"] = tuple(payload["affected_state"])
        return cls(**payload)