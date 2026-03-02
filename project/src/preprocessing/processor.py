import pandas as pd
import os


class DataProcessor:
    """
    Classe responsável por processar o dataset bruto de músicas.
    Realiza limpeza, seleção de colunas e amostragem balanceada por gênero.
    Gera dois arquivos CSV:
    1. songs_full.csv  — Dataset completo limpo.
    2. songs.csv       — Amostra balanceada para construção do grafo.
    """

    def __init__(self, input_path: str, output_dir: str):
        """
        Inicializa o processador com caminhos de entrada e saída.

        Args:
            input_path: Caminho do arquivo CSV bruto de entrada.
            output_dir: Diretório onde os arquivos processados serão salvos.
        """
        self.input_path = input_path
        self.output_dir = output_dir

        # Define as colunas que serão usadas no processamento
        self.REQUIRED_COLS = [
            'track_id',
            'track_name',
            'artists',
            'track_genre',
            'tempo',
            'danceability',
            'energy',
            'valence',
            'acousticness',
            'instrumentalness'
        ]

        # Cache interno: evita reler e reprocessar o CSV quando ambos os
        # métodos públicos são chamados na mesma instância (ex.: via ETL).
        self._df_cache: pd.DataFrame | None = None

    def _load_and_filter(self) -> pd.DataFrame:
        """
        [INTERNO] Carrega, seleciona colunas e remove duplicatas/nulos.

        O resultado é armazenado em ``_df_cache`` para que chamadas
        subsequentes dentro da mesma instância não releiam o disco.

        Returns:
            DataFrame limpo e filtrado.
        """
        # Retorna o cache se já tiver sido processado
        if self._df_cache is not None:
            return self._df_cache

        if not os.path.exists(self.input_path):
            raise FileNotFoundError(
                f"Arquivo raw não encontrado: {self.input_path}"
            )

        print("   -> Lendo CSV bruto...")
        df = pd.read_csv(self.input_path, low_memory=False)

        # Verifica quais colunas da lista existem no dataframe
        cols_to_keep = [c for c in self.REQUIRED_COLS if c in df.columns]

        if len(cols_to_keep) < len(self.REQUIRED_COLS):
            missing = set(self.REQUIRED_COLS) - set(cols_to_keep)
            print(f"   [AVISO] Colunas faltando no CSV original: {missing}")

        df = df[cols_to_keep]

        # Limpeza
        initial_len = len(df)
        df = df.dropna()

        if 'track_id' in df.columns:
            df = df.drop_duplicates(subset='track_id')

        if 'track_name' in df.columns and 'artists' in df.columns:
            df = df.drop_duplicates(subset=['track_name', 'artists'])

        print(f"   -> Limpeza: {initial_len} linhas -> {len(df)} linhas válidas.")

        self._df_cache = df
        return df

    def invalidate_cache(self) -> None:
        """
        Descarta o cache interno, forçando nova leitura do CSV na próxima
        chamada a qualquer método de processamento.
        """
        self._df_cache = None

    def process_full_dataset(self, filename: str = 'songs_full.csv') -> str:
        """
        Processa e salva todo o dataset limpo com as colunas selecionadas.

        Args:
            filename: Nome do arquivo de saída para o dataset completo.

        Returns:
            Path completo do arquivo gerado.
        """
        print(f"\n[ETL] Gerando Dataset COMPLETO ({filename})...")

        df = self._load_and_filter()

        os.makedirs(self.output_dir, exist_ok=True)
        full_path = os.path.join(self.output_dir, filename)
        df.to_csv(full_path, index=False)

        print(f"   ✔ Arquivo Mestre salvo em: {full_path}")
        return full_path

    def process_graph_dataset(
        self,
        filename: str = 'songs.csv',
        samples_per_genre: int = 800
    ) -> str:
        """
        Processa e salva uma amostra balanceada por gênero.

        Args:
            filename: Nome do arquivo de saída para o dataset do grafo.
            samples_per_genre: Número máximo de amostras por gênero alvo.

        Returns:
            Path completo do arquivo gerado.
        """
        print(f"\n[ETL] Gerando Dataset para GRAFO ({filename})...")

        df = self._load_and_filter()

        target_genres = [
            'pop', 'rock', 'metal', 'classical', 'acoustic',
            'piano', 'dance', 'brazil', 'jazz', 'hip-hop',
            'electronic', 'reggae'
        ]

        col_genre = 'track_genre' if 'track_genre' in df.columns else None

        if col_genre:
            print(
                f"   -> Filtrando gêneros alvo e coletando "
                f"até {samples_per_genre} amostras..."
            )
            frames = []
            for genre in target_genres:
                df_genre = df[df[col_genre] == genre]
                if len(df_genre) > samples_per_genre:
                    df_genre = df_genre.sample(
                        n=samples_per_genre, random_state=42
                    )
                frames.append(df_genre)

            df_final = pd.concat(frames, ignore_index=True)
        else:
            print(
                "   [!] Coluna de gênero não encontrada. "
                "Fazendo amostragem simples."
            )
            df_final = df.sample(
                n=min(len(df), samples_per_genre * 12), random_state=42
            )

        os.makedirs(self.output_dir, exist_ok=True)
        graph_path = os.path.join(self.output_dir, filename)
        df_final.to_csv(graph_path, index=False)

        print(f"   ✔ Arquivo do Grafo salvo em: {graph_path}")
        print(f"   -> Nós prontos para o grafo: {len(df_final)}")
        return graph_path