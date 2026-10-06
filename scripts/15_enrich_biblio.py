"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 15 – Extended Bibliographic Enrichment

Description
-----------
Enriches dataset with priority, application and publication metadata
retrieved via OPS.

Input:  data/processed/tablon_biblio_light_0.parquet
Output: data/processed/tablon_biblio_light_ext.parquet

Core logic remains unchanged.
"""

from pathlib import Path
import pandas as pd

from src.ops_build import enrich_biblio

OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)
INP = Path("data/processed/tablon_biblio_light_0.parquet")
OUT = Path("data/processed/tablon_biblio_light_ext.parquet")

def main():
    df = pd.read_parquet(INP)
    df2 = enrich_biblio(df, pub_col="pub", limit=None)
    df2.to_parquet(OUT, index=False)

    print("OK saved:", OUT, df2.shape)

if __name__ == "__main__":
    main()
