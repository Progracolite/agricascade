"""Page 1: WHAT IS HAPPENING NOW? (presentation only)."""
from __future__ import annotations
import streamlit as st
from app.components.runner import get_result, sidebar
from app.components.ui import (apply_theme, hero, prov_tag, status_dot,
    storyline, stress_line, water_line)

st.set_page_config(page_title="01 Field Today — AgriCascade", layout="wide")
apply_theme()
st.markdown("# AGRICASCADE")
storyline(0)
choice, horizon, seed, region, mc_n = sidebar()
r = get_result(choice, horizon, seed, region, mc_n)
s0 = r["initial_state"]
if s0 is None:
    st.warning("No field state is available for this configuration.")
    st.stop()
hero("What is happening now?", "The reconstructed field condition everything else plays forward from.")
st.markdown(f"<p class='big-story'>🌾 {water_line(s0.soil_moisture_root)} {stress_line(s0.crop_water_stress)}</p>", unsafe_allow_html=True)
a, b = st.columns(2)
with a:
    st.markdown(f"<div class='stage'>💧 <b>Water around the roots</b><br>{water_line(s0.soil_moisture_root)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='stage'>🌱 <b>Crop condition</b><br>{stress_line(s0.crop_water_stress)}</div>", unsafe_allow_html=True)
with b:
    sc = r["scenario"]
    dist = ", ".join(f"{d.type} (day {d.start_time}, {d.duration}d)" for d in sc.disturbances) or "no disturbance"
    st.markdown(f"<div class='stage stage-warn'>🌡️ <b>Weather pressure</b><br>{sc.name}: {dist}.</div>", unsafe_allow_html=True)
    try:
        rv = float(s0.water_reserve)
        rv_txt = "a strong reserve" if rv >= 0.70 else ("a moderate reserve" if rv >= 0.40 else "a limited reserve")
    except (TypeError, ValueError):
        rv_txt = "an unknown reserve"
    st.markdown(f"<div class='stage'>🌊 <b>Water reserve</b><br>The field starts with {rv_txt}.</div>", unsafe_allow_html=True)
st.info("This is the reconstructed current state used by the simulator — not a prediction.")
obs_tag = prov_tag(r["observation_report"].get("weather", ""))
soil_tag = prov_tag(r["soil_report"])
if "SYNTHETIC" in (obs_tag, soil_tag):
    st.caption("🧪 SYNTHETIC SCENARIO — a controlled simulated field, not a live measurement.")
else:
    st.caption(f"Data: weather {obs_tag} | soil {soil_tag}.")
with st.expander("Scientific details ↗"):
    st.write("initial_state:", s0.to_dict())
st.caption("Next: 02 — IF NOTHING CHANGES → How could the damage spread?")
