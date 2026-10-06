import numpy as np
import pandas as pd

def lagrangian_rank(df: pd.DataFrame,
                    score_col: str,
                    cost_col: str,
                    budget: float,
                    ipc_col: str = None,
                    min_ipc_share: float = 0.0,
                    lam_cost: float = 1.0,
                    lam_conc: float = 0.0):
    """
    Devuelve un ranking que maximiza score - lam_cost*cost - lam_conc*concentración
    bajo un presupuesto aproximado.
    """
    d = df.copy()
    d["lag_score"] = d[score_col] - lam_cost * d[cost_col].fillna(0)

    # Penaliza concentración por IPC si se pide
    if ipc_col and lam_conc > 0:
        # Penalización simple: cuanto más frecuente la IPC, más resta
        freq = d[ipc_col].fillna("UNK").value_counts(normalize=True)
        d["ipc_freq"] = d[ipc_col].fillna("UNK").map(freq)
        d["lag_score"] = d["lag_score"] - lam_conc * d["ipc_freq"]

    d = d.sort_values("lag_score", ascending=False)

    # Selección con budget (tipo mochila sencilla)
    sel = []
    total_cost = 0.0
    ipc_counts = {}

    for _, r in d.iterrows():
        c = float(r[cost_col]) if pd.notna(r[cost_col]) else 0.0
        if total_cost + c > budget:
            continue

        if ipc_col and min_ipc_share > 0:
            ipc = r[ipc_col] if pd.notna(r[ipc_col]) else "UNK"
            # evita que una IPC domine demasiado pronto
            future_n = len(sel) + 1
            future_share = (ipc_counts.get(ipc, 0) + 1) / future_n
            if future_share > (1.0 - min_ipc_share):
                continue

            ipc_counts[ipc] = ipc_counts.get(ipc, 0) + 1

        sel.append(r.name)
        total_cost += c

    return d.loc[sel].copy(), total_cost
