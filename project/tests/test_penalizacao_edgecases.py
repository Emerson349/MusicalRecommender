# project/tests/test_penalizacao_edgecases.py
import pytest
import networkx as nx
from src.algorithm.search import dijkstra, a_star


def test_penalizacao_nao_quebra_quando_weight_ausente():
    # se aresta não tiver weight, usa 1.0
    G = nx.Graph()
    G.add_node("A", energy=0.1)
    G.add_node("B", energy=0.2)
    G.add_edge("A", "B")  # sem weight

    path, cost = dijkstra(G, "A", "B", penalizar=True)
    assert path == ["A", "B"]
    assert cost > 0

    path2, cost2 = a_star(G, "A", "B", penalizar=True)
    assert path2 == ["A", "B"]
    assert cost2 > 0


def test_penalizacao_same_source_target():
    G = nx.Graph()
    G.add_node("A", energy=0.1)
    path, cost = dijkstra(G, "A", "A", penalizar=True)
    assert path == ["A"]
    assert cost == 0.0

    path2, cost2 = a_star(G, "A", "A", penalizar=True)
    assert path2 == ["A"]
    assert cost2 == 0.0
