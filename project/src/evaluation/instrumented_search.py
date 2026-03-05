# src/evaluation/instrumented_search.py
# Instrumented versions of Dijkstra and A* to collect metrics.
from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

import networkx as nx

from src.algorithm import search as search_mod


@dataclass
class SearchStats:
    algorithm: str
    penalizar: bool
    source: Any
    target: Any
    found: bool
    time_ms: float
    expanded_nodes: int
    relaxations: int
    path_length: int
    path_cost: float


def dijkstra_instrumented(
    graph: nx.Graph,
    source: Any,
    target: Any,
    *,
    penalizar: bool = False,
) -> Tuple[Optional[List[Any]], float, int, int]:
    dist = {node: float("inf") for node in graph.nodes}
    prev = {node: None for node in graph.nodes}
    dist[source] = 0.0

    pq: List[Tuple[float, Any]] = [(0.0, source)]
    expanded_nodes = 0
    relaxations = 0

    while pq:
        current_dist, current_node = heapq.heappop(pq)

        if current_dist > dist[current_node]:
            continue

        expanded_nodes += 1

        if current_node == target:
            break

        for neighbor, data in graph[current_node].items():
            relaxations += 1
            weight = data.get("weight", 1.0)
            custo = search_mod._custo_aresta(weight, penalizar)  # type: ignore[attr-defined]
            new_dist = current_dist + custo

            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = current_node
                heapq.heappush(pq, (new_dist, neighbor))

    if dist.get(target, float("inf")) == float("inf"):
        return None, float("inf"), expanded_nodes, relaxations

    path: List[Any] = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path, dist[target], expanded_nodes, relaxations


def a_star_instrumented(
    graph: nx.Graph,
    source: Any,
    target: Any,
    *,
    penalizar: bool = False,
) -> Tuple[Optional[List[Any]], float, int, int]:
    g = {node: float("inf") for node in graph.nodes}
    g[source] = 0.0
    prev = {node: None for node in graph.nodes}

    h_source = search_mod._heuristica(graph, source, target)  # type: ignore[attr-defined]
    pq: List[Tuple[float, float, Any]] = [(h_source, 0.0, source)]

    visited = set()
    expanded_nodes = 0
    relaxations = 0

    while pq:
        f_current, g_current, current_node = heapq.heappop(pq)

        if current_node in visited:
            continue
        visited.add(current_node)

        expanded_nodes += 1

        if current_node == target:
            break

        for neighbor, data in graph[current_node].items():
            if neighbor in visited:
                continue

            relaxations += 1
            weight = data.get("weight", 1.0)
            custo = search_mod._custo_aresta(weight, penalizar)  # type: ignore[attr-defined]
            g_new = g_current + custo

            if g_new < g[neighbor]:
                g[neighbor] = g_new
                prev[neighbor] = current_node
                h = search_mod._heuristica(graph, neighbor, target)  # type: ignore[attr-defined]
                heapq.heappush(pq, (g_new + h, g_new, neighbor))

    if g.get(target, float("inf")) == float("inf"):
        return None, float("inf"), expanded_nodes, relaxations

    path: List[Any] = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path, g[target], expanded_nodes, relaxations