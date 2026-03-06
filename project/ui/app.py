"""
ui/app.py — Servidor Flask que expõe a lógica do backend via API REST.
A interface gráfica é servida como SPA (Single Page Application) em HTML/CSS/JS.
"""

import os
import sys
import threading
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

# ---------------------------------------------------------------------------
# Ajuste do path para importar módulos do projeto raiz
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.services.graph_service import GraphService  # noqa: E402
from src.algorithm.search import dijkstra, a_star     # noqa: E402
from main import buscar_musicas, formatar_musica        # noqa: E402

# ---------------------------------------------------------------------------
# Inicialização do app Flask
# ---------------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app = Flask(__name__, static_folder=STATIC_DIR)

# Grafo carregado em memória (singleton)
_graph = None
_loading_error = None
_loading = True


def _load_graph():
    """Carrega o grafo em thread separada para não bloquear o servidor."""
    global _graph, _loading_error, _loading
    try:
        service = GraphService(root_dir=BASE_DIR)
        service.run_full_etl()
        _graph = service.get_graph(force_rebuild=False)
        print(f"[UI] Grafo carregado: {len(_graph.nodes)} nós, {len(_graph.edges)} arestas")
    except Exception as e:
        _loading_error = str(e)
        print(f"[UI] Erro ao carregar grafo: {e}")
    finally:
        _loading = False


# ---------------------------------------------------------------------------
# Rotas de API
# ---------------------------------------------------------------------------

@app.route("/api/status")
def api_status():
    """Retorna o status de carregamento do grafo."""
    if _loading:
        return jsonify({"status": "loading", "message": "Carregando grafo musical..."})
    if _loading_error:
        return jsonify({"status": "error", "message": _loading_error})
    return jsonify({
        "status": "ready",
        "nodes": len(_graph.nodes),
        "edges": len(_graph.edges)
    })


@app.route("/api/search")
def api_search():
    """Busca músicas pelo nome ou artista. Query param: q=<termo>"""
    if _graph is None:
        return jsonify({"error": "Grafo não carregado ainda."}), 503

    termo = request.args.get("q", "").strip()
    if not termo:
        return jsonify({"results": []})

    resultados = buscar_musicas(_graph, termo)[:30]

    return jsonify({
        "results": [
            {
                "id": node_id,
                "name": data.get("name", "Desconhecido"),
                "artist": data.get("artist", "Desconhecido"),
                "genre": data.get("genre", ""),
                "energy": round(float(data.get("energy", 0)), 3),
                "danceability": round(float(data.get("danceability", 0)), 3),
                "valence": round(float(data.get("valence", 0)), 3),
                "tempo": round(float(data.get("tempo", 0)), 1),
            }
            for node_id, data, _ in resultados
        ]
    })


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    """
    Gera a sequência recomendada entre origem e destino.
    Body JSON: { "origin": <id>, "target": <id>, "algorithm": "astar"|"dijkstra", "penalize": bool }
    """
    if _graph is None:
        return jsonify({"error": "Grafo não carregado ainda."}), 503

    body = request.get_json(force=True)
    origin_id = body.get("origin")
    target_id = body.get("target")
    algorithm = body.get("algorithm", "astar")
    penalize = bool(body.get("penalize", False))

    if not origin_id or not target_id:
        return jsonify({"error": "Parâmetros 'origin' e 'target' são obrigatórios."}), 400

    if origin_id not in _graph.nodes:
        return jsonify({"error": f"Música de origem não encontrada: {origin_id}"}), 404
    if target_id not in _graph.nodes:
        return jsonify({"error": f"Música de destino não encontrada: {target_id}"}), 404

    if origin_id == target_id:
        return jsonify({"error": "Origem e destino são a mesma música."}), 400

    try:
        if algorithm == "astar":
            path, cost = a_star(_graph, origin_id, target_id, penalizar=penalize)
        else:
            path, cost = dijkstra(_graph, origin_id, target_id, penalizar=penalize)

        if path is None:
            return jsonify({"error": "Nenhum caminho encontrado entre essas músicas."}), 404

        def node_info(nid):
            d = _graph.nodes[nid]
            return {
                "id": nid,
                "name": d.get("name", "Desconhecido"),
                "artist": d.get("artist", "Desconhecido"),
                "genre": d.get("genre", ""),
                "energy": round(float(d.get("energy", 0)), 3),
                "danceability": round(float(d.get("danceability", 0)), 3),
                "valence": round(float(d.get("valence", 0)), 3),
                "tempo": round(float(d.get("tempo", 0)), 1),
            }

        return jsonify({
            "path": [node_info(n) for n in path],
            "cost": round(cost, 6),
            "algorithm": algorithm,
            "penalize": penalize,
            "transitions": len(path) - 1,
        })

    except Exception as e:
        return jsonify({"error": f"Erro ao calcular caminho: {str(e)}"}), 500


@app.route("/api/songs/all")
def api_songs_all():
    """Retorna lista completa de músicas (paginada). Query params: page, per_page."""
    if _graph is None:
        return jsonify({"error": "Grafo não carregado ainda."}), 503

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    start = (page - 1) * per_page
    end = start + per_page

    all_nodes = list(_graph.nodes(data=True))
    total = len(all_nodes)
    page_nodes = all_nodes[start:end]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "songs": [
            {
                "id": nid,
                "name": d.get("name", "Desconhecido"),
                "artist": d.get("artist", "Desconhecido"),
                "genre": d.get("genre", ""),
                "tempo": round(float(d.get("tempo", 0)), 1),
                "energy": round(float(d.get("energy", 0)), 3),
            }
            for nid, d in page_nodes
        ]
    })


# ---------------------------------------------------------------------------
# Servir o frontend (SPA)
# ---------------------------------------------------------------------------

@app.route("/")
def serve_index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run_server(host="127.0.0.1", port=5000, open_browser=True):
    """Inicia o servidor Flask com carregamento do grafo em background."""
    # Carrega o grafo em thread separada
    loader = threading.Thread(target=_load_graph, daemon=True)
    loader.start()

    if open_browser:
        def _open():
            import time
            time.sleep(1.2)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=_open, daemon=True).start()

    print(f"\n🎵  Musical Recommender UI")
    print(f"    Acesse: http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, use_reloader=False)
