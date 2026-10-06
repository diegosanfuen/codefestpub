import numpy as np
import pandas as pd

def safe_log1p(x):
    return np.log1p(np.clip(x, 0, None))

def build_core_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Ajusta estos nombres a los que existan en tu dataset CodeFest:
    candidates = {
        "family_size": ["family_size", "docdb_family_size", "inpadoc_family_size"],
        "forward_cits_5y": ["forward_citations_5y", "fwd_cits_5y", "cits_fwd_5y"],
        "backward_cits": ["backward_citations", "bwd_cits", "cits_bwd"],
        "n_claims": ["num_claims", "n_claims", "claims_count"],
        "n_inventors": ["num_inventors", "inventor_count", "n_inventors"],
        "n_applicants": ["num_applicants", "applicant_count", "n_applicants"],
        "grant_lag_days": ["grant_lag_days", "days_to_grant", "grant_delay_days"],
        "renewal_years": ["renewal_years", "years_renewed", "renewal_count"],
        "oppositions": ["oppositions_count", "n_oppositions", "opposition_count"],
    }

    def pick(colnames):
        for c in colnames:
            if c in out.columns:
                return c
        return None

    # Log-features (suelen funcionar muy bien en patentes)
    for k, cols in candidates.items():
        c = pick(cols)
        if c:
            out[f"log_{k}"] = safe_log1p(out[c])

    # Ratios típicos de “calidad vs volumen”
    if "log_forward_cits_5y" in out.columns and "log_backward_cits" in out.columns:
        out["cite_balance"] = out["log_forward_cits_5y"] - out["log_backward_cits"]

    if "n_claims" in out.columns and "n_inventors" in out.columns:
        out["claims_per_inventor"] = (out["n_claims"] + 1) / (out["n_inventors"] + 1)

    # Indicadores de “fricción/coste”
    if "log_renewal_years" in out.columns:
        out["maintenance_proxy"] = out["log_renewal_years"]

    if "log_grant_lag_days" in out.columns:
        out["complexity_proxy"] = out["log_grant_lag_days"]

    return out
