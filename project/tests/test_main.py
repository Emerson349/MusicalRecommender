import builtins
import networkx as nx
import pytest
from unittest.mock import patch, MagicMock

from main import (
    buscar_musicas,
    formatar_musica,
    listar_e_selecionar_musica,
    processar_busca_caminho,
    menu_principal,
    executar_interface,
    main,
)

def test_buscar_musicas_basic():
    G = nx.DiGraph()
    G.add_node(1, name="Love Song", artist="Adele")
    G.add_node(2, name="Lovely Day", artist="Bill Withers")

    result = buscar_musicas(G, "love")

    assert len(result) == 2
    assert result[0][2] >= result[1][2]


def test_buscar_musicas_empty_term():
    G = nx.DiGraph()
    G.add_node(1, name="Test", artist="X")

    assert buscar_musicas(G, "") == []


def test_formatar_musica_known():
    G = nx.DiGraph()
    G.add_node(1, name="Song", artist="Artist")

    assert formatar_musica(G, 1) == "Song — Artist"


def test_formatar_musica_unknown():
    G = nx.DiGraph()
    assert formatar_musica(G, 999) == "[ID desconhecido: 999]"


@patch("builtins.input")
def test_listar_e_selecionar_musica_select_first(mock_input):
    G = nx.DiGraph()
    G.add_node(10, name="Hello", artist="Adele")

    mock_input.side_effect = [
        "hel",
        "1"
    ]

    node = listar_e_selecionar_musica(G, "ORIGEM")
    assert node == 10


@patch("builtins.input")
def test_listar_e_selecionar_musica_cancel(mock_input):
    mock_input.side_effect = ["sair"]
    G = nx.DiGraph()
    assert listar_e_selecionar_musica(G, "ORIGEM") is None


@patch("main.dijkstra")
def test_processar_busca_caminho_ok(mock_dijkstra, capsys):
    G = nx.DiGraph()
    G.add_node(1, name="A", artist="X")
    G.add_node(2, name="B", artist="Y")

    mock_dijkstra.return_value = ([1, 2], 3.5)

    processar_busca_caminho(G, 1, 2, algoritmo='dijkstra')

    out = capsys.readouterr().out
    assert "Caminho encontrado" in out or "✔ Caminho encontrado" in out
    assert ("Distância total" in out) or ("Custo total" in out)


@patch("main.dijkstra")
def test_processar_busca_caminho_no_path(mock_dijkstra, capsys):
    mock_dijkstra.return_value = (None, 0)

    G = nx.DiGraph()
    G.add_node(1, name="A", artist="X")
    G.add_node(2, name="B", artist="Y")

    processar_busca_caminho(G, 1, 2, algoritmo='dijkstra')

    out = capsys.readouterr().out
    assert "Nenhum caminho encontrado" in out


def test_processar_busca_caminho_same_node(capsys):
    G = nx.DiGraph()
    G.add_node(1, name="A", artist="X")

    processar_busca_caminho(G, 1, 1)

    out = capsys.readouterr().out
    assert "Origem e destino são a mesma música" in out


@patch("builtins.input", return_value="1")
def test_menu_principal(mock_input):
    assert menu_principal() == "1"


@patch("builtins.input")
def test_executar_interface_exit(mock_input, capsys):
    mock_input.side_effect = ["0"]  # sai direto

    G = nx.DiGraph()
    executar_interface(G)

    out = capsys.readouterr().out
    assert "Até logo" in out


@patch("main.executar_interface")
@patch("main.GraphService")
def test_main_success(mock_service, mock_exec, capsys):
    instance = mock_service.return_value
    instance.run_full_etl.return_value = True

    G = nx.DiGraph()
    G.add_node(1)
    instance.get_graph.return_value = G

    main()

    out = capsys.readouterr().out
    assert "Grafo carregado com sucesso" in out
    mock_exec.assert_called_once()


@patch("main.GraphService")
def test_main_file_not_found(mock_service, capsys):
    instance = mock_service.return_value
    instance.run_full_etl.side_effect = FileNotFoundError("arq")

    main()

    out = capsys.readouterr().out
    assert "Arquivo não encontrado" in out
