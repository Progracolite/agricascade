"""Cascade graph construction (NetworkX)."""

from __future__ import annotations

from typing import Any

import networkx as nx

from agricascade.cascade.transitions import (
    EDGE_SPECS,
    NODES,
    make_edge,
)
from agricascade.schemas.transition import CascadeEdge


def build_cascade_graph(config: dict[str, Any] | None = None) -> nx.DiGraph:
    """Build the directed cascade dependency graph.

    Node attributes carry a human-readable label; edge attributes mirror the
    :class:`CascadeEdge` schema plus the activation rule.
    """
    graph = nx.DiGraph()
    for node in NODES:
        graph.add_node(node, label=node.replace("_", " ").title())

    for spec in EDGE_SPECS:
        edge = make_edge(spec)
        graph.add_edge(
            spec["source"],
            spec["target"],
            label=spec["label"],
            relationship=edge.relationship,
            sensitivity=edge.sensitivity,
            lag_days=edge.lag_days,
            threshold=edge.threshold,
            uncertainty=edge.uncertainty,
            activation_probability=edge.activation_probability,
            activation=dict(spec["activation"]),
        )
    return graph


def graph_edges(graph: nx.DiGraph) -> list[CascadeEdge]:
    """Return the graph edges as schema objects."""
    out: list[CascadeEdge] = []
    for source, target, data in graph.edges(data=True):
        out.append(
            CascadeEdge(
                source=source,
                target=target,
                relationship=data["relationship"],
                sensitivity=data["sensitivity"],
                lag_days=data["lag_days"],
                threshold=data["threshold"],
                uncertainty=data["uncertainty"],
                activation_probability=data["activation_probability"],
            )
        )
    return out


def graph_summary(graph: nx.DiGraph) -> dict[str, Any]:
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "is_dag": nx.is_directed_acyclic_graph(graph),
        "topological_order": list(nx.topological_sort(graph))
        if nx.is_directed_acyclic_graph(graph)
        else [],
    }


def to_plotly_elements(graph: nx.DiGraph) -> dict[str, list[dict[str, Any]]]:
    """Produce node/edge element lists for Plotly rendering in the UI."""
    import math

    # Layered layout by topological position for a readable graph.
    order = list(nx.topological_sort(graph))
    layer: dict[str, int] = {}
    for node in order:
        preds = list(graph.predecessors(node))
        layer[node] = 0 if not preds else max(layer[p] for p in preds) + 1

    by_layer: dict[int, list[str]] = {}
    for node in order:
        by_layer.setdefault(layer[node], []).append(node)

    positions: dict[str, tuple[float, float]] = {}
    for lyr, nodes in by_layer.items():
        n = len(nodes)
        for i, node in enumerate(nodes):
            x = lyr / max(1, (max(by_layer) or 1))
            y = (i + 0.5) / n if n > 1 else 0.5
            positions[node] = (x, y)

    nodes = [
        {
            "id": node,
            "label": graph.nodes[node].get("label", node),
            "x": positions[node][0],
            "y": positions[node][1],
        }
        for node in order
    ]
    edges = [
        {
            "source": s,
            "target": t,
            "label": data.get("label", ""),
            "sensitivity": data.get("sensitivity"),
            "lag_days": data.get("lag_days"),
            "threshold": data.get("threshold"),
        }
        for s, t, data in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}