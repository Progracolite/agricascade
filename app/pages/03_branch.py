"""Page 3: THE FUTURE SPLITS HERE (presentation only)."""
from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st
from app.components.runner import get_result, sidebar
from app.components.ui import apply_theme, hero, storyline

st.set_page_config(page_title="03 The Turning Point — AgriCascade", layout="wide")
apply_theme()
st.markdown("# AGRICASCADE")
storyline(2)
choice, horizon, seed, region, mc_n = sidebar()
r = get_result(choice, horizon, seed, region, mc_n)
branch = r["critical_branch"]
if branch is None:
    hero("No turning point found.", "Under this scenario, the model did not find a sufficiently sensitive point.")
    st.stop()


def _plain(v) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "an uncertain simulated outcome"
    if x >= 0.50:
        return "tips toward a damaging cascade"
    if x >= 0.30:
        return "lands under serious stress"
    if x >= 0.10:
        return "stays strained but manageable"
    return "recovers toward a manageable state"


alt = branch.alternate_outcomes or {}
drier = float(alt.get("drier", 0.0))
wetter = float(alt.get("wetter", 0.0))
blo = float(branch.baseline_outcome)
hero("The future splits here.", "At this point, small changes in root-zone water lead to substantially different simulated futures.")
st.markdown(f"## DAY {branch.day}")
fig = go.Figure()
fig.add_trace(go.Scatter(x=[0, branch.day], y=[blo, blo], name="Current state", mode="lines", line={"width": 6, "color": "#6b7280"}))
fig.add_trace(go.Scatter(x=[branch.day, horizon], y=[blo, drier], name="Drier future", mode="lines", line={"width": 6, "color": "#dc2626"}))
fig.add_trace(go.Scatter(x=[branch.day, horizon], y=[blo, wetter], name="Wetter future", mode="lines", line={"width": 6, "color": "#16a34a"}))
fig.add_trace(go.Scatter(x=[branch.day], y=[blo], name="Turning point", mode="markers", marker={"size": 20, "color": "#f59e0b", "line": {"width": 2, "color": "#78350f"}}))
fig.update_layout(height=480, margin={"l": 10, "r": 10, "t": 50, "b": 10}, title="One present. Two simulated futures.",
    xaxis_title="Days from today", yaxis_title="Harvest risk (low → high)", legend={"orientation": "h", "y": -0.2})
st.plotly_chart(fig, use_container_width=True)
st.caption("Fork arms join the branch-day outcome to each re-simulated future outcome — no fabricated daily paths.")
left, right = st.columns(2)
with left:
    st.markdown(f"<div class='fork-box stage-hot'>🔴 <b>IF CONDITIONS SHIFT DRIER</b><br><br>The field {_plain(drier)}.<br><i>Simulated outcome.</i></div>", unsafe_allow_html=True)
with right:
    st.markdown(f"<div class='fork-box stage-ok'>🟢 <b>IF CONDITIONS SHIFT WETTER</b><br><br>The field {_plain(wetter)}.<br><i>Simulated outcome.</i></div>", unsafe_allow_html=True)
st.markdown("### Why does this matter?")
st.write(f"Around day {branch.day}, acting has the largest leverage — after this point the two futures pull apart.")
with st.expander("Scientific details ↗"):
    st.write(branch.to_dict())
    st.write(r["explanations"]["branch"])
st.info("Identified by re-simulating the same model under slightly different conditions. Model sensitivity — not a guaranteed prediction, and not an experimentally proven real-world threshold.")
st.caption("Next: 04 — TEST AN INTERVENTION → Can we change the outcome?")
