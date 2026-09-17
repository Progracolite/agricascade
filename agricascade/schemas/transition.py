"""Explicit state-transition and cascade-edge schemas.

Every state transition in the simulation is explicit: what changed, by which
function, with which inputs/parameters, and with what uncertainty (spec
sections 10 and 19).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class StateTransition:
    """A recorded transition between two named state variables."""

    source_state: str
    target_state: str
    function_name: str
    inputs: dict[str, float] = field(default_factory=dict)
    parameters: dict[str, float] = field(default_factory=dict)
    output: float = 0.0
    uncertainty: float = 0.0
    day: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CascadeEdge:
    """A directed dependency edge in the cascade graph.

    Attributes mirror spec section 19: lag, sensitivity, threshold, uncertainty
    and activation probability. Values are configurable model assumptions.
    """

    source: str
    target: str
    relationship: str = "monotonic_increasing"
    sensitivity: float = 1.0
    lag_days: int = 1
    threshold: float = 0.0
    uncertainty: float = 0.1
    activation_probability: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.activation_probability <= 1.0:
            raise ValueError("activation_probability must be within [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CascadeEdge":
        return cls(**data)