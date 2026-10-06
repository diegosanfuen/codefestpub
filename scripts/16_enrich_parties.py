"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 16 – Applicant & Inventor Enrichment

Description
-----------
Enriches dataset with applicant and inventor-related features via OPS.

Input:  data/processed/tablon_biblio_light_ext.parquet
Output: data/processed/tablon_biblio_light_ext1.parquet

Core logic remains unchanged.
"""

from pathlib import Path
import pandas as pd

from src.ops_build import enrich_parties

OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)
INP = Path("data/processed/tablon_biblio_light_ext.parquet")
OUT = Path("data/processed/tablon_biblio_light_ext1.parquet")

def main():
    df = pd.read_parquet(INP)
    df2 = enrich_parties(df, pub_col="pub", limit=None)
    df2.to_parquet(OUT, index=False)

    print("OK saved:", OUT, df2.shape)

if __name__ == "__main__":
    main()
