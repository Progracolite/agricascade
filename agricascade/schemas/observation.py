"""Observation schema and the provenance contract.

Every record in the system carries enough provenance to answer: where did this
come from, when, what processing step produced it, and is it measured or
estimated (spec sections 7 and 60).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

# The three data layers (spec section 7).
SOURCE_TYPES = ("observed", "derived", "synthetic")


@dataclass
class Provenance:
    """Traceability for a single value or record."""

    source: str
    source_date: Optional[str] = None
    processing_step: str = ""
    observed_or_estimated: str = "observed"

    def __post_init__(self) -> None:
        if self.observed_or_estimated not in SOURCE_TYPES:
            raise ValueError(
                f"observed_or_estimated must be one of {SOURCE_TYPES}, "
                f"got {self.observed_or_estimated!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Provenance":
        return cls(**data)

    @classmethod
    def synthetic(
        cls, source: str, processing_step: str = "scenario_generation"
    ) -> "Provenance":
        return cls(
            source=source,
            processing_step=processing_step,
            observed_or_estimated="synthetic",
        )

    @classmethod
    def derived(
        cls, source: str, source_date: str | None = None, processing_step: str = ""
    ) -> "Provenance":
        return cls(
            source=source,
            source_date=source_date,
            processing_step=processing_step,
            observed_or_estimated="derived",
        )


@dataclass
class Observation:
    """A single observed/derived/synthetic variable at a point or region."""

    variable: str
    value: float
    timestamp: datetime
    provenance: Provenance
    uncertainty: Optional[float] = None
    region: Optional[str] = None
    unit: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def source_type(self) -> str:
        return self.provenance.observed_or_estimated

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        if isinstance(self.timestamp, datetime):
            out["timestamp"] = self.timestamp.isoformat()
        out["source_type"] = self.source_type
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        payload = dict(data)
        payload.pop("source_type", None)
        payload["provenance"] = Provenance.from_dict(payload["provenance"])
        ts = payload.get("timestamp")
        if isinstance(ts, str):
            payload["timestamp"] = datetime.fromisoformat(ts)
        return cls(**payload)


def observations_to_frame(observations: list[Observation]):
    """Convert observations to a tidy pandas DataFrame."""
    import pandas as pd

    rows = []
    for obs in observations:
        rows.append(
            {
                "timestamp": obs.timestamp,
                "variable": obs.variable,
                "value": obs.value,
                "uncertainty": obs.uncertainty,
                "source": obs.provenance.source,
                "source_type": obs.source_type,
                "region": obs.region,
                "unit": obs.unit,
            }
        )
    return pd.DataFrame(rows)