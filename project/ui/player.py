"""
ui/player.py — Lógica auxiliar do player musical (lado Python).

O player principal é implementado em JavaScript na SPA (index.html).
Este módulo fornece utilitários para formatar dados de músicas
exibidos no player e calcular durações simuladas.
"""


def format_duration(tempo_bpm: float) -> str:
    """
    Gera uma duração simulada de música baseada no BPM.

    Args:
        tempo_bpm: Tempo da música em batidas por minuto.

    Returns:
        String formatada como "M:SS".
    """
    if not tempo_bpm or tempo_bpm <= 0:
        return "3:30"

    # Simula duração: músicas mais rápidas tendem a ser mais curtas
    seconds = int(180 + (tempo_bpm / 200.0) * 60)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def song_display_name(song_data: dict) -> str:
    """
    Formata o nome de exibição de uma música.

    Args:
        song_data: Dicionário com dados do nó do grafo.

    Returns:
        String "Nome — Artista".
    """
    name = song_data.get("name") or "Título desconhecido"
    artist = song_data.get("artist") or "Artista desconhecido"
    return f"{name} — {artist}"


def build_player_payload(node_id: str, graph) -> dict:
    """
    Constrói o payload JSON para o player a partir de um nó do grafo.

    Args:
        node_id: ID do nó no grafo.
        graph: Instância do nx.DiGraph.

    Returns:
        Dicionário com dados formatados para o player.
    """
    if node_id not in graph.nodes:
        return {}

    data = graph.nodes[node_id]
    tempo = float(data.get("tempo", 120))

    return {
        "id": node_id,
        "name": data.get("name", "Desconhecido"),
        "artist": data.get("artist", "Desconhecido"),
        "genre": data.get("genre", ""),
        "duration": format_duration(tempo),
        "energy": round(float(data.get("energy", 0)), 3),
        "danceability": round(float(data.get("danceability", 0)), 3),
        "valence": round(float(data.get("valence", 0)), 3),
        "tempo": round(tempo, 1),
    }
