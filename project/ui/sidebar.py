"""
ui/sidebar.py — Configurações e dados da sidebar.

Este módulo define as entradas de navegação e metadados usados
tanto pelo servidor Flask quanto pela SPA para montar a sidebar.
"""

# Entradas de navegação principal
NAV_ITEMS = [
    {
        "id": "home",
        "label": "Início",
        "icon": "home",
    },
    {
        "id": "search",
        "label": "Buscar Música",
        "icon": "search",
    },
    {
        "id": "recommend",
        "label": "Recomendação",
        "icon": "music",
    },
]

# Gêneros musicais exibidos como atalhos na sidebar
# Populado dinamicamente a partir dos dados do grafo
FEATURED_GENRES = [
    "pop", "rock", "hip-hop", "jazz", "electronic",
    "classical", "country", "r&b", "latin", "indie",
]
