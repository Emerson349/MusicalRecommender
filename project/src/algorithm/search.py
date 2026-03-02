import heapq
import math
import networkx as nx
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Configurações de penalização de transições longas
# ---------------------------------------------------------------------------
PENALIDADE_LIMIAR = 0.3     # Distância acima desse valor recebe penalidade extra
PENALIDADE_PESO = 2.0       # Multiplicador aplicado ao excesso acima do limiar
PENALIDADE_TRANSICAO = 0.05 # Custo fixo adicionado por cada transição

# ---------------------------------------------------------------------------
# Pesos das features na heurística do A*
# Devem espelhar os FEATURE_WEIGHTS do graph_builder para que a heurística
# seja consistente com os pesos usados na construção das arestas.
# ---------------------------------------------------------------------------
_HEURISTICA_WEIGHTS = {
    'energy':            1.5,
    'valence':           1.5,
    'danceability':      1.2,
    'tempo':             0.8,
    'acousticness':      1.0,
    'instrumentalness':  0.6,
}

# Penalidade aplicada à heurística quando os dois nós são de gêneros
# diferentes — mantém consistência com GENRE_EDGE_PENALTY do graph_builder.
_HEURISTICA_GENRE_PENALTY = 1.3


# ---------------------------------------------------------------------------
# Função de custo de aresta
# ---------------------------------------------------------------------------

def _custo_aresta(distancia: float, penalizar: bool = False) -> float:
    """
    Calcula o custo de travessia de uma aresta.

    Quando ``penalizar=True``, aplica:
      - Custo fixo por transição (``PENALIDADE_TRANSICAO``), desincentivando
        caminhos com muitas etapas.
      - Penalidade proporcional ao excesso de distância acima de
        ``PENALIDADE_LIMIAR``, ponderado por ``PENALIDADE_PESO``.

    Args:
        distancia: Peso bruto da aresta.
        penalizar: Ativa a função de custo com penalização.

    Returns:
        Custo efetivo da aresta.
    """
    if not penalizar:
        return distancia

    custo = distancia + PENALIDADE_TRANSICAO

    if distancia > PENALIDADE_LIMIAR:
        excesso = distancia - PENALIDADE_LIMIAR
        custo += excesso * PENALIDADE_PESO

    return custo


# ---------------------------------------------------------------------------
# Heurística do A*
# ---------------------------------------------------------------------------

def _heuristica(graph, node, target) -> float:
    """
    Heurística admissível para o A*: distância euclidiana ponderada entre
    ``node`` e ``target`` no espaço de features musicais.

    Os pesos espelham ``FEATURE_WEIGHTS`` do ``GraphBuilder``, e uma
    penalidade de gênero é somada quando os nós pertencem a gêneros
    diferentes — garantindo consistência com a construção do grafo.

    A heurística é admissível porque nunca superestima o custo real:
    ela mede a distância direta no mesmo espaço em que as arestas foram
    construídas, mas sem aplicar penalidades adicionais de rota.

    Args:
        graph: Grafo NetworkX com atributos nos nós.
        node: Nó atual.
        target: Nó destino.

    Returns:
        Estimativa do custo restante (>= 0). Retorna 0 se os atributos
        não estiverem disponíveis (degrada para Dijkstra).
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

    # Penalidade de gênero na heurística (multiplicativa, assim como no grafo)
    genre_node = node_data.get('genre', '')
    genre_target = target_data.get('genre', '')
    if genre_node and genre_target and genre_node != genre_target:
        h *= _HEURISTICA_GENRE_PENALTY

    return h


# ---------------------------------------------------------------------------
# Dijkstra
# ---------------------------------------------------------------------------

def dijkstra(graph, source, target, penalizar: bool = False):
    """
    Busca o menor caminho entre ``source`` e ``target`` usando Dijkstra.

    Args:
        graph: Grafo NetworkX (DiGraph ou Graph) com atributo ``weight``
               nas arestas.
        source: Nó de origem.
        target: Nó de destino.
        penalizar: Se True, usa a função de custo com penalização de grandes
                   transições (ver :func:`_custo_aresta`).

    Returns:
        Tupla ``(path, custo_total)``. Se não houver caminho, retorna
        ``(None, inf)``.
    """
    dist = {node: float('inf') for node in graph.nodes}
    prev = {node: None for node in graph.nodes}
    dist[source] = 0.0
    pq = [(0.0, source)]

    while pq:
        current_dist, current_node = heapq.heappop(pq)

        if current_dist > dist[current_node]:
            continue

        if current_node == target:
            break

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
# A* (A-estrela)
# ---------------------------------------------------------------------------

def a_star(graph, source, target, penalizar: bool = False):
    """
    Busca o menor caminho entre ``source`` e ``target`` usando A*.

    Usa como heurística a distância euclidiana ponderada no espaço de
    features musicais, consistente com os pesos e penalidades usados no
    ``GraphBuilder`` — garantindo admissibilidade e, portanto, otimalidade.

    Args:
        graph: Grafo NetworkX (DiGraph ou Graph) com atributo ``weight``
               nas arestas e atributos de features nos nós.
        source: Nó de origem.
        target: Nó de destino.
        penalizar: Se True, usa a função de custo com penalização de grandes
                   transições (ver :func:`_custo_aresta`).

    Returns:
        Tupla ``(path, custo_total)``. Se não houver caminho, retorna
        ``(None, inf)``.
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
            graph, pos,
            edgelist=caminho_arestas,
            width=4,
            edge_color="red"
        )
        nx.draw_networkx_nodes(
            graph, pos,
            nodelist=path,
            node_size=700,
            node_color="red"
        )

    edge_labels = nx.get_edge_attributes(graph, "weight")
    nx.draw_networkx_edge_labels(
        graph, pos,
        edge_labels=edge_labels,
        font_color="black",
        font_size=10,
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
    print("Dijkstra (sem penalização)")
    path_d, cost_d = dijkstra(G, source, target)
    print(f"  Caminho : {path_d}")
    print(f"  Custo   : {cost_d}")

    print("\nDijkstra (com penalização)")
    path_dp, cost_dp = dijkstra(G, source, target, penalizar=True)
    print(f"  Caminho : {path_dp}")
    print(f"  Custo   : {cost_dp:.4f}")

    print("\nA* (sem penalização)")
    path_a, cost_a = a_star(G, source, target)
    print(f"  Caminho : {path_a}")
    print(f"  Custo   : {cost_a}")

    print("\nA* (com penalização)")
    path_ap, cost_ap = a_star(G, source, target, penalizar=True)
    print(f"  Caminho : {path_ap}")
    print(f"  Custo   : {cost_ap:.4f}")
    print("=" * 50)

    mostrar_grafo(G, path_a)


if __name__ == "__main__":
    main()