"""Shared presentation helpers (formatting + layman wording only — no science)."""
from __future__ import annotations

# Centralized UI terminology map: technical key -> (human title, technical label).
TERMS = {
    "root_moisture": ("Water around the roots", "Root-zone moisture"),
    "surface_moisture": ("Surface water", "Surface-layer moisture"),
    "deep_moisture": ("Deeper soil water", "Deep-layer moisture"),
    "crop_stress": ("Crop stress", "Crop water stress"),
    "yield_risk": ("Risk to the harvest", "Yield-risk proxy"),
    "water_reserve": ("Water reserve", "Stored irrigation water"),
    "rainfall": ("Rainfall", "Daily rainfall"),
    "temperature": ("Temperature", "Air temperature"),
    "critical_branch": ("Future split point", "Critical branch"),
    "counterfactual": ("Simulated intervention", "Counterfactual simulation"),
    "p_severe": ("Chance of severe stress", "Monte Carlo simulation"),
    "p_cascade": ("Chance of a damaging cascade", "Monte Carlo simulation"),
    "terminal_state": ("Final field condition", "Terminal state"),
}

TERMINAL_PLAIN = {
    "STABLE": "The field ends the simulation stable",
    "RECOVERING": "The field ends the simulation recovering",
    "STRESSED": "The field ends the simulation under stress",
    "SEVERE_STRESS": "The field ends the simulation under severe stress",
    "CASCADE_CONTAINED": "The spreading damage ends the simulation contained",
    "CASCADE_ESCALATING": "The spreading damage ends the simulation still escalating",
}

STEPS = [
    ("01 — FIELD TODAY", "What is happening now?"),
    ("02 — IF NOTHING CHANGES", "How could the damage spread?"),
    ("03 — THE TURNING POINT", "Where can the future split?"),
    ("04 — TEST AN INTERVENTION", "Can we change the outcome?"),
]

FLOW_TAGLINE = "FIELD → DISTURBANCE → CASCADE → TURNING POINT → INTERVENTION"

THEME_CSS = """
<style>
.block-container { max-width: 1120px; padding-top: 1.2rem; }
h1 { letter-spacing: -0.02em; }
.hero-sub { font-size: 1.15rem; color: #4b5563; margin-top: -0.4rem; }
.storyline { font-size: 0.95rem; letter-spacing: 0.06em; color: #6b7280; }
.big-story { font-size: 1.6rem; line-height: 1.35; font-weight: 600; }
.stage { font-size: 1.05rem; padding: 0.55rem 0.8rem; border-radius: 0.6rem; background: #f8fafc; margin: 0.25rem 0; }
.stage-hot { background: #fef2f2; }
.stage-warn { background: #fffbeb; }
.stage-ok { background: #f0fdf4; }
.fork-box { text-align: center; padding: 1rem; border-radius: 0.8rem; }
.vs-label { font-size: 0.85rem; letter-spacing: 0.08em; color: #6b7280; }
</style>
"""

EVENT_META = {
    "irrigation_demand_spike": ("💧", "Water demand surges",
        "The crop calls for more irrigation than usual."),
    "crop_stress_onset": ("🌱", "Crop stress appears",
        "The earlier water shortage is now reaching the crop."),
    "rainfall_deficit": ("☁️", "Rain falls short",
        "Less rain arrives than the field needs."),
    "soil_moisture_decline": ("💧", "Water around the roots begins to fall",
        "Less available water increases pressure on the crop."),
}

STATUS_DOT = {
    "STABLE": "🟢", "RECOVERING": "🟡", "STRESSED": "🟠",
    "SEVERE_STRESS": "🔴", "CASCADE_CONTAINED": "🟢", "CASCADE_ESCALATING": "🔴",
}


def apply_theme() -> None:
    import streamlit as st
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    import streamlit as st
    st.markdown(f"# {title}")
    st.markdown(f"<p class='hero-sub'>{subtitle}</p>", unsafe_allow_html=True)


def storyline(active: int) -> None:
    import streamlit as st
    st.markdown(
        "<p class='storyline'>FIELD → DISTURBANCE → CASCADE → TURNING POINT → INTERVENTION</p>",
        unsafe_allow_html=True)
    flow_stepper(active)


def status_dot(t: str) -> str:
    return STATUS_DOT.get(str(t), "⚪")


def water_line(root) -> str:
    try:
        v = float(root)
    except (TypeError, ValueError):
        return "Root-zone water data is unavailable."
    if v >= 0.40:
        return "The field currently has enough root-zone water to support the crop."
    if v >= 0.25:
        return "Root-zone water is getting tight for the crop."
    return "Root-zone water is low — the crop is under water pressure."


