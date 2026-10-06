# src/roi_proxy.py
import numpy as np
import pandas as pd

def make_roi_proxy(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # señales “de valor” disponibles en biblio
    a = pd.to_numeric(out.get("ops_n_applicants"), errors="coerce").fillna(0)
    i = pd.to_numeric(out.get("ops_n_inventors"), errors="coerce").fillna(0)
    ipc = pd.to_numeric(out.get("ops_n_ipc"), errors="coerce").fillna(0)
    cpc = pd.to_numeric(out.get("ops_n_cpc"), errors="coerce").fillna(0)

    # Proxy continuo (simple pero razonable):
    # - más applicants -> capacidad de explotación (ligero)
    # - más inventors -> complejidad (ligero)
    # - más clasificaciones -> más amplitud / cobertura tecnológica (moderado)
    out["roi_proxy"] = (
        0.25 * np.log1p(a) +
        0.15 * np.log1p(i) +
        0.35 * np.log1p(ipc) +
        0.25 * np.log1p(cpc)
    )

    # Convertimos a 3 clases por cuantiles
    q1 = out["roi_proxy"].quantile(0.33)
    q2 = out["roi_proxy"].quantile(0.66)

    out["roi_class"] = 0
    out.loc[out["roi_proxy"] >= q1, "roi_class"] = 1
    out.loc[out["roi_proxy"] >= q2, "roi_class"] = 2

    return out
