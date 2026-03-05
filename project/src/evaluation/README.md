# Benchmark (Dijkstra vs A*)

## Rodar
Na pasta `project/`:

```bash
pip install -r requirements.txt
python -m src.evaluation.benchmark_run --n 50 --seed 42
python -m src.evaluation.benchmark_run --n 50 --seed 42 --penalizar
```

## Saida
`project/reports/benchmark/`:
- results_*.csv
- summary_*.json
- bar_*.png e box_*.png