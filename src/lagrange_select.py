# src/lagrange_select.py
from __future__ import annotations
import numpy as np
import pandas as pd

def lagrange_select(
    df: pd.DataFrame,
    score_col: str = "score_high_roi",
    cost_col: str = "log_family_size",
    budget: float = 50.0,
    lam_cost: float = 1.0,
    top_k: int | None = None,
):
    """
    Selección tipo mochila greedy con Lagrangiano:
      objetivo_i = score_i - lam_cost * cost_i
    y además respeta un presupuesto total de coste.

    - Ordena por (score - lambda*cost) desc
    - Añade mientras no supere budget
    - opcional: top_k max elementos
    """
    d = df.copy()

    d[score_col] = pd.to_numeric(d[score_col], errors="coerce").fillna(0.0)
    d[cost_col]  = pd.to_numeric(d[cost_col], errors="coerce").fillna(0.0)

    d["lag_obj"] = d[score_col] - lam_cost * d[cost_col]
    d = d.sort_values("lag_obj", ascending=False)

    selected_idx = []
    total_cost = 0.0

    for idx, row in d.iterrows():
        c = float(row[cost_col])
        if total_cost + c <= budget:
            selected_idx.append(idx)
            total_cost += c
            if top_k is not None and len(selected_idx) >= top_k:
                break

    sel = d.loc[selected_idx].copy()
    sel["total_cost_budget"] = total_cost
    return sel, total_cost
