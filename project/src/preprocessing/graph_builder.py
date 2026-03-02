import pandas as pd
import numpy as np
import networkx as nx
from sklearn.preprocessing import MinMaxScaler
from scipy.spatial.distance import cdist
import os

# Métricas suportadas na construção do grafo
METRICAS_SUPORTADAS = ('euclidean', 'cityblock', 'cosine')

# ---------------------------------------------------------------------------
# Pesos por feature musical
# ---------------------------------------------------------------------------
# Quanto maior o peso, mais aquela dimensão influencia a distância entre
# duas músicas. Ajuste aqui para mudar o "conceito" de similaridade.
#
#   energy / valence   → definem a "vibe" emocional da música
#   danceability       → ritmo percebido
#   tempo              → BPM — peso menor para não dominar as demais features
#   acousticness       → timbre (acústico vs. elétrico)
#   instrumentalness   → presença de voz — menor peso pois é muito esparso
#
FEATURE_WEIGHTS = {
    'energy':            1.5,
    'valence':           1.5,
    'danceability':      1.2,
    'tempo':             0.8,
    'acousticness':      1.0,
    'instrumentalness':  0.6,
}

# ---------------------------------------------------------------------------
# Configurações do One-Hot de gênero
# ---------------------------------------------------------------------------
# Peso aplicado às colunas de gênero após One-Hot Encoding.
# Mantido baixo para influenciar a similaridade sem criar componentes
# desconexos no grafo — especialmente importante com K pequeno.
GENRE_WEIGHT = 0.5

# ---------------------------------------------------------------------------
# Penalidade de gênero nas arestas
# ---------------------------------------------------------------------------
# Multiplicador aplicado ao peso da aresta quando os dois nós pertencem
# a gêneros diferentes. Valor próximo de 1.0 para não cortar pontes entre
# gêneros distantes (ex: metal → pop).
GENRE_EDGE_PENALTY = 1.1


