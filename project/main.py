import os
import sys

from src.services.graph_service import GraphService
from src.algorithm.search import dijkstra, a_star

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Busca de músicas no grafo
# ---------------------------------------------------------------------------

def buscar_musicas(G, termo):
    """
    Busca músicas que contém o termo no nome ou artista.
    Retorna lista de (node_id, data, score) ordenada por relevância.
    """
    if not termo:
        return []

    termo = termo.lower()
    candidatos = []

    for node_id, data in G.nodes(data=True):
        nome = data.get("name", "").lower()
        artista = data.get("artist", "").lower()

        score = 0
        if termo == nome:
            score = 1000
        elif termo == artista:
            score = 900
        elif nome.startswith(termo):
            score = 500
        elif artista.startswith(termo):
            score = 400
        elif termo in nome:
            score = 100
        elif termo in artista:
            score = 50

        if score > 0:
            score -= len(nome) * 0.1
            candidatos.append((node_id, data, score))

    candidatos.sort(key=lambda x: x[2], reverse=True)
    return candidatos


def formatar_musica(G, node_id):
    """Retorna 'NOME — ARTISTA' dado o ID da música."""
    if node_id not in G.nodes:
        return f"[ID desconhecido: {node_id}]"

    data = G.nodes[node_id]
    nome = data.get("name") or "Nome desconhecido"
    artista = data.get("artist") or "Artista desconhecido"
    return f"{nome} — {artista}"


def listar_e_selecionar_musica(G, tipo, termo_inicial=None):
    """
    Interface interativa para buscar e selecionar uma música.

    Args:
        G: Grafo de músicas.
        tipo: ``"ORIGEM"`` ou ``"DESTINO"`` (para mensagens).
        termo_inicial: Termo de busca opcional para primeira iteração.

    Returns:
        node_id da música selecionada ou None se cancelado.
    """
    while True:
        if termo_inicial is None:
            print(f"\n🎵  Buscar música de {tipo}")
            print("    (Digite parte do nome ou artista, ou 'sair' para cancelar)")
            termo = input(" → Busca: ").strip()

            if termo.lower() in ['sair', 'cancelar', 'exit']:
                return None
        else:
            termo = termo_inicial
            termo_inicial = None

        if not termo:
            print("⚠️  Digite algo para buscar!")
            continue

        resultados = buscar_musicas(G, termo)

        if not resultados:
            print(f"❌ Nenhuma música encontrada com '{termo}'")
            print("    Tente outro termo de busca.\n")
            continue

        resultados_exibir = resultados[:20]

        print(
            f"\n📋 Encontradas {len(resultados)} música(s) "
            f"- Mostrando top {len(resultados_exibir)}:\n"
        )
        for i, (node_id, data, score) in enumerate(resultados_exibir, 1):
            print(f"  {i:2d}. {data.get('name', '??')} — {data.get('artist', '??')}")

        print(f"\n  0. Buscar novamente")
        print(f"  S. Sair/Cancelar")

        selecao = input(f"\n → Selecione o número da música de {tipo}: ").strip()

        if selecao.lower() in ['s', 'sair', 'cancelar', 'exit']:
            return None

        if selecao == '0':
            continue

        try:
            idx = int(selecao)
            if 1 <= idx <= len(resultados_exibir):
                node_id = resultados_exibir[idx - 1][0]
                print(f"\n✔ Selecionado: {formatar_musica(G, node_id)}")
                return node_id
            else:
                print(f"❌ Número inválido! Digite entre 1 e {len(resultados_exibir)}")
        except ValueError:
            print("❌ Digite um número válido!")


# ---------------------------------------------------------------------------
# Processamento e exibição do caminho
# ---------------------------------------------------------------------------

def processar_busca_caminho(G, origem, destino, algoritmo='astar', penalizar=False):
    """
    Executa o algoritmo escolhido e exibe o caminho encontrado.

    Args:
        G: Grafo de músicas.
        origem: node_id da música de origem.
        destino: node_id da música de destino.
        algoritmo: ``'dijkstra'`` ou ``'astar'``.
        penalizar: Se True, usa função de custo com penalização.
    """
    algo_label = "A*" if algoritmo == 'astar' else "Dijkstra"
    pen_label = " + penalização" if penalizar else ""

    print("\n" + "=" * 70)
    print(f"🔍 Calculando menor caminho ({algo_label}{pen_label})")
    print(f"   Origem : {formatar_musica(G, origem)}")
    print(f"   Destino: {formatar_musica(G, destino)}")
    print("=" * 70)

    if origem == destino:
        print("⚠️  Origem e destino são a mesma música!\n")
        return

    try:
        if algoritmo == 'astar':
            path, dist = a_star(G, origem, destino, penalizar=penalizar)
        else:
            path, dist = dijkstra(G, origem, destino, penalizar=penalizar)

        if path is None:
            print("\n❌ Nenhum caminho encontrado entre essas músicas!")
            print("   As músicas podem estar em componentes desconexos do grafo.\n")
        else:
            print(f"\n✔ Caminho encontrado! ({len(path)} músicas, {len(path)-1} transições)\n")

            for i, node in enumerate(path, 1):
                prefixo = "🎯" if i == len(path) else "🎵" if i == 1 else "  "
                print(f"  {prefixo} {i:2d}. {formatar_musica(G, node)}")

            print(f"\n🎯 Custo total: {dist:.4f}")
            print("=" * 70 + "\n")

    except Exception as e:
        print(f"❌ Erro ao calcular caminho: {e}\n")


# ---------------------------------------------------------------------------
# Menus
# ---------------------------------------------------------------------------

def menu_configuracoes():
    """
    Exibe menu para o usuário escolher algoritmo e modo de penalização.

    Returns:
        Tupla ``(algoritmo, penalizar)``.
    """
    print("\n" + "─" * 70)
    print("⚙️  CONFIGURAÇÕES DA BUSCA")
    print("\n  Algoritmo:")
    print("    1. A* (padrão — mais eficiente)")
    print("    2. Dijkstra")

    opcao_algo = input("\n → Escolha o algoritmo [1]: ").strip() or '1'
    algoritmo = 'astar' if opcao_algo != '2' else 'dijkstra'

    print("\n  Função de custo:")
    print("    1. Distância simples (padrão)")
    print("    2. Com penalização de grandes transições")

    opcao_pen = input("\n → Escolha a função de custo [1]: ").strip() or '1'
    penalizar = opcao_pen == '2'

    print(
        f"\n✔ Configurado: "
        f"{'A*' if algoritmo == 'astar' else 'Dijkstra'}"
        f"{' + penalização' if penalizar else ''}"
    )
    return algoritmo, penalizar


def menu_principal():
    """Exibe o menu principal e retorna a opção escolhida."""
    print("\n" + "=" * 70)
    print("🎵  SISTEMA DE BUSCA DE CAMINHOS ENTRE MÚSICAS")
    print("=" * 70)
    print("\n  1. Buscar caminho entre duas músicas")
    print("  0. Sair")
    return input("\n → Escolha uma opção: ").strip()


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------

def executar_interface(G):
    """Loop principal da interface de usuário."""
    # Configurações padrão
    algoritmo = 'astar'
    penalizar = False

    while True:
        opcao = menu_principal()

        if opcao == '1':
            algoritmo, penalizar = menu_configuracoes()

            print("\n" + "─" * 70)
            origem = listar_e_selecionar_musica(G, "ORIGEM")
            if origem is None:
                print("❌ Busca cancelada.\n")
                continue

            print("\n" + "─" * 70)
            destino = listar_e_selecionar_musica(G, "DESTINO")
            if destino is None:
                print("❌ Busca cancelada.\n")
                continue

            processar_busca_caminho(G, origem, destino, algoritmo, penalizar)
            input("\n[Pressione ENTER para continuar]")

        elif opcao == '0':
            print("\n👋 Até logo!\n")
            break

        else:
            print("❌ Opção inválida!")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    print("🔄 Carregando grafo, aguarde...")

    service = GraphService(root_dir=BASE_DIR)

    try:
        service.run_full_etl()
        G = service.get_graph(force_rebuild=True)

        if not G or len(G.nodes) == 0:
            print("❌ Grafo vazio! Verifique os dados de entrada.")
            return

        print("✔ Grafo carregado com sucesso!")
        executar_interface(G)

    except FileNotFoundError as e:
        print(f"💥 Arquivo não encontrado: {e}")
    except KeyboardInterrupt:
        print("\n\n👋 Encerrando...")
    except Exception as e:
        print(f"💥 Erro inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()