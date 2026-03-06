# project/tests/test_a_star.py
import math
import runpy
import pytest
import networkx as nx

from src.algorithm import search as search_mod


def _build_feature_graph():
    """
    Grafo pequeno com atributos de features nos nós, para testar A*.
    """
    G = nx.Graph()

    # Nós com features
    G.add_node("A", energy=0.1, valence=0.1, danceability=0.1, tempo=100, acousticness=0.1, instrumentalness=0.0, genre="pop")
    G.add_node("B", energy=0.2, valence=0.1, danceability=0.2, tempo=105, acousticness=0.1, instrumentalness=0.0, genre="pop")
    G.add_node("C", energy=0.9, valence=0.9, danceability=0.9, tempo=160, acousticness=0.9, instrumentalness=0.5, genre="metal")
    G.add_node("D", energy=0.25, valence=0.15, danceability=0.25, tempo=110, acousticness=0.1, instrumentalness=0.0, genre="pop")

    # A-B-D é barato, A-C-D é caro
    G.add_edge("A", "B", weight=0.10)
    G.add_edge("B", "D", weight=0.10)
    G.add_edge("A", "C", weight=0.90)
    G.add_edge("C", "D", weight=0.90)

    return G


def test_custo_aresta_sem_penalizacao():
    assert search_mod._custo_aresta(0.2, penalizar=False) == 0.2


def test_custo_aresta_com_penalizacao_base():
    # sempre adiciona PENALIDADE_TRANSICAO quando penalizar=True
    w = 0.10
    got = search_mod._custo_aresta(w, penalizar=True)
    assert got == pytest.approx(w + search_mod.PENALIDADE_TRANSICAO)


def test_custo_aresta_com_penalizacao_excesso():
    # acima do limiar aplica excesso * PENALIDADE_PESO
    w = search_mod.PENALIDADE_LIMIAR + 0.10
    got = search_mod._custo_aresta(w, penalizar=True)
    expected = w + search_mod.PENALIDADE_TRANSICAO + (0.10 * search_mod.PENALIDADE_PESO)
    assert got == pytest.approx(expected)


def test_heuristica_retorna_zero_se_sem_features():
    G = nx.Graph()
    G.add_node("A")
    G.add_node("B")
    assert search_mod._heuristica(G, "A", "B") == 0.0


def test_heuristica_com_generos_diferentes_aplica_penalidade():
    G = nx.Graph()
    G.add_node("A", energy=0.1, valence=0.1, danceability=0.1, tempo=100, acousticness=0.1, instrumentalness=0.0, genre="pop")
    G.add_node("B", energy=0.2, valence=0.2, danceability=0.2, tempo=110, acousticness=0.1, instrumentalness=0.0, genre="metal")
    h1 = search_mod._heuristica(G, "A", "B")

    # mesmo nó B, mas com genre igual ao nó A => heurística deve ser menor ou igual
    G.nodes["B"]["genre"] = "pop"
    h2 = search_mod._heuristica(G, "A", "B")

    assert h1 >= h2
    # se existirem features, h2 deve ser > 0
    assert h2 > 0


def test_a_star_encontra_mesmo_caminho_que_dijkstra():
    G = _build_feature_graph()

    path_d, cost_d = search_mod.dijkstra(G, "A", "D", penalizar=False)
    path_a, cost_a = search_mod.a_star(G, "A", "D", penalizar=False)

    assert path_d == ["A", "B", "D"]
    assert path_a == path_d
    assert cost_a == pytest.approx(cost_d)


def test_a_star_sem_caminho():
    G = nx.Graph()
    G.add_node("A", energy=0.1)
    G.add_node("B", energy=0.2)
    path, cost = search_mod.a_star(G, "A", "B")
    assert path is None
    assert cost == float("inf")


def test_a_star_penalizacao_aumenta_custo():
    G = _build_feature_graph()

    _, cost_no = search_mod.a_star(G, "A", "D", penalizar=False)
    _, cost_pen = search_mod.a_star(G, "A", "D", penalizar=True)

    assert cost_pen > cost_no


def test_a_star_ignora_entrada_repetida_na_fila():
    G = nx.Graph()
    G.add_edge("A", "B", weight=5.0)
    G.add_edge("A", "C", weight=1.0)
    G.add_edge("C", "B", weight=1.0)
    G.add_edge("B", "D", weight=1.0)
    G.add_edge("C", "D", weight=100.0)

    path, cost = search_mod.a_star(G, "A", "D", penalizar=False)

    assert path == ["A", "C", "B", "D"]
    assert cost == pytest.approx(3.0)


def test_main_executa_sem_abrir_janela(monkeypatch):
    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)
    search_mod.main()


def test_bloco_main_quando_modulo_executado_como_script(monkeypatch):
    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)
    runpy.run_module("src.algorithm.search", run_name="__main__")
