"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 14 – Lightweight Bibliographic Feature Engineering

Description
-----------
Derives structured bibliographic features from publication metadata
including geography, temporal cohorts, and text length metrics.

Input:  data/processed/tablon_text.parquet
Output: data/processed/tablon_biblio_light_0.parquet

Core logic remains unchanged.
"""

from pathlib import Path
import pandas as pd
import numpy as np

INP = Path("data/processed/tablon_text.parquet")
OUT = Path("data/processed/tablon_biblio_light_0.parquet")

def main():
    if not INP.exists():
        raise FileNotFoundError(f"No existe {INP}")

    df = pd.read_parquet(INP)

    df["pub"] = df["pub"].astype(str).str.strip().str.upper()

    df["pub_prefix"] = df["pub"].str[:2]
    for k in ["EP","US","WO","CN","JP","KR","DE","FR","GB","ES"]:
        df[f"pub_is_{k.lower()}"] = (df["pub_prefix"] == k).astype("int8")

    pub_dt = pd.to_datetime(df.get("ops_pub_date"), errors="coerce", utc=True)
    df["pub_year"] = pub_dt.dt.year
    df["pub_month"] = pub_dt.dt.month
    now = pd.Timestamp.utcnow()
    df["patent_age_days"] = (now - pub_dt).dt.days
    df["patent_age_years"] = df["patent_age_days"] / 365.25

    df["title_len"] = df.get("ops_title", "").fillna("").astype(str).str.len()
    df["abstract_len"] = df.get("ops_abstract", "").fillna("").astype(str).str.len()

    df.to_parquet(OUT, index=False)
    print(f"OK: {OUT} | shape={df.shape}")

if __name__ == "__main__":
    main()
