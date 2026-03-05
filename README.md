# Musical Recommender 🎵

Sistema de recomendação musical que utiliza **Grafos** e o **Algoritmo de Dijkstra** para criar playlists com transições suaves, baseando-se na similaridade matemática dos atributos de áudio (BPM, Energia, Danceability, etc.).

## 🚀 Instalação

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/seu-usuario/musical-recommender.git](https://github.com/seu-usuario/musical-recommender.git)
Instale as dependências:

2. **Dependecias**
  ```bash
    pip install -r project/requirements.txt
  ```

   
3. **📂 Dataset usado:**
   
  Este projeto utiliza dados reais do Spotify:
  *Spotify Tracks Dataset - Kaggle).*


5. **▶️ Como Executar**
Navegue até a pasta do projeto e rode o arquivo principal:

```Bash

py project/main.py
```

6. **Executar Testes**
Navegue até a pasta do projeto.

```Bash
   pytest --cov=src --cov-report=term-missing -q
```
Gerar relatório html

```Bash
   pytest --cov=src --cov-report=html
```

7. **Plotar Gráficos**
Navegue até a pasta do projeto.

```Bash
   python -m src.evaluation.benchmark_run --n 50 --seed 42
   python -m src.evaluation.benchmark_run --n 50 --seed 42 --penalizar
```

*Desenvolvido para a disciplina de IA.*
