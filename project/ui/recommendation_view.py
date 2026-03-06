"""
ui/recommendation_view.py — Lógica de formatação da view de recomendação.

Transforma o resultado bruto dos algoritmos de busca em grafo
em estruturas formatadas para exibição na interface.
"""

from typing import Optional


def format_path_response(
    path: list,
    cost: float,
    graph,
    algorithm: str = "astar",
    penalize: bool = False,
) -> dict:
    """
    Formata o resultado do algoritmo de busca para a API REST.

    Args:
        path: Lista de node_ids representando o caminho encontrado.
        cost: Custo total do caminho.
        graph: Instância do nx.DiGraph com os dados das músicas.
        algorithm: Nome do algoritmo usado ('astar' ou 'dijkstra').
        penalize: Se a função de custo com penalização foi usada.

    Returns:
        Dicionário pronto para serialização JSON.
    """
    def node_to_dict(node_id: str) -> dict:
        d = graph.nodes.get(node_id, {})
        return {
            "id": node_id,
            "name": d.get("name", "Desconhecido"),
            "artist": d.get("artist", "Desconhecido"),
            "genre": d.get("genre", ""),
            "energy": round(float(d.get("energy", 0)), 3),
            "danceability": round(float(d.get("danceability", 0)), 3),
            "valence": round(float(d.get("valence", 0)), 3),
            "tempo": round(float(d.get("tempo", 0)), 1),
            "acousticness": round(float(d.get("acousticness", 0)), 3),
            "instrumentalness": round(float(d.get("instrumentalness", 0)), 3),
        }

    return {
        "path": [node_to_dict(n) for n in path],
        "cost": round(cost, 6),
        "algorithm": algorithm,
        "penalize": penalize,
        "transitions": len(path) - 1,
        "algorithm_label": "A* (Weighted A*)" if algorithm == "astar" else "Dijkstra",
    }


def describe_transition(song_a: dict, song_b: dict) -> str:
    """
    Descreve a transição entre duas músicas em termos de características.

    Args:
        song_a: Dados da primeira música.
        song_b: Dados da segunda música.

    Returns:
        String descrevendo a mudança principal entre as músicas.
    """
    energy_delta = float(song_b.get("energy", 0)) - float(song_a.get("energy", 0))
    dance_delta = float(song_b.get("danceability", 0)) - float(song_a.get("danceability", 0))
    val_delta = float(song_b.get("valence", 0)) - float(song_a.get("valence", 0))

    changes = []

    if abs(energy_delta) > 0.15:
        direction = "↑" if energy_delta > 0 else "↓"
        changes.append(f"Energia {direction}")

    if abs(dance_delta) > 0.15:
        direction = "↑" if dance_delta > 0 else "↓"
        changes.append(f"Dançabilidade {direction}")

    if abs(val_delta) > 0.15:
        direction = "↑" if val_delta > 0 else "↓"
        changes.append(f"Valência {direction}")

    if not changes:
        return "Transição suave"

    return " · ".join(changes)
