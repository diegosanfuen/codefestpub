from pathlib import Path
import numpy as np
import pandas as pd

from sentence_transformers import SentenceTransformer

IN_DIR = Path("data/processed/final")
OUT_DIR = Path("data/processed/final")

IN_FILE = "tablon_model_ready_full.parquet"
IN_NLP_FILE = "tablon_nlp_base_v3.parquet"
OUT_FILE = "tablon_model_ready_full_plus_nlp.parquet"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE = 32
HIGH_ROI_CLASS = 2
MAX_CLAIMS_CHARS = 8000  # recorte para rendimiento


def _clean_text(s):
    if pd.isna(s):
        return np.nan
    s = str(s)
    s = " ".join(s.split()).strip()
    return s if s else np.nan


def _len_chars(s):
    return np.nan if pd.isna(s) else len(s)


def transform(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # ============================
    # (A) Variables estructurales mínimas necesarias para interacciones
    #     (Reusamos lo que ya haces en 24_build_model_tablon (1).py)
    # ============================
    out["ops_pub_date_tx"] = pd.to_datetime(out["ops_pub_date"], format="%Y%m%d", errors="coerce")
    out["pub_year"] = out["ops_pub_date_tx"].dt.year

    out["ops_n_cpc"] = out["ops_n_cpc"].fillna(0)
    out["tech_breadth_proxy"] = np.log1p(out["ops_n_cpc"])

    out["family_size_simple"] = out["family_size_simple"].fillna(0)
    out["log_family_size"] = np.log1p(out["family_size_simple"])

    # ============================
    # (B) Texto: longitudes y ratio claims/abstract
    # ============================
    for c in ["text_abstract", "text_claims"]:
        if c in out.columns:
            out[c] = out[c].apply(_clean_text)
        else:
            out[c] = np.nan

    out["abstract_len"] = out["text_abstract"].apply(_len_chars)
    out["claims_len"] = out["text_claims"].apply(_len_chars)

    # ratio seguro
    ratio = out["claims_len"] / out["abstract_len"]
    ratio = ratio.replace([np.inf, -np.inf], np.nan)
    out["log_claims_to_abstract_ratio"] = np.log1p(ratio)

    # ============================
    # (C) Embeddings (abstract) -> semantic_novelty, sim_to_high_roi
    # ============================
    model = SentenceTransformer(MODEL_NAME)

    mask_abs = out["text_abstract"].notna()
    df_abs = out.loc[mask_abs, ["text_abstract", "roi_class_v3"]].copy()

    X_abs = model.encode(
        df_abs["text_abstract"].tolist(),
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # centroid global y novelty (dist coseno = 1 - cos)
    centroid_all = X_abs.mean(axis=0)
    centroid_all = centroid_all / np.linalg.norm(centroid_all)
    semantic_novelty = 1 - np.dot(X_abs, centroid_all)

    # centroid high ROI y similitud
    mask_high = (df_abs["roi_class_v3"] == HIGH_ROI_CLASS).values
    if mask_high.sum() == 0:
        # si no hay clase alta (raro), dejamos NaN
        sim_to_high = np.full(shape=(X_abs.shape[0],), fill_value=np.nan)
    else:
        centroid_high = X_abs[mask_high].mean(axis=0)
        centroid_high = centroid_high / np.linalg.norm(centroid_high)
        sim_to_high = np.dot(X_abs, centroid_high)

    # volcar a out
    out.loc[mask_abs, "semantic_novelty"] = semantic_novelty
    out.loc[mask_abs, "sim_to_high_roi"] = sim_to_high

    # estandarizar sim_to_high_roi (z-score) en el conjunto disponible
    mu = pd.to_numeric(out["sim_to_high_roi"], errors="coerce").mean()
    sd = pd.to_numeric(out["sim_to_high_roi"], errors="coerce").std(ddof=0)
    if sd and sd > 0:
        out["sim_to_high_roi"] = (out["sim_to_high_roi"] - mu) / sd
    else:
        out["sim_to_high_roi"] = np.nan

    # ============================
    # (D) Interacciones clave
    # ============================
    out["novelty_x_family"] = out["semantic_novelty"] * out["log_family_size"]
    out["novelty_x_breadth"] = out["semantic_novelty"] * out["tech_breadth_proxy"]

    # ============================
    # (E) Embeddings claims vs abstract -> sim_claims_abstract
    # ============================
    mask_ca = out["text_claims"].notna() & out["text_abstract"].notna()
    df_ca = out.loc[mask_ca, ["text_claims", "text_abstract"]].copy()
    if len(df_ca) > 0:
        claims_cut = df_ca["text_claims"].str.slice(0, MAX_CLAIMS_CHARS)

        X_ca_abs = model.encode(
            df_ca["text_abstract"].tolist(),
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        X_ca_cla = model.encode(
            claims_cut.tolist(),
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
            normalize_embeddings=True
        )

        sim_claims_abstract = np.sum(X_ca_abs * X_ca_cla, axis=1)
        out.loc[mask_ca, "sim_claims_abstract"] = sim_claims_abstract
    else:
        out["sim_claims_abstract"] = np.nan

    # ============================
    # (F) Selección final: SOLO las 6 variables NLP pedidas + target + pub
    #     (Puedes mergearlo luego con tu tablon_model_ready_full si quieres)
    # ============================
    final_cols = [
        "roi_proxy_v3",
        "roi_class_v3",
        "cost_proxy_v2",
        "pub_year",

        # Anteriores
        "family_size_simple",
        "legal_has_grant_like",
        "legal_has_opposition_like",
        "is_active_recent",
        "log_legal_events_count",
        "log_legal_codes_unique",
        "alive_years",
        "events_per_year",
        "log_title_len",
        "log_abstract_len",
        "age_since_priority",
        "age_since_application",
        "age_since_publication",
        "lag_app_minus_priority",
        "lag_pub_minus_priority",
        "is_A1",
        "log_priority_count",
        "priority_complexity",
        "priority_cohort",
        "log_party_inventor_count",
        "log_party_applicant_count",
        "ops_pub_date",
        "ops_n_cpc",
        "tech_breadth_proxy",
        "log_family_size",
        "pub_year"

        # NLP seleccionadas
        "log_claims_to_abstract_ratio",
        "sim_claims_abstract",
        "semantic_novelty",
        "sim_to_high_roi",          # estandarizada
        "novelty_x_family",
        "novelty_x_breadth",
    ]

    # Mantener solo las columnas que existan
    final_cols = [c for c in final_cols if c in out.columns]
    out = out[final_cols].copy()

    # Target mínimo
    out = out.dropna(subset=["roi_proxy_v3"])

    return out


def main():
    df = pd.read_parquet(IN_DIR / IN_FILE)
    df_nlp = pd.read_parquet(IN_DIR / IN_NLP_FILE)

    df_final = df.merge(
        df_nlp,
        on="pub",
        how="left",
        validate="one_to_one"  # MUY importante
    )
    df_final = df_final.loc[:, ~df_final.columns.duplicated()]
    df_clean = df_final.copy()
    
    cols_x = [c for c in df_clean.columns if c.endswith("_x")]
    
    for c in cols_x:
        base = c[:-2]  # quita _x
        df_clean[base] = df_clean[c]

    cols_y = [c for c in df_clean.columns if c.endswith("_y")]
    df_clean = df_clean.drop(columns=cols_x + cols_y)
    
    df_out = transform(df_clean)

    df_out.to_parquet(OUT_DIR / OUT_FILE, index=False)

    print("OK ✅ NLP FEATURES ADDED")
    print("Shape:", df_out.shape)
    print(df_out.head())


if __name__ == "__main__":
    main()
