import os
import pandas as pd
import pytest
from src.preprocessing.processor import DataProcessor

def create_raw_csv(tmp_path, missing_cols=False, genres=True, duplicates=False):
    base_len = 3

    data = {
        "track_id": ["1", "2", "3"],
        "track_name": ["SongA", "SongB", "SongC"],
        "artists": ["A1", "A2", "A3"],
        "track_genre": ["pop", "rock", "jazz"] if genres else None,
        "tempo": [120, 130, 140],
        "danceability": [0.5, 0.6, 0.7],
        "energy": [0.8, 0.9, 0.4],
        "valence": [0.2, 0.3, 0.4],
        "acousticness": [0.1, 0.3, 0.5],
        "instrumentalness": [0.0, 0.1, 0.2],
    }

    if duplicates:
        for key in list(data.keys()):
            data[key].append(data[key][-1])

    if missing_cols:
        del data["tempo"]

    df = pd.DataFrame(data)

    csv_file = os.path.join(tmp_path, "raw.csv")
    df.to_csv(csv_file, index=False)
    return csv_file




def test_load_and_filter_basic(tmp_path):
    """testa carregamento basico e limpeza."""
    raw = create_raw_csv(tmp_path)
    dp = DataProcessor(raw, tmp_path)

    df = dp._load_and_filter()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3  
    assert "track_id" in df.columns
    assert df.isna().sum().sum() == 0


def test_load_and_filter_missing_file(tmp_path):
    """Arquivo inexistente: Levantar erro."""
    dp = DataProcessor("arquivo_inexistente.csv", tmp_path)

    with pytest.raises(FileNotFoundError):
        dp._load_and_filter()


def test_load_and_filter_missing_columns(tmp_path):
    """CSV faltando colunas obrigatórias deve avisar e continuar."""
    raw = create_raw_csv(tmp_path, missing_cols=True)
    dp = DataProcessor(raw, tmp_path)

    df = dp._load_and_filter()

    assert isinstance(df, pd.DataFrame)
    assert "tempo" not in df.columns


def test_load_and_filter_remove_duplicates(tmp_path):
    """Testa remoção de duplicatas pelo track_id."""
    raw = create_raw_csv(tmp_path, duplicates=True)
    dp = DataProcessor(raw, tmp_path)

    df = dp._load_and_filter()

    assert len(df) == 3 



def test_process_full_dataset(tmp_path):
    """Gera arquivo songs_full.csv corretamente."""
    raw = create_raw_csv(tmp_path)
    dp = DataProcessor(raw, tmp_path)

    output_path = dp.process_full_dataset()

    assert os.path.exists(output_path)
    df = pd.read_csv(output_path)

    assert len(df) == 3
    assert "track_name" in df.columns



def test_process_graph_dataset_basic(tmp_path):
    """Testa acriação do dataset para grafo com gêneros reconhecidos."""
    raw = create_raw_csv(tmp_path)
    dp = DataProcessor(raw, tmp_path)

    graph_path = dp.process_graph_dataset(samples_per_genre=1)

    assert os.path.exists(graph_path)
    df = pd.read_csv(graph_path)

    assert set(df["track_genre"]).issubset(set([
        'pop', 'rock', 'metal', 'classical', 'acoustic',
        'piano', 'dance', 'brazil', 'jazz', 'hip-hop',
        'electronic', 'reggae'
    ]))





def test_process_graph_dataset_output_size(tmp_path):
    """Testa limite de amostragem por gênero."""
    raw = create_raw_csv(tmp_path)
    dp = DataProcessor(raw, tmp_path)

    graph_path = dp.process_graph_dataset(samples_per_genre=1)
    df = pd.read_csv(graph_path)

    assert len(df) <= 12  



def test_output_dir_created(tmp_path):
    """Diretorio de saída deve ser criado automaticamente."""
    raw = create_raw_csv(tmp_path)

    output_dir = os.path.join(tmp_path, "subfolder")
    dp = DataProcessor(raw, output_dir)

    dp.process_full_dataset()

    assert os.path.exists(output_dir)

def test_process_graph_dataset_no_target_genres(tmp_path):
    """Testa quando a coluna track_genre existe mas nao contém generos da lista alvo."""
    raw = create_raw_csv(tmp_path)

    df = pd.read_csv(raw)
    df["track_genre"] = ["funk", "sertanejo", "blues"]  
    df.to_csv(raw, index=False)

    dp = DataProcessor(raw, tmp_path)
    graph_path = dp.process_graph_dataset(samples_per_genre=2)

    df_out = pd.read_csv(graph_path)

    assert len(df_out) == 0

def test_process_graph_dataset_triggers_sampling(tmp_path):
    """Testa se o metodo ativa sample() quando ha mais que samples_per_genre itens"""
    raw = create_raw_csv(tmp_path, duplicates=True)

    df = pd.read_csv(raw)

    big_df = []
    for i in range(40):
            row = df.iloc[i % len(df)].copy()
            row["track_id"] = str(1000 + i)
            # Garante unicidade para não ser removido na limpeza (drop_duplicates)
            row["track_name"] = f"Song_pop_{i}"
            row["artists"] = f"Artist_{i}"
            row["track_genre"] = "pop"
            big_df.append(row)

    big_df = pd.DataFrame(big_df)
    big_df.to_csv(raw, index=False)

    dp = DataProcessor(raw, tmp_path)
    graph_path = dp.process_graph_dataset(samples_per_genre=5)

    df_out = pd.read_csv(graph_path)

    assert len(df_out) == 5
