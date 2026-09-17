"""Validation metrics: state/event/cascade (measured from runs, never invented)."""
from __future__ import annotations
from typing import Any
import numpy as np
from agricascade.cascade.simulator import CascadeTrajectory

def regression_metrics(y_true: list[float], y_pred: list[float]) -> dict[str, float]:
    t = np.array(y_true, float); p = np.array(y_pred, float)
    mae = float(np.mean(np.abs(t - p)))
    rmse = float(np.sqrt(np.mean((t - p) ** 2)))
    ss = float(np.sum((t - t.mean()) ** 2)) if len(t) > 1 else 0.0
    r2 = float(1 - np.sum((t - p) ** 2) / ss) if ss > 0 else 0.0
    return {"mae": mae, "rmse": rmse, "r2": r2, "n": float(len(t))}

def event_metrics(detected: list, true: list, tol: int = 1) -> dict[str, float]:
    """Days (int) use tolerance matching; labels (str) use exact set matching."""
    if detected and true and isinstance(detected[0], str):
        ds, ts = set(detected), set(true)
        tp = len(ds & ts); fp = len(ds - ts); fn = len(ts - ds)
        prec = tp / max(1, tp + fp); rec = tp / max(1, tp + fn)
        f1 = 2 * prec * rec / max(1e-9, prec + rec)
        return {"precision": prec, "recall": rec, "f1": f1, "tp": float(tp),
            "fp": float(fp), "fn": float(fn)}
    detected_days = list(detected); true_days = list(true)
    tp = 0; matched = set()
    for d in detected_days:
        for t in true_days:
            if abs(d - t) <= tol and t not in matched:
                tp += 1; matched.add(t); break
    fp = len(detected_days) - tp; fn = len(true_days) - tp
    prec = tp / max(1, tp + fp); rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    return {"precision": prec, "recall": rec, "f1": f1, "tp": float(tp),
        "fp": float(fp), "fn": float(fn)}

def transition_order_accuracy(detected: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    pos = 0; hits = 0
    for e in expected:
        try:
            i = detected.index(e, pos)
            hits += 1; pos = i + 1
        except ValueError:
            continue
    return hits / len(expected)

def cascade_metrics(traj: CascadeTrajectory, expected: dict[str, Any]) -> dict[str, Any]:
    det_edges = [f"{a.get('source')}->{a.get('target')}" for a in traj.activated_edges]
    det_events = [e.effect for e in traj.events]
    return {"order_accuracy": transition_order_accuracy(det_edges, expected.get("expected_transitions", [])),
        "event_f1": event_metrics(det_events, expected.get("expected_events", [])).get("f1", 0.0) if isinstance(det_events[0] if det_events else None, str) else 0.0,
        "terminal_ok": traj.terminal_state in expected.get("expected_terminal", [traj.terminal_state]),
        "n_events": len(traj.events), "cascade_depth": traj.cascade_depth(),
        "detected_edges": det_edges, "detected_events": det_events}
