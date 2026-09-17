"""Page 2: WHAT HAPPENS NEXT? (presentation only)."""
from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st
from app.components.runner import get_result, sidebar
from app.components.ui import (EVENT_META, apply_theme, event_sentence,
    event_title, hero, status_dot, storyline)

st.set_page_config(page_title="02 What Happens Next — AgriCascade", layout="wide")
apply_theme()
st.markdown("# AGRICASCADE")
storyline(1)
choice, horizon, seed, region, mc_n = sidebar()
r = get_result(choice, horizon, seed, region, mc_n)
base = r["baseline"]
mc = r["monte_carlo"] or {}
if base is None or not getattr(base, "states", None):
    st.warning("No cascade is available for this configuration.")
    st.stop()
hero("What happens next?", "We let the current conditions play forward.")
term = str(base.terminal_state).replace("_", " ").lower()
st.markdown(f"<p class='big-story'>{status_dot(base.terminal_state)} If nothing changes, the field drifts toward <b>{term}</b>. <i>Simulated outcome, under this scenario.</i></p>", unsafe_allow_html=True)
st.markdown("<div class='stage'>🟢 <b>TODAY</b> — the reconstructed field.</div>", unsafe_allow_html=True)
sc = r["scenario"]
dist = ", ".join(f"{d.type} (day {d.start_time}, {d.duration}d)" for d in sc.disturbances) or "no disturbance"
st.markdown(f"<div class='stage stage-warn'>🌩️ <b>DISTURBANCE</b> — {sc.name}: {dist}.</div>", unsafe_allow_html=True)
events = sorted(list(base.events or []), key=lambda e: int(e.day))
for e in events[:10]:
    icon, title, _ = EVENT_META.get(str(e.effect), ("📌", str(e.effect).replace("_", " "), ""))
    st.markdown(f"<div class='stage'><b>DAY {e.day}</b> — {icon} <b>{title}</b><br>{event_sentence(e)}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='stage stage-hot'>{status_dot(base.terminal_state)} <b>CASCADE</b> — the field ends {term}.</div>", unsafe_allow_html=True)
st.caption("Timeline order comes only from events the simulator actually activated — nothing invented.")
days = list(range(len(base.states)))
risk = [s.yield_risk for s in base.states]
stress = [s.crop_water_stress for s in base.states]
reserve = [s.water_reserve for s in base.states]
fig = go.Figure()
fig.add_trace(go.Scatter(x=days, y=risk, name="Harvest risk", mode="lines", line={"width": 5, "color": "#dc2626"}))
fig.add_trace(go.Scatter(x=days, y=stress, name="Crop stress", mode="lines", line={"width": 3, "color": "#f59e0b"}))
fig.add_trace(go.Scatter(x=days, y=reserve, name="Water reserve", mode="lines", line={"width": 2, "color": "#16a34a", "dash": "dot"}, opacity=0.7))
for e in events[:6]:
    try:
        d = int(e.day)
    except (TypeError, ValueError):
        continue
    fig.add_annotation(x=d, y=max(risk[d], stress[d]), text=f"Day {d}: {event_title(str(e.effect))}", showarrow=True, arrowhead=1)
fig.update_layout(height=480, margin={"l": 10, "r": 10, "t": 50, "b": 10}, title="HEALTHY → STRESSED → CASCADE",
    xaxis_title="Days from today", yaxis_title="Pressure (low → high)", legend={"orientation": "h", "y": -0.2})
st.plotly_chart(fig, use_container_width=True)
st.caption("Red is the harvest at risk rising; orange is crop stress; dotted green is the reserve draining. Shape first, numbers later.")
try:
    n = int(mc.get("n", 0))
    p = float(mc.get("p_severe", 0.0) or 0.0)
    bad = int(round(p * n))
    st.markdown(f"<p class='big-story'>In {bad} of {n} simulated futures, the field tips into severe stress.</p>", unsafe_allow_html=True)
    st.caption("These shares come from re-running the same simulator with small seeded variations — not a separate prediction model.")
except (TypeError, ValueError):
    st.write("Possible-futures data is unavailable.")
with st.expander("Scientific details ↗"):
    st.write("summary:", base.summary())
    st.write("events:", [e.to_dict() for e in base.events])
    st.write("monte_carlo:", {k: v for k, v in mc.items() if k != "terminals"})
st.caption("Next: 03 — THE TURNING POINT → Where can the future split?")