def stress_line(s) -> str:
    try:
        v = float(s)
    except (TypeError, ValueError):
        return "Crop condition data is unavailable."
    if v <= 0.0:
        return "The crop shows no visible stress today."
    if v < 0.30:
        return "The crop shows early signs of stress."
    return "The crop is showing clear stress."


def event_title(effect: str) -> str:
    return EVENT_META.get(str(effect), ("📌", str(effect).replace("_", " "), ""))[1]


def event_sentence(e) -> str:
    meta = EVENT_META.get(str(e.effect))
    base = meta[2] if meta else ""
    desc = str(getattr(e, "description", "") or "")
    return f"{base} {desc}".strip() if base else desc



def flow_stepper(active: int) -> None:
    import streamlit as st
    cols = st.columns(4)
    for i, (title, sub) in enumerate(STEPS):
        with cols[i]:
            mark = "●" if i == active else "○"
            if i == active:
                st.markdown(f"**{mark} {title}**")
                st.caption(sub)
            else:
                st.caption(f"{mark} {title}")
    st.caption(FLOW_TAGLINE)


def prov_tag(report: object) -> str:
    return "SYNTHETIC" if "synthetic" in str(report).lower() else "OBSERVED / DERIVED"


def fmt_pct(x) -> str:
    try:
        return f"{float(x):.0%}"
    except (TypeError, ValueError):
        return "—"


def fmt2(x) -> str:
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return "—"


def fmt3(x) -> str:
    try:
        return f"{float(x):.3f}"
    except (TypeError, ValueError):
        return "—"


def plain_terminal(t: str) -> str:
    return TERMINAL_PLAIN.get(str(t), f"The field ends the simulation: {t}")


def field_sentence(s0) -> str:
    try:
        root = float(s0.soil_moisture_root)
        stress = float(s0.crop_water_stress)
        reserve = float(s0.water_reserve)
    except (TypeError, ValueError, AttributeError):
        return "Current field values are unavailable."
    water = "limited water availability" if root < 0.25 else ("moderate water availability" if root < 0.40 else "good water availability")
    st_ = "rising stress" if stress >= 0.30 else ("mild stress" if stress > 0.0 else "no visible stress")
    rv = "limited reserve" if reserve < 0.40 else ("a moderate reserve" if reserve < 0.70 else "a strong reserve")
    return f"The field currently has {water}, {st_}, and {rv}."


def why_block(title: str, why: str, how: str, technical: str) -> None:
    import streamlit as st
    st.markdown(f"**Why does this matter?** {why}")
    st.caption(f"How does AgriCascade know? {how}")
    with st.expander("Technical details"):
        st.write(technical)


def traj_frame(traj):
    import pandas as pd
    rows = []
    for i, s in enumerate(traj.states):
        rows.append({"day": i, "Water around the roots": s.soil_moisture_root,
                     "Crop stress": s.crop_water_stress, "Water reserve": s.water_reserve,
                     "Risk to the harvest": s.yield_risk})
    return pd.DataFrame(rows)


def cascade_fig(base, events=()):
    import plotly.graph_objects as go
    df = traj_frame(base)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["day"], y=df["Water around the roots"], name="Water around the roots", mode="lines"))
    fig.add_trace(go.Scatter(x=df["day"], y=df["Crop stress"], name="Crop stress", mode="lines"))
    fig.add_trace(go.Scatter(x=df["day"], y=df["Water reserve"], name="Water reserve", mode="lines"))
    fig.add_trace(go.Scatter(x=df["day"], y=df["Risk to the harvest"], name="Risk to the harvest", mode="lines"))
    for e in (events or []):
        try:
            d = int(e.day)
        except (AttributeError, TypeError, ValueError):
            continue
        fig.add_vline(x=d, line_dash="dot", line_color="gray", opacity=0.5)
    fig.update_layout(height=400, margin={"l": 10, "r": 10, "t": 40, "b": 10},
                      title="How the field evolves if nothing changes",
                      xaxis_title="Day", yaxis_title="Value (0-1)",
                      legend={"orientation": "h", "y": -0.22})
    return fig


def compare_fig(base, cf):
    import plotly.graph_objects as go
    b = traj_frame(base); c = traj_frame(cf)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=b["day"], y=b["Risk to the harvest"], name="Without intervention — harvest risk", mode="lines"))
    fig.add_trace(go.Scatter(x=c["day"], y=c["Risk to the harvest"], name="With simulated intervention — harvest risk", mode="lines"))
    fig.update_layout(height=380, margin={"l": 10, "r": 10, "t": 40, "b": 10},
                      title="Compare the futures (same simulator, both sides)",
                      xaxis_title="Day", yaxis_title="Value (0-1)",
                      legend={"orientation": "h", "y": -0.22})
    return fig



