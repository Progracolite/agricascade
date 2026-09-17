"""Logging helpers.

AGENTS.md rule 14: never silently swallow exceptions. Modules log failures at
``warning`` and re-raise or return explicitly marked fallbacks.
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    root = logging.getLogger("agricascade")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    if not name.startswith("agricascade"):
        name = f"agricascade.{name}"
    return logging.getLogger(name)