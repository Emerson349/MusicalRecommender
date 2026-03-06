"""
main_gui.py — Ponto de entrada da interface gráfica do Musical Recommender.

Executa o servidor Flask com a interface web estilo Spotify e abre
automaticamente no navegador padrão.

Uso:
    python main_gui.py
    python main_gui.py --port 8080 --no-browser
"""

import argparse
import os
import sys

# Garante que o diretório do projeto está no path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def main():
    parser = argparse.ArgumentParser(
        description="Musical Recommender — Interface Gráfica"
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Host do servidor (padrão: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=5000,
        help="Porta do servidor (padrão: 5000)"
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Não abrir o navegador automaticamente"
    )
    args = parser.parse_args()

    # Importa e inicia o servidor Flask com a UI
    from ui.app import run_server  # noqa
    run_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser
    )


if __name__ == "__main__":
    main()
