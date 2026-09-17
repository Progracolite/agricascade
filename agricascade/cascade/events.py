"""Threshold-crossing event extraction (no LLM explanations)."""
from __future__ import annotations
from datetime import timedelta
from typing import Any
from agricascade.schemas.event import CascadeEvent
from agricascade.schemas.state import AgriculturalState

def _mk(day: int, state: AgriculturalState, cause: str, effect: str,
        severity: float, affected: list[str], before: dict[str, float],
        after: dict[str, float], desc: str, prior: list[CascadeEvent]) -> CascadeEvent:
    prev_ids = [e.event_id for e in prior[-3:]]
    return CascadeEvent(
        event_id=f"d{day:02d}-{effect}", timestamp=state.timestamp, day=day,
        cause=cause, effect=effect, severity=float(max(0.0, min(1.0, severity))),
        confidence=0.8, preceding_events=prev_ids,
        affected_variables=affected, state_before=before, state_after=after,
        description=desc)

def detect_threshold_crossings(new: AgriculturalState, old: AgriculturalState,
        day: int, config: dict[str, Any], prior: list[CascadeEvent]) -> list[CascadeEvent]:
    ev_cfg = config.get("events", {})
    out: list[CascadeEvent] = []
    def snap(s: AgriculturalState) -> dict[str, float]:
        return {"soil_moisture_root": s.soil_moisture_root,
            "crop_water_stress": s.crop_water_stress, "water_reserve": s.water_reserve,
            "secondary_stress": s.secondary_stress, "yield_risk": s.yield_risk,
            "rainfall": s.rainfall}
    b, a = snap(old), snap(new)
    if new.rainfall < float(ev_cfg.get("rainfall_deficit_mm", 1.0)) <= old.rainfall:
        out.append(_mk(day, new, "rainfall_deficit", "rainfall_deficit",
            0.5, ["rainfall"], b, a, f"Rainfall fell to {new.rainfall:.1f} mm.", prior + out))
    if new.soil_moisture_root < 0.22 <= old.soil_moisture_root:
        out.append(_mk(day, new, "soil_drying", "soil_moisture_decline", 0.5,
            ["soil_moisture_root"], b, a,
            f"Root-zone moisture declined to {new.soil_moisture_root:.2f}.", prior + out))
    if new.crop_water_stress >= float(ev_cfg.get("crop_stress_threshold", 0.4)) > old.crop_water_stress:
        out.append(_mk(day, new, "root_deficit", "crop_stress_onset",
            new.crop_water_stress, ["crop_water_stress"], b, a,
            f"Crop water stress reached {new.crop_water_stress:.2f}.", prior + out))
    if new.irrigation_demand >= float(ev_cfg.get("irrigation_demand_threshold_mm", 2.0)) > old.irrigation_demand:
        out.append(_mk(day, new, "crop_stress", "irrigation_demand_spike",
            min(1.0, new.irrigation_demand / 8.0), ["irrigation_demand"], b, a,
            f"Irrigation demand spiked to {new.irrigation_demand:.1f} mm/day.", prior + out))
    if new.water_reserve < float(ev_cfg.get("reserve_depletion_threshold", 0.25)) <= old.water_reserve:
        out.append(_mk(day, new, "irrigation_use", "water_reserve_depletion",
            0.7, ["water_reserve"], b, a,
            f"Water reserve depleted to {new.water_reserve:.0%}.", prior + out))
    if new.secondary_stress >= float(ev_cfg.get("secondary_stress_threshold", 0.5)) > old.secondary_stress:
        out.append(_mk(day, new, "reserve_shortfall", "secondary_stress_onset",
            new.secondary_stress, ["secondary_stress"], b, a,
            f"Secondary stress reached {new.secondary_stress:.2f}.", prior + out))
    if new.crop_water_stress >= float(ev_cfg.get("severe_stress_threshold", 0.75)) > old.crop_water_stress:
        out.append(_mk(day, new, "sustained_stress", "severe_stress",
            new.crop_water_stress, ["crop_water_stress", "yield_risk"], b, a,
            f"Severe crop stress {new.crop_water_stress:.2f}.", prior + out))
    return out

def explain_trajectory(events: list[CascadeEvent]) -> list[str]:
    lines = []
    for e in events:
        lines.append(f"Day {e.day}: {e.description} (cause: {e.cause})")
    return lines