class GraphBuilder:
    """
    Responsável por transformar um CSV de músicas num Grafo Direcionado (DiGraph).
    Usa K-Nearest Neighbors (K-NN) com métrica de distância configurável.

    Melhorias de similaridade:
        - Gênero incluído como feature via One-Hot Encoding (ponderado por
          ``GENRE_WEIGHT``).
        - Pesos individuais por feature numérica (``FEATURE_WEIGHTS``).
        - Penalidade adicional nas arestas entre músicas de gêneros distintos
          (``GENRE_EDGE_PENALTY``).

    Métricas disponíveis:
        - ``'euclidean'``  — Distância Euclidiana (padrão).
        - ``'cityblock'``  — Distância de Manhattan.
        - ``'cosine'``     — Similaridade do Cosseno (convertida em distância).
    """

    def __init__(self, csv_path: str):
        """
        Inicializa o construtor de grafo com o caminho do dataset.

        Args:
            csv_path: Path do dataset CSV de músicas processado.
        """
        self.csv_path = csv_path
        self.G = nx.DiGraph()
        self.df = None

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
        """
        Constrói a matriz de features usada para calcular distâncias.

        Etapas:
          1. Seleciona features numéricas e aplica Min-Max Scaling.
          2. Multiplica cada coluna pelo seu peso em ``FEATURE_WEIGHTS``.
          3. Se ``track_genre`` existir, gera One-Hot Encoding e pondera
             pelo ``GENRE_WEIGHT``.

        Args:
            df: DataFrame indexado por ``track_id`` com as colunas brutas.

        Returns:
            DataFrame com as features prontas para ``cdist``.
        """
        numeric_cols = [c for c in FEATURE_WEIGHTS if c in df.columns]
        if not numeric_cols:
            raise ValueError(
                "O dataset não contém colunas numéricas válidas para "
                "calcular distâncias!"
            )

        data_numeric = df[numeric_cols].copy().dropna()

        # 1. Normalização Min-Max
        scaler = MinMaxScaler()
        data_norm = pd.DataFrame(
            scaler.fit_transform(data_numeric),
            columns=data_numeric.columns,
            index=data_numeric.index,
        )

        # 2. Pesos por feature
        for col in data_norm.columns:
            data_norm[col] *= FEATURE_WEIGHTS.get(col, 1.0)

        # 3. One-Hot Encoding do gênero
        if 'track_genre' in df.columns:
            genre_series = df.loc[data_norm.index, 'track_genre'].fillna('unknown')
            genre_dummies = pd.get_dummies(genre_series, prefix='genre').astype(float)
            genre_dummies *= GENRE_WEIGHT
            data_norm = pd.concat([data_norm, genre_dummies], axis=1)

        return data_norm

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def build_graph(
        self,
        k_neighbors: int = 50,
        save_path: str = None,
        metrica: str = 'euclidean',
    ) -> nx.DiGraph:
        """
        Constrói o grafo a partir do CSV fornecido no construtor.

        Args:
            k_neighbors: Número de vizinhos mais próximos para cada nó.
            save_path: Path opcional para salvar o grafo em GraphML.
            metrica: Métrica de distância — ``'euclidean'``, ``'cityblock'``
                     ou ``'cosine'``.

        Returns:
            Um ``nx.DiGraph`` com músicas como nós e distâncias como arestas.

        Raises:
            FileNotFoundError: Se o CSV não existir.
            ValueError: Se o dataset não tiver colunas válidas ou a métrica
                        for inválida.
        """
        if metrica not in METRICAS_SUPORTADAS:
            raise ValueError(
                f"Métrica '{metrica}' não suportada. "
                f"Escolha entre: {METRICAS_SUPORTADAS}"
            )

        print(f"--- [GRAFO] Iniciando construção (métrica={metrica}) ---")

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {self.csv_path}")

        self.df = pd.read_csv(self.csv_path)
        if 'track_id' in self.df.columns:
            self.df.set_index('track_id', inplace=True)

        print(f"-> Carregadas {len(self.df)} músicas.")

        # Monta a matriz de features (numérico + gênero One-Hot)
        print("-> Construindo matriz de features (pesos + One-Hot gênero)...")
        data_features = self._build_feature_matrix(self.df)

        # Calcula matriz de distâncias
        metrica_label = 'Manhattan' if metrica == 'cityblock' else metrica.capitalize()
        print(f"-> Calculando distâncias ({metrica_label})...")
        dist_matrix = cdist(data_features, data_features, metric=metrica)

        df_dist = pd.DataFrame(
            dist_matrix,
            index=data_features.index,
            columns=data_features.index,
        )

        # Cria nós e arestas
        print(f"-> Criando arestas (K={k_neighbors}, penalidade de gênero ativa)...")
        self.G = nx.DiGraph()

        has_genre = 'track_genre' in self.df.columns
        count = 0
        total = len(data_features)

        for song_id in data_features.index:
            row = self.df.loc[song_id]
            nome = row.get('track_name', 'Unknown')
            artista = row.get('artists', 'Unknown')
            genre = row.get('track_genre', '') if has_genre else ''

            self.G.add_node(song_id, name=nome, artist=artista, genre=genre)

            vizinhos = df_dist.loc[song_id].nsmallest(k_neighbors + 1).iloc[1:]

            for vizinho_id, distancia in vizinhos.items():
                # Penalidade extra entre gêneros diferentes
                if has_genre:
                    genre_viz = self.df.loc[vizinho_id].get('track_genre', '')
                    if genre != genre_viz:
                        distancia *= GENRE_EDGE_PENALTY

                self.G.add_edge(song_id, vizinho_id, weight=distancia)

            count += 1
            if count % 500 == 0:
                print(f"   Processados {count}/{total} nós...")

        print(
            f"--- [GRAFO] Concluído! "
            f"Nós: {self.G.number_of_nodes()}, "
            f"Arestas: {self.G.number_of_edges()} ---"
        )

        if save_path:
            self.save_graph(save_path)

        return self.G

    def save_graph(self, output_path: str) -> None:
        """
        Salva o grafo em formato GraphML (.graphml).

        Args:
            output_path: Path completo do arquivo de saída.
        """
        if not self.G or len(self.G) == 0:
            print("[AVISO] Grafo vazio. Nada salvo.")
            return

        print(f"-> Exportando grafo para GraphML: {output_path}")
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            nx.write_graphml(self.G, output_path)
            print("✔ Grafo exportado com sucesso.")
        except Exception as e:
            print(f"✖ Erro ao exportar grafo: {e}")

    @staticmethod
    def load_graph(input_path: str) -> nx.DiGraph:
        """
        Carrega um arquivo GraphML do disco.

        Args:
            input_path: Path completo do arquivo GraphML.

        Returns:
            Um ``nx.DiGraph``.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

        print(f"-> Importando grafo de: {input_path}")
        G = nx.read_graphml(input_path)
        print(f"✔ Grafo carregado! ({G.number_of_nodes()} nós)")
        return G