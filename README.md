# AgriCascade 9.29

**Intervention-sensitive agricultural cascade simulator.**

AgriCascade reconstructs an agricultural system's current state, simulates how a
disturbance propagates across water, soil, crop, weather and management states,
identifies the critical transition where the future branches toward damage, and
tests the smallest intervention that prevents that cascade.

```
OBSERVE → RECONSTRUCT STATE → SIMULATE CASCADE
        → IDENTIFY CRITICAL BRANCH → INTERVENE → REPLAY COUNTERFACTUAL
```

## What this is (and is not)

It is **not** a yield predictor, a disease classifier, an irrigation
recommender, a weather app, a satellite dashboard, or an LLM chatbot. Those can
supply inputs. The product is the explicit **state-transition simulation loop**
that tests where and when an intervention changes the future trajectory.

## Scope

| Item | Value |
| --- | --- |
| MVP crop | Rice (configurable via `config/crop_rice.yaml`) |
| MVP geography | Kerala: Thrissur, Palakkad, Alappuzha, Kuttanad, Ernakulam |
| Simulation resolution | Daily |
| Default horizon | 14 days |
| Runtime cost | ₹0 — no paid API, no LLM at runtime |
| Free inputs | Copernicus Sentinel, Open-Meteo, SoilGrids, Kerala crop statistics |

## Install

```powershell
python -m pip install -r requirements.txt
```

Optional geospatial stack (only needed for raw Sentinel raster processing):

```powershell
python -m pip install -e ".[geo]"
```

## Run the simulator (no UI required)

```powershell
python scripts/run_benchmark.py
python -c "from agricascade.pipeline import analyze_agricultural_cascade; import pprint; pprint.pprint(analyze_agricultural_cascade(horizon_days=14, seed=42)['baseline'].summary())"
```

## Run the dashboard

```powershell
python -m streamlit run app/streamlit_app.py
```

Four pages: **Field State → Cascade → Branch Point → Counterfactual**.

## Tests

```powershell
pytest
```

## Repository layout

```
config/       model, crop, scenario registry, objective weights
agricascade/  schemas, data, features, state, physics, forecasting,
              cascade, intervention, evaluation, utils
app/          Streamlit entrypoint, pages, components
scenarios/    normal / rainfall_deficit / heatwave / irrigation_failure /
              heavy_rain / compound
scripts/      download, preprocess, features, train, scenarios, benchmark
tests/        data, water balance, state, cascade, branches, intervention, e2e
reports/      benchmark.csv, historical_replay.csv, figures
```

## Data provenance contract

Every record carries `source_type ∈ {observed, derived, synthetic}` (and
observations carry a `Provenance` object). Real satellite/weather/soil inputs
and synthetic field-operational state remain distinguishable everywhere. The
simulation never claims that satellite sensors directly measure subsurface
variables — depth layers are **model states** constrained by public data.

## Scientific status

All numeric parameters (infiltration fractions, stage sensitivities, thresholds,
objective weights) are documented prototype assumptions in `config/`, not
calibrated operational constants. See `docs/` in the spec and the in-code
`Assumption` notes. Established techniques (bucket water balance, branch
sensitivity, bootstrap uncertainty) are used as established techniques, not
claimed as novel.