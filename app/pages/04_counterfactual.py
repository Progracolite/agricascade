"""Page 4: CAN WE BREAK THE CASCADE? (presentation only)."""
from __future__ import annotations
import streamlit as st
from app.components.runner import get_result, sidebar
from app.components.ui import (apply_theme, compare_fig, hero, prov_tag,
    status_dot, storyline)

st.set_page_config(page_title="04 Break the Cascade — AgriCascade", layout="wide")
apply_theme()
st.markdown("# AGRICASCADE")
storyline(3)
choice, horizon, seed, region, mc_n = sidebar()
r = get_result(choice, horizon, seed, region, mc_n)
base = r["baseline"]
cf = r["counterfactual"]["trajectory"]
comp = r["counterfactual"]["comparison"]
ev = r["best_intervention"]
if base is None or cf is None or not getattr(base, "states", None) or not getattr(cf, "states", None):
    st.warning("No intervention comparison is available for this configuration.")
    st.stop()
hero("Can we break the cascade?", "We now test the intervention instead of assuming it works.")
name = ev.intervention.label if ev else "the simulated intervention"
st.markdown(f"# TEST SIMULATED INTERVENTION")
st.caption(f"Testing: **{name}**. Same scenario, same seed, same simulator on both sides — only the intervention differs. Simulated outcome, under this scenario.")
bl = str(comp["baseline_terminal"])
ct = str(comp["counterfactual_terminal"])
left, right = st.columns(2)
with left:
    st.markdown(f"<div class='fork-box stage-hot'>{status_dot(bl)}<br><b>WITHOUT INTERVENTION</b><br><br>The field ends {bl.replace('_', ' ').lower()}.<br>Field deteriorates.<br><i>Modelled outcome.</i></div>", unsafe_allow_html=True)
with right:
    st.markdown(f"<div class='fork-box stage-ok'>{status_dot(ct)}<br><b>WITH SIMULATED INTERVENTION</b><br><br>The field ends {ct.replace('_', ' ').lower()}.<br>Field recovers.<br><i>Modelled outcome — a model experiment, not a field instruction.</i></div>", unsafe_allow_html=True)
st.warning("SIMULATED INTERVENTION — a model experiment, not a field instruction. Never presented as 'this WILL happen'.")
st.markdown("### Same scenario. Different intervention. Different simulated future.")
st.plotly_chart(compare_fig(base, cf), use_container_width=True)
st.caption("Harvest-risk paths from the same simulator: without vs with the intervention. All values measured from re-simulation — including any metric that does not improve.")
with st.expander("Scientific details ↗"):
    st.write("comparison:", comp)
    st.write("candidates:", [{"label": e.intervention.label, "score": round(float(e.score), 3), "terminal": e.trajectory.terminal_state} for e in r["interventions"]])
    st.write(r["explanations"]["counterfactual"])
obs_tag = prov_tag(r["observation_report"].get("weather", ""))
soil_tag = prov_tag(r["soil_report"])
st.caption(f"Provenance: weather {obs_tag} | soil {soil_tag}. Synthetic stays labeled; simulated stays simulated.")
st.caption("Story complete: FIELD → DISTURBANCE → CASCADE → TURNING POINT → INTERVENTION.")
