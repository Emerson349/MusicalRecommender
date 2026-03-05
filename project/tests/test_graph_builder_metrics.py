# project/tests/test_graph_builder_metrics.py
import os
import pandas as pd
import pytest

from src.preprocessing.graph_builder import GraphBuilder, METRICAS_SUPORTADAS


def _csv_minimo(tmp_path):
    df = pd.DataFrame({
        "track_id": ["1", "2", "3"],
        "track_name": ["A", "B", "C"],
        "artists": ["X", "Y", "Z"],
        "track_genre": ["pop", "pop", "rock"],
        "danceability": [0.5, 0.6, 0.7],
        "energy": [0.8, 0.7, 0.6],
        "valence": [0.3, 0.4, 0.5],
        "tempo": [120, 130, 110],
        "acousticness": [0.1, 0.2, 0.3],
        "instrumentalness": [0.0, 0.0, 0.1],
    })
    fp = os.path.join(tmp_path, "songs.csv")
    df.to_csv(fp, index=False)
    return fp


def test_build_graph_metrica_invalida(tmp_path):
    csv_file = _csv_minimo(tmp_path)
    builder = GraphBuilder(csv_file)

    with pytest.raises(ValueError):
        builder.build_graph(metrica="nao_existe")


@pytest.mark.parametrize("metrica", list(METRICAS_SUPORTADAS))
def test_build_graph_metricas_suportadas_geram_grafo(tmp_path, metrica):
    csv_file = _csv_minimo(tmp_path)
    builder = GraphBuilder(csv_file)
    G = builder.build_graph(k_neighbors=2, metrica=metrica)

    assert G.number_of_nodes() == 3
    # com 3 nós e k=2, cada nó deve ter pelo menos 1 saída (em geral 2, mas pode empatar/distância)
    assert G.number_of_edges() > 0
