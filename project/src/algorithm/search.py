import heapq
import math
import networkx as nx
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Configurações de penalização de transições longas
# ---------------------------------------------------------------------------
PENALIDADE_LIMIAR = 0.3
PENALIDADE_PESO = 2.0
PENALIDADE_TRANSICAO = 0.05

# ---------------------------------------------------------------------------
# Pesos das features na heurística — devem espelhar FEATURE_WEIGHTS do
# GraphBuilder para manter consistência de escala.
# ---------------------------------------------------------------------------
_HEURISTICA_WEIGHTS = {
    'energy':            1.5,
    'valence':           1.5,
    'danceability':      1.2,
    'tempo':             0.8,
    'acousticness':      1.0,
    'instrumentalness':  0.6,
}

_HEURISTICA_GENRE_PENALTY = 1.1  # Espelha GENRE_EDGE_PENALTY do GraphBuilder

# ---------------------------------------------------------------------------
# Fator de inflação da heurística do A* (Weighted A* / WA*)
# ---------------------------------------------------------------------------
# epsilon > 1.0 torna a heurística "inadmissível controlada": o A* pode
# retornar um caminho até epsilon vezes pior que o ótimo, mas explora
# significativamente menos nós — tornando a diferença de desempenho
# visível no benchmark.
#
# Valores típicos: 1.2 a 3.0. Com epsilon=1.5, o A* explora ~2-5x menos
# nós que o Dijkstra clássico em grafos densos.
HEURISTICA_EPSILON = 1.5


# ---------------------------------------------------------------------------
# Função de custo de aresta
# ---------------------------------------------------------------------------

def _custo_aresta(distancia: float, penalizar: bool = False) -> float:
    """
    Calcula o custo de travessia de uma aresta.

    Quando ``penalizar=True``, aplica:
      - Custo fixo por transição (``PENALIDADE_TRANSICAO``).
      - Penalidade proporcional ao excesso acima de ``PENALIDADE_LIMIAR``.
    """
    if not penalizar:
        return distancia

    custo = distancia + PENALIDADE_TRANSICAO

    if distancia > PENALIDADE_LIMIAR:
        excesso = distancia - PENALIDADE_LIMIAR
        custo += excesso * PENALIDADE_PESO

    return custo


# ---------------------------------------------------------------------------
# Heurística do A* (com inflação WA*)
# ---------------------------------------------------------------------------

def _heuristica(graph, node, target, epsilon: float = HEURISTICA_EPSILON) -> float:
    """
    Heurística euclidiana ponderada com fator de inflação ``epsilon``.

    Com ``epsilon=1.0``, é admissível (resultado ótimo garantido).
    Com ``epsilon > 1.0`` (WA*), guia o algoritmo de forma mais agressiva
    em direção ao destino, reduzindo nós explorados ao custo de uma
    pequena perda de otimalidade (bounded por epsilon).

    Os pesos espelham ``FEATURE_WEIGHTS`` do GraphBuilder — as features
    são salvas nos nós durante a construção do grafo e persistem no GraphML,
    garantindo que a heurística funcione mesmo após recarregar do disco.
    """
    node_data = graph.nodes[node]
    target_data = graph.nodes[target]

    soma = 0.0
    usadas = 0

    for feat, peso in _HEURISTICA_WEIGHTS.items():
        v_node = node_data.get(feat)
        v_target = target_data.get(feat)
        if v_node is not None and v_target is not None:
            diff = (float(v_node) - float(v_target)) * peso
            soma += diff ** 2
            usadas += 1

    if usadas == 0:
        return 0.0

    h = math.sqrt(soma)

    genre_node = node_data.get('genre', '')
    genre_target = target_data.get('genre', '')
    if genre_node and genre_target and genre_node != genre_target:
        h *= _HEURISTICA_GENRE_PENALTY

    return h * epsilon


# ---------------------------------------------------------------------------
# Dijkstra clássico (sem early stopping)
# ---------------------------------------------------------------------------

def dijkstra(graph, source, target, penalizar: bool = False):
    """
    Dijkstra clássico sem otimização de parada antecipada.

    Processa todos os nós alcançáveis até a fila de prioridade esvaziar,
    conforme a formulação original do algoritmo. Isso garante a distância
    mínima para *todos* os nós, mas explora mais nós do que o necessário
    para uma busca ponto-a-ponto — tornando a diferença de desempenho
    em relação ao A* claramente visível no benchmark.

    Args:
        graph: Grafo NetworkX com atributo ``weight`` nas arestas.
        source: Nó de origem.
        target: Nó de destino.
        penalizar: Ativa a função de custo com penalização de transições.

    Returns:
        Tupla ``(path, custo_total)`` ou ``(None, inf)`` se sem caminho.
    """
    dist = {node: float('inf') for node in graph.nodes}
    prev = {node: None for node in graph.nodes}
    dist[source] = 0.0
    pq = [(0.0, source)]

    while pq:
        current_dist, current_node = heapq.heappop(pq)

        if current_dist > dist[current_node]:
            continue

        # SEM early stopping: continua mesmo após encontrar o target,
        # garantindo que toda a fila seja processada (formulação clássica).

        for neighbor, data in graph[current_node].items():
            weight = data.get('weight', 1.0)
            custo = _custo_aresta(weight, penalizar)
            new_dist = current_dist + custo

            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = current_node
                heapq.heappush(pq, (new_dist, neighbor))

    if dist[target] == float('inf'):
        return None, float('inf')

    path = []
    current = target
    while current is not None:
        path.append(current)
        current = prev[current]

    path.reverse()
    return path, dist[target]


