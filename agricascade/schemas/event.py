"""Cascade event schema.

Events make the cascade explainable without an LLM: each event records its
cause, effect, severity, confidence, preceding events and the state change it
represents (spec section 23).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class CascadeEvent:
    """One detected transition/threshold-crossing in the cascade timeline."""

    event_id: str
    timestamp: datetime
    day: int
    cause: str
    effect: str
    severity: float
    confidence: float = 1.0
    preceding_events: list[str] = field(default_factory=list)
    affected_variables: list[str] = field(default_factory=list)
    state_before: dict[str, float] = field(default_factory=dict)
    state_after: dict[str, float] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.severity <= 1.0:
            raise ValueError("severity must be within [0, 1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        if isinstance(self.timestamp, datetime):
            out["timestamp"] = self.timestamp.isoformat()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CascadeEvent":
        payload = dict(data)
        ts = payload.get("timestamp")
        if isinstance(ts, str):
            payload["timestamp"] = datetime.fromisoformat(ts)
        return cls(**payload)

    def severity_label(self) -> str:
        if self.severity >= 0.75:
            return "SEVERE"
        if self.severity >= 0.4:
            return "MODERATE"
        return "MILD"