# src/evaluation/plots.py
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def plot_bar(df: pd.DataFrame, *, value_col: str, title: str, out_path: str) -> None:
    means = df.groupby("algorithm")[value_col].mean().sort_index()
    plt.figure()
    means.plot(kind="bar")
    plt.title(title)
    plt.xlabel("Algoritmo")
    plt.ylabel(value_col)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_box(df: pd.DataFrame, *, value_col: str, title: str, out_path: str) -> None:
    plt.figure()
    df.boxplot(column=value_col, by="algorithm")
    plt.title(title)
    plt.suptitle("")
    plt.xlabel("Algoritmo")
    plt.ylabel(value_col)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()