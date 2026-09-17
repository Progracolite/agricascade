"""I/O helpers: config discovery and YAML/JSON read-write.

Config lookup is centralised so every module resolves the same canonical files
under ``config/`` and ``scenarios/``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    """Return the repository root (the directory that contains ``config``)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config").is_dir() and (parent / "agricascade").is_dir():
            return parent
    # Fallback: three levels up from agricascade/utils/io.py
    return here.parents[2]


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_absolute():
        path = project_root() / path
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        raise ValueError(f"Config file is empty: {path}")
    return data


def save_yaml(data: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    if not path.is_absolute():
        path = project_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)
    return path


def load_json(path: str | Path) -> Any:
    path = Path(path)
    if not path.is_absolute():
        path = project_root() / path
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(data: Any, path: str | Path, indent: int = 2) -> Path:
    path = Path(path)
    if not path.is_absolute():
        path = project_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, default=str)
    return path


@lru_cache(maxsize=None)
def load_config(
    name: str = "model.yaml",
    config_dir: str = "config",
) -> dict[str, Any]:
    """Load a canonical config file by name (cached)."""
    return load_yaml(project_root() / config_dir / name)


def load_model_config() -> dict[str, Any]:
    return load_config("model.yaml")


def load_crop_config() -> dict[str, Any]:
    return load_config("crop_rice.yaml")


def load_objective_config() -> dict[str, Any]:
    return load_config("objectives.yaml")


def load_scenario_registry() -> dict[str, Any]:
    return load_config("scenarios.yaml")


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = project_root() / p
    p.mkdir(parents=True, exist_ok=True)
    return p