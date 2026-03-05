# src/evaluation/benchmark_run.py
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import time
from typing import Any, Dict, List, Tuple

import pandas as pd

from src.services.graph_service import GraphService
from src.evaluation.instrumented_search import a_star_instrumented, dijkstra_instrumented
from src.evaluation.plots import plot_bar, plot_box


def _pick_pairs(nodes: List[Any], n: int, rng: random.Random) -> List[Tuple[Any, Any]]:
    pairs: List[Tuple[Any, Any]] = []
    if len(nodes) < 2:
        return pairs
    for _ in range(n):
        a, b = rng.sample(nodes, 2)
        pairs.append((a, b))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--k", type=int, default=50)
    parser.add_argument("--metrica", type=str, default="euclidean", choices=["euclidean", "cityblock", "cosine"])
    parser.add_argument("--penalizar", action="store_true")
    parser.add_argument("--force-rebuild", action="store_true")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    gs = GraphService(project_root)
    G = gs.get_graph(k_neighbors=args.k, force_rebuild=args.force_rebuild, metrica=args.metrica)

    nodes = list(G.nodes)
    rng = random.Random(args.seed)
    pairs = _pick_pairs(nodes, args.n, rng)

    rows: List[Dict[str, Any]] = []

    for i, (source, target) in enumerate(pairs, 1):
        t0 = time.perf_counter()
        path_d, cost_d, expanded_d, relax_d = dijkstra_instrumented(G, source, target, penalizar=args.penalizar)
        t1 = time.perf_counter()
        rows.append({
            "query_id": i,
            "algorithm": "Dijkstra",
            "penalizar": args.penalizar,
            "source": source,
            "target": target,
            "found": path_d is not None,
            "time_ms": (t1 - t0) * 1000.0,
            "expanded_nodes": expanded_d,
            "relaxations": relax_d,
            "path_length": 0 if path_d is None else max(0, len(path_d) - 1),
            "path_cost": cost_d,
        })

        t0 = time.perf_counter()
        path_a, cost_a, expanded_a, relax_a = a_star_instrumented(G, source, target, penalizar=args.penalizar)
        t1 = time.perf_counter()
        rows.append({
            "query_id": i,
            "algorithm": "A*",
            "penalizar": args.penalizar,
            "source": source,
            "target": target,
            "found": path_a is not None,
            "time_ms": (t1 - t0) * 1000.0,
            "expanded_nodes": expanded_a,
            "relaxations": relax_a,
            "path_length": 0 if path_a is None else max(0, len(path_a) - 1),
            "path_cost": cost_a,
        })

    df = pd.DataFrame(rows)

    out_dir = os.path.join(project_root, "reports", "benchmark")
    os.makedirs(out_dir, exist_ok=True)

    suffix = f"n{args.n}_k{args.k}_{args.metrica}_{'penal' if args.penalizar else 'nop'}_seed{args.seed}"
    csv_path = os.path.join(out_dir, f"results_{suffix}.csv")
    df.to_csv(csv_path, index=False)

    summary: Dict[str, Any] = {"config": vars(args), "by_algorithm": {}}
    for alg in ["Dijkstra", "A*"]:
        sub_ok = df[(df["algorithm"] == alg) & (df["found"] == True)]

        def agg(col: str) -> Dict[str, float]:
            vals = list(sub_ok[col].astype(float))
            if not vals:
                return {"count": 0}
            return {
                "count": len(vals),
                "mean": statistics.fmean(vals),
                "median": statistics.median(vals),
                "stdev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
                "min": min(vals),
                "max": max(vals),
            }

        summary["by_algorithm"][alg] = {
            "time_ms": agg("time_ms"),
            "expanded_nodes": agg("expanded_nodes"),
            "relaxations": agg("relaxations"),
            "path_length": agg("path_length"),
            "path_cost": agg("path_cost"),
        }

    summary_path = os.path.join(out_dir, f"summary_{suffix}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    df_ok = df[df["found"] == True].copy()
    plot_bar(df_ok, value_col="time_ms", title="Tempo medio por algoritmo (ms)", out_path=os.path.join(out_dir, f"bar_time_{suffix}.png"))
    plot_bar(df_ok, value_col="expanded_nodes", title="Nos expandidos (media) por algoritmo", out_path=os.path.join(out_dir, f"bar_expanded_{suffix}.png"))
    plot_box(df_ok, value_col="time_ms", title="Distribuicao do tempo (ms) por algoritmo", out_path=os.path.join(out_dir, f"box_time_{suffix}.png"))
    plot_box(df_ok, value_col="expanded_nodes", title="Distribuicao de nos expandidos por algoritmo", out_path=os.path.join(out_dir, f"box_expanded_{suffix}.png"))

    print("[OK] CSV:", csv_path)
    print("[OK] Summary:", summary_path)
    print("[OK] Graficos em:", out_dir)


if __name__ == "__main__":
    main()