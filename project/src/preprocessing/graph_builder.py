import pandas as pd
import networkx as nx
from sklearn.preprocessing import MinMaxScaler
from scipy.spatial.distance import cdist
import os

# Métricas suportadas na construção do grafo
METRICAS_SUPORTADAS = ('euclidean', 'cityblock', 'cosine')

# ---------------------------------------------------------------------------
# Pesos por feature musical
# ---------------------------------------------------------------------------
FEATURE_WEIGHTS = {
    'energy':            1.5,
    'valence':           1.5,
    'danceability':      1.2,
    'tempo':             0.8,
    'acousticness':      1.0,
    'instrumentalness':  0.6,
}

# Peso aplicado às colunas de gênero após One-Hot Encoding.
GENRE_WEIGHT = 0.5

# Multiplicador aplicado ao peso da aresta quando os nós são de gêneros diferentes.
GENRE_EDGE_PENALTY = 1.1


class GraphBuilder:
    """
    Responsável por transformar um CSV de músicas num Grafo Direcionado (DiGraph).
    Usa K-Nearest Neighbors (K-NN) com métrica de distância configurável.

    Melhorias de similaridade:
        - Gênero incluído como feature via One-Hot Encoding (GENRE_WEIGHT).
        - Pesos individuais por feature numérica (FEATURE_WEIGHTS).
        - Penalidade adicional nas arestas entre músicas de gêneros distintos.
        - Features numéricas normalizadas salvas como atributos dos nós,
          permitindo que a heurística do A* funcione mesmo após carregar
          o grafo do disco via GraphML.

    Métricas disponíveis: ``'euclidean'``, ``'cityblock'``, ``'cosine'``.
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.G = nx.DiGraph()
        self.df = None

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_numeric(df: pd.DataFrame):
        """
        Aplica Min-Max Scaling nas features numéricas.

        Retorna dois DataFrames com o mesmo índice:
          - ``data_norm``: features normalizadas (valores em [0, 1]).
          - ``data_weighted``: features normalizadas × FEATURE_WEIGHTS,
            usadas para calcular distâncias.
        """
        numeric_cols = [c for c in FEATURE_WEIGHTS if c in df.columns]
        if not numeric_cols:
            raise ValueError(
                "O dataset não contém colunas numéricas válidas para "
                "calcular distâncias!"
            )

        data_numeric = df[numeric_cols].copy().dropna()

        scaler = MinMaxScaler()
        data_norm = pd.DataFrame(
            scaler.fit_transform(data_numeric),
            columns=data_numeric.columns,
            index=data_numeric.index,
        )

        data_weighted = data_norm.copy()
        for col in data_weighted.columns:
            data_weighted[col] *= FEATURE_WEIGHTS[col]

        return data_norm, data_weighted

    @staticmethod
    def _add_genre_onehot(data_weighted: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        Concatena colunas One-Hot do gênero (ponderadas por GENRE_WEIGHT)
        à matriz de features ponderadas.
        """
        if 'track_genre' not in df.columns:
            return data_weighted

        genre_series = df.loc[data_weighted.index, 'track_genre'].fillna('unknown')
        genre_dummies = pd.get_dummies(genre_series, prefix='genre').astype(float)
        genre_dummies *= GENRE_WEIGHT
        return pd.concat([data_weighted, genre_dummies], axis=1)

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
            metrica: ``'euclidean'``, ``'cityblock'`` ou ``'cosine'``.

        Returns:
            Um ``nx.DiGraph`` com músicas como nós e distâncias como arestas.
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
        print("-> Construindo matriz de features (pesos + One-Hot gênero)...")

        # data_norm  → valores em [0,1], usados como atributos dos nós
        # data_features → ponderado + One-Hot, usado para cdist
        data_norm, data_weighted = self._normalize_numeric(self.df)
        data_features = self._add_genre_onehot(data_weighted, self.df)

        metrica_label = 'Manhattan' if metrica == 'cityblock' else metrica.capitalize()
        print(f"-> Calculando distâncias ({metrica_label})...")
        dist_matrix = cdist(data_features, data_features, metric=metrica)

        df_dist = pd.DataFrame(
            dist_matrix,
            index=data_features.index,
            columns=data_features.index,
        )

        print(f"-> Criando arestas (K={k_neighbors}, penalidade de gênero ativa)...")
        self.G = nx.DiGraph()

        has_genre = 'track_genre' in self.df.columns
        numeric_cols = list(data_norm.columns)  # features a salvar nos nós
        count = 0
        total = len(data_features)

        for song_id in data_features.index:
            row = self.df.loc[song_id]
            genre = row.get('track_genre', '') if has_genre else ''

            # --- Atributos do nó ---
            # Metadados descritivos
            node_attrs = {
                'name':   row.get('track_name', 'Unknown'),
                'artist': row.get('artists', 'Unknown'),
                'genre':  genre,
            }
            # Features numéricas normalizadas (necessárias para a heurística
            # do A* funcionar mesmo após recarregar o grafo do GraphML)
            for feat in numeric_cols:
                node_attrs[feat] = float(data_norm.loc[song_id, feat])

            self.G.add_node(song_id, **node_attrs)

            # --- Arestas K-NN ---
            vizinhos = df_dist.loc[song_id].nsmallest(k_neighbors + 1).iloc[1:]
            for vizinho_id, distancia in vizinhos.items():
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
        """Salva o grafo em formato GraphML."""
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
        """Carrega um arquivo GraphML do disco."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

        print(f"-> Importando grafo de: {input_path}")
        G = nx.read_graphml(input_path)
        print(f"✔ Grafo carregado! ({G.number_of_nodes()} nós)")
        return G