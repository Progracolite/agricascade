"""Shared runner: the ONLY place that calls the computational pipeline (no logic here)."""
from __future__ import annotations
import streamlit as st
from agricascade.evaluation.ground_truth import monsoon_break_scenario
from agricascade.pipeline import analyze_agricultural_cascade
from agricascade.schemas.scenario import Disturbance, Scenario

def get_scenario(choice: str, horizon: int, seed: int) -> Scenario:
    if choice.startswith("monsoon"):
        return monsoon_break_scenario(horizon, seed)
    if choice == "heavy_rain":
        return Scenario(scenario_id="heavy_rain", name="Heavy Rain",
            disturbances=[Disturbance(type="heavy_rain", start_time=3, duration=3,
                rainfall_multiplier=3.0, affected_state=("rainfall",), spatial_scope="region")],
            horizon_days=horizon, seed=seed)
    return Scenario(scenario_id="normal", name="Normal", horizon_days=horizon, seed=seed)

def get_result(choice: str, horizon: int, seed: int, region: str, mc_n: int) -> dict:
    key = (choice, horizon, seed, region, mc_n)
    if st.session_state.get("result_key") != key or st.session_state.get("result") is None:
        sc = get_scenario(choice, horizon, seed)
        with st.spinner("Simulating cascade..."):
            st.session_state.result = analyze_agricultural_cascade(
                scenario=sc, horizon_days=horizon, seed=seed, region=region,
                mc_trajectories=mc_n)
            st.session_state.result_key = key
    return st.session_state.result

def sidebar() -> tuple[str, int, int, str, int]:
    with st.sidebar:
        st.header("Scenario controls")
        choice = st.selectbox("Scenario", ["monsoon_break (killer demo)", "normal", "heavy_rain"], index=0)
        horizon = st.slider("Horizon (days)", 7, 21, 14)
        seed = int(st.number_input("Random seed", value=42, step=1))
        region = st.selectbox("Region", ["thrissur", "palakkad", "alappuzha"], index=0)
        mc_n = st.slider("Monte Carlo trajectories", 20, 1000, 1000)
    return choice, horizon, seed, region, mc_n
