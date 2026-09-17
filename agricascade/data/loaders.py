"""Observation loaders with graceful offline fallback."""
from __future__ import annotations
from datetime import datetime, timedelta
from agricascade.schemas.observation import Observation, Provenance
from agricascade.utils.random import make_rng

def _prov(source: str, step: str, kind: str) -> Provenance:
    return Provenance(source=source, processing_step=step, observed_or_estimated=kind)

def demo_observations(seed: int = 42, region: str = "thrissur",
        start: datetime | None = None, days: int = 14) -> list[Observation]:
    """Bundled demonstration observations (explicitly synthetic)."""
    start = start or datetime(2026, 6, 1)
    rng = make_rng(seed)
    obs: list[Observation] = []
    for d in range(days):
        ts = start + timedelta(days=d)
        vals = {"temperature": float(rng.normal(29.0, 1.0)),
            "humidity": float(max(40, min(100, rng.normal(78, 5)))),
            "rainfall": float(max(0.0, rng.normal(6.0, 4.0))),
            "evapotranspiration": float(max(0.5, rng.normal(4.2, 0.8))),
            "ndvi": float(max(0.1, min(0.95, rng.normal(0.68, 0.05)))),
            "ndmi": float(max(-0.2, min(0.5, rng.normal(0.18, 0.05)))),
            "s1_backscatter_vv": float(rng.normal(-13.5, 1.2)),
            "surface_moisture_proxy": float(max(0.05, min(0.45, rng.normal(0.30, 0.03))))}
        for var, v in vals.items():
            obs.append(Observation(variable=var, value=v, timestamp=ts,
                provenance=_prov("agricascade.demo_bundle", "demo_observations", "synthetic"),
                uncertainty=0.05, region=region))
    return obs

def fetch_open_meteo(lat: float, lon: float, start: str, end: str,
        timeout: int = 8) -> list[Observation]:
    import requests
    url = ("https://archive-api.open-meteo.com/v1/archive?latitude=%s&longitude=%s"
        "&start_date=%s&end_date=%s&daily=temperature_2m_mean,relative_humidity_2m_mean,"
        "precipitation_sum,et0_fao_evapotranspiration&timezone=Asia%%2FKolkata" % (lat, lon, start, end))
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    daily = r.json().get("daily", {})
    times = daily.get("time", [])
    out: list[Observation] = []
    for i, t in enumerate(times):
        ts = datetime.fromisoformat(t)
        mp = {"temperature": daily.get("temperature_2m_mean", [None])[i],
            "humidity": daily.get("relative_humidity_2m_mean", [None])[i],
            "rainfall": daily.get("precipitation_sum", [None])[i],
            "evapotranspiration": daily.get("et0_fao_evapotranspiration", [None])[i]}
        for var, v in mp.items():
            if v is None:
                continue
            out.append(Observation(variable=var, value=float(v), timestamp=ts,
                provenance=_prov("open-meteo.archive", "fetch_open_meteo", "observed"),
                region=f"{lat},{lon}"))
    return out

def fetch_soilgrids(lat: float, lon: float, timeout: int = 8) -> dict[str, float]:
    import requests
    url = ("https://rest.isric.org/soilgrids/v2.0/properties/query?lat=%s&lon=%s"
        "&property=sand&property=clay&depth=0-5cm&value=mean" % (lat, lon))
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    layers = {l["name"]: l for l in r.json().get("properties", {}).get("layers", [])}
    def mean(name: str) -> float | None:
        try:
            return float(layers[name]["depths"][0]["values"]["mean"]) / 10.0
        except Exception:
            return None
    sand = mean("sand"); clay = mean("clay")
    if sand is None or clay is None:
        raise ValueError("SoilGrids response missing sand/clay")
    from agricascade.features.soil_features import properties_from_soilgrids
    props = properties_from_soilgrids(sand / 100.0 if sand > 1 else sand,
        clay / 100.0 if clay > 1 else clay)
    props["source_type"] = "observed"
    return props

def soil_properties_with_fallback(lat: float, lon: float,
        timeout: int = 5) -> tuple[dict[str, float], str]:
    try:
        return fetch_soilgrids(lat, lon, timeout), "observed"
    except Exception:
        from agricascade.features.soil_features import default_soil_properties
        props = default_soil_properties()
        props["source_type"] = "synthetic"
        return props, "synthetic"

def observations_with_fallback(region: str = "thrissur", seed: int = 42,
        lat: float | None = None, lon: float | None = None) -> tuple[list[Observation], dict[str, str]]:
    import os as _os
    report: dict[str, str] = {}
    if lat is not None and lon is not None and not _os.environ.get("AGRICASCADE_OFFLINE"):
        try:
            end = datetime.now().date()
            start = end - timedelta(days=14)
            obs = fetch_open_meteo(lat, lon, start.isoformat(), end.isoformat())
            if obs:
                report["weather"] = "observed:open-meteo.archive"
                return obs + [o for o in demo_observations(seed, region)
                    if o.variable in ("ndvi", "ndmi", "s1_backscatter_vv", "surface_moisture_proxy")], report
        except Exception as e:
            report["weather_error"] = "%s: %s" % (type(e).__name__, e)
    report["weather"] = "synthetic:agricascade.demo_bundle"
    return demo_observations(seed, region), report

def kerala_statistics() -> dict:
    return {"source": "synthetic:kerala_agri_statistics_placeholder",
        "source_type": "synthetic",
        "note": "Placeholder district rice area/yield for demo context only.",
        "districts": {"thrissur": {"rice_area_ha": 28000, "yield_t_ha": 3.1},
            "palakkad": {"rice_area_ha": 83000, "yield_t_ha": 3.4},
            "alappuzha": {"rice_area_ha": 38000, "yield_t_ha": 3.0}}}