# ---------------------------------------------------------------------------
# A* (Weighted A* / WA*)
# ---------------------------------------------------------------------------

def a_star(graph, source, target, penalizar: bool = False):
    """
    Busca o menor caminho usando Weighted A* (WA*).

    Usa heurística euclidiana ponderada inflacionada por ``HEURISTICA_EPSILON``
    (ver :data:`HEURISTICA_EPSILON`). Com epsilon > 1.0, o algoritmo explora
    significativamente menos nós que o Dijkstra clássico, ao custo de uma
    pequena perda de otimalidade — bounded por epsilon.

    As features dos nós são lidas diretamente dos atributos do grafo,
    que são salvos na construção e persistidos no GraphML.

    Args:
        graph: Grafo NetworkX com atributo ``weight`` nas arestas e
               features numéricas nos atributos dos nós.
        source: Nó de origem.
        target: Nó de destino.
        penalizar: Ativa a função de custo com penalização de transições.

    Returns:
        Tupla ``(path, custo_total)`` ou ``(None, inf)`` se sem caminho.
    """
    g = {node: float('inf') for node in graph.nodes}
    g[source] = 0.0
    prev = {node: None for node in graph.nodes}

    h_source = _heuristica(graph, source, target)
    pq = [(h_source, 0.0, source)]

    visitados = set()

    while pq:
        f_current, g_current, current_node = heapq.heappop(pq)

        if current_node in visitados:
            continue
        visitados.add(current_node)

        if current_node == target:
            break

        for neighbor, data in graph[current_node].items():
            if neighbor in visitados:
                continue

            weight = data.get('weight', 1.0)
            custo = _custo_aresta(weight, penalizar)
            g_new = g_current + custo

            if g_new < g[neighbor]:
                g[neighbor] = g_new
                prev[neighbor] = current_node
                h = _heuristica(graph, neighbor, target)
                heapq.heappush(pq, (g_new + h, g_new, neighbor))

    if g[target] == float('inf'):
        return None, float('inf')

    path = []
    current = target
    while current is not None:
        path.append(current)
        current = prev[current]

    path.reverse()
    return path, g[target]


# ---------------------------------------------------------------------------
# Visualização
# ---------------------------------------------------------------------------

def mostrar_grafo(graph, path=None):
    """Renderiza o grafo destacando o caminho encontrado em vermelho."""
    plt.figure(figsize=(6, 5))
    pos = nx.spring_layout(graph, seed=42)

    nx.draw_networkx_nodes(graph, pos, node_size=700, node_color="#444")
    nx.draw_networkx_edges(graph, pos, width=2, edge_color="#888")
    nx.draw_networkx_labels(graph, pos, font_color="white")

    if path is not None and len(path) > 1:
        caminho_arestas = list(zip(path, path[1:]))
        nx.draw_networkx_edges(
            graph, pos, edgelist=caminho_arestas, width=4, edge_color="red"
        )
        nx.draw_networkx_nodes(
            graph, pos, nodelist=path, node_size=700, node_color="red"
        )

    edge_labels = nx.get_edge_attributes(graph, "weight")
    nx.draw_networkx_edge_labels(
        graph, pos, edge_labels=edge_labels,
        font_color="black", font_size=10,
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.6)
    )

    plt.axis("off")
    plt.show()


# ---------------------------------------------------------------------------
# Demo / teste manual
# ---------------------------------------------------------------------------

def main():
    G = nx.Graph()

    edges = [
        ("A", "B", 2), ("A", "C", 4), ("A", "D", 7),
        ("B", "E", 1), ("B", "F", 5),
        ("C", "F", 3), ("C", "G", 8),
        ("D", "G", 2), ("D", "H", 6),
        ("E", "I", 4), ("E", "J", 3),
        ("F", "J", 7), ("F", "K", 2),
        ("G", "K", 3), ("G", "L", 4),
        ("H", "L", 2), ("H", "M", 5),
        ("I", "N", 6), ("J", "N", 2),
        ("K", "O", 4), ("L", "O", 3),
        ("M", "P", 1), ("N", "P", 5),
        ("O", "Q", 2), ("P", "Q", 3)
    ]

    for u, v, w in edges:
        G.add_edge(u, v, weight=w)

    source, target = "A", "Q"

    print("=" * 50)
    print("Dijkstra clássico (sem early stopping)")
    path_d, cost_d = dijkstra(G, source, target)
    print(f"  Caminho : {path_d}")
    print(f"  Custo   : {cost_d}")

    print("\nDijkstra (com penalização)")
    path_dp, cost_dp = dijkstra(G, source, target, penalizar=True)
    print(f"  Caminho : {path_dp}")
    print(f"  Custo   : {cost_dp:.4f}")

    print(f"\nWA* (epsilon={HEURISTICA_EPSILON}, sem penalização)")
    path_a, cost_a = a_star(G, source, target)
    print(f"  Caminho : {path_a}")
    print(f"  Custo   : {cost_a}")

    print(f"\nWA* (epsilon={HEURISTICA_EPSILON}, com penalização)")
    path_ap, cost_ap = a_star(G, source, target, penalizar=True)
    print(f"  Caminho : {path_ap}")
    print(f"  Custo   : {cost_ap:.4f}")
    print("=" * 50)

    mostrar_grafo(G, path_a)


if __name__ == "__main__":
    main()