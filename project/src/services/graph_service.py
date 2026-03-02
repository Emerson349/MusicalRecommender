import os
import networkx as nx
from src.preprocessing.graph_builder import GraphBuilder
from src.preprocessing.processor import DataProcessor


class GraphService:
    """
    Fachada para usar o módulo preprocessing de forma simples.
    Permite rodar o ETL completo e construir/obter o grafo.
    """

    def __init__(self, root_dir: str):
        """
        Inicializa o serviço definindo a estrutura de arquivos do projeto.

        Args:
            root_dir: Caminho absoluto da raiz do projeto.
        """
        # Diretórios base
        self.dirs = {
            'raw': os.path.join(root_dir, 'data', 'raw'),
            'processed': os.path.join(root_dir, 'data', 'processed'),
        }

        # Todos os paths agora são absolutos e consistentes entre si
        self.files = {
            'input_raw': os.path.join(self.dirs['raw'], 'dataset.csv'),
            'dataset_full': os.path.join(self.dirs['processed'], 'songs_full.csv'),
            'dataset_graph': os.path.join(self.dirs['processed'], 'songs.csv'),
            'graph_obj': os.path.join(self.dirs['processed'], 'graph.graphml'),
        }

        # Cache em memória para evitar recarregar o grafo do disco
        self._graph_cache: nx.DiGraph | None = None

    def run_full_etl(self, samples_per_genre: int = 800) -> bool:
        """
        Executa o pipeline ETL completo:
          1. Gera a base completa (songs_full.csv).
          2. Gera a base amostral balanceada (songs.csv).

        Args:
            samples_per_genre: Número máximo de amostras por gênero.

        Returns:
            True se o ETL concluiu com sucesso, False caso contrário.
        """
        print("[Service] Iniciando Pipeline ETL...")

        if not os.path.exists(self.files['input_raw']):
            raise FileNotFoundError(
                f"Dataset bruto não encontrado em: {self.files['input_raw']}"
            )

        try:
            # Uma única instância reutiliza o cache interno do processor,
            # lendo o CSV bruto apenas uma vez.
            processor = DataProcessor(
                input_path=self.files['input_raw'],
                output_dir=self.dirs['processed']
            )

            print("   -> Processando dataset completo...")
            processor.process_full_dataset(
                filename=os.path.basename(self.files['dataset_full'])
            )

            print(
                f"   -> Processando amostra para grafo "
                f"({samples_per_genre}/gênero)..."
            )
            processor.process_graph_dataset(
                filename=os.path.basename(self.files['dataset_graph']),
                samples_per_genre=samples_per_genre
            )

            # Invalida o cache do grafo, pois os dados mudaram
            self._graph_cache = None
            print("[Service] ETL concluído com sucesso.")
            return True

        except Exception as e:
            print(f"[Service] Erro crítico no ETL: {e}")
            return False

    def get_graph(
        self,
        k_neighbors: int = 50,
        force_rebuild: bool = False,
        metrica: str = 'euclidean'
    ) -> nx.DiGraph:
        """
        Retorna o grafo construído e pronto para uso.

        Ordem de prioridade:
          1. Cache em memória (mais rápido).
          2. Arquivo GraphML salvo em disco.
          3. Construção do zero a partir do CSV amostral.

        Args:
            k_neighbors: Número de vizinhos para cada nó.
            force_rebuild: Se True, ignora cache e disco e reconstrói o grafo.
            metrica: Métrica de distância usada na construção do grafo.
                     Aceita ``'euclidean'``, ``'cityblock'`` ou ``'cosine'``.

        Returns:
            Um ``nx.DiGraph`` com as músicas como nós.

        Raises:
            FileNotFoundError: Se o CSV amostral não existir e ``run_full_etl``
                               ainda não tiver sido executado.
        """
        # 1. Cache em memória
        if self._graph_cache is not None and not force_rebuild:
            return self._graph_cache

        # 2. Arquivo salvo em disco (apenas para a métrica padrão)
        if (
            os.path.exists(self.files['graph_obj'])
            and not force_rebuild
            and metrica == 'euclidean'
        ):
            print("[Service] Carregando grafo salvo do disco...")
            try:
                self._graph_cache = GraphBuilder.load_graph(
                    self.files['graph_obj']
                )
                return self._graph_cache
            except Exception as e:
                print(
                    f"[Service] Erro ao carregar grafo salvo ({e}). "
                    "Reconstruindo..."
                )

        # 3. Constrói do zero
        print(
            f"[Service] Construindo novo grafo a partir do CSV "
            f"(métrica={metrica})..."
        )

        if not os.path.exists(self.files['dataset_graph']):
            raise FileNotFoundError(
                "CSV do grafo não encontrado. "
                "Execute 'run_full_etl()' primeiro."
            )

        builder = GraphBuilder(csv_path=self.files['dataset_graph'])

        # Persiste em disco apenas quando usa a métrica padrão
        save_path = (
            self.files['graph_obj'] if metrica == 'euclidean' else None
        )

        self._graph_cache = builder.build_graph(
            k_neighbors=k_neighbors,
            save_path=save_path,
            metrica=metrica
        )

        return self._graph_cache