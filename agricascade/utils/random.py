"""Deterministic RNG helpers.

AGENTS.md rule 8: every stochastic experiment requires an explicit seed.
These helpers make it hard to accidentally run an unseeded experiment.
"""

from __future__ import annotations

import numpy as np


def require_seed(seed: int | None) -> int:
    """Validate that an explicit seed was provided."""
    if seed is None:
        raise ValueError(
            "An explicit random seed is required for every stochastic "
            "experiment (AGENTS.md rule 8)."
        )
    if not isinstance(seed, (int, np.integer)):
        raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
    return int(seed)


def make_rng(seed: int | None) -> np.random.Generator:
    """Create a NumPy Generator from an explicit seed."""
    return np.random.default_rng(require_seed(seed))


def child_seed(seed: int, *keys: object) -> int:
    """Derive a reproducible child seed from a base seed and context keys.

    Uses a stable hash so the same (seed, keys) always maps to the same child
    seed across processes (unlike Python's randomised ``hash``).
    """
    import hashlib

    payload = "|".join(str(k) for k in keys).encode("utf-8")
    digest = hashlib.sha256(str(require_seed(seed)).encode("utf-8") + b"::" + payload)
    return int.from_bytes(digest.digest()[:4], "big")