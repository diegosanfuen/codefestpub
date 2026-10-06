"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 17 – Full Text Enrichment

Description
-----------
Retrieves extended textual content (claims and description) and
derives NLP-ready text fields for embedding generation.

Input:  data/processed/tablon_biblio_light_ext1.parquet
Output: data/processed/tablon_biblio_light.parquet

Core logic remains unchanged.
"""

from pathlib import Path
import pandas as pd

from src.ops_build import enrich_text

OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = Path("data/processed/tablon_biblio_light.parquet")
INP = Path("data/processed/tablon_biblio_light_ext1.parquet")

def main():
    df = pd.read_parquet(INP)

    df2 = enrich_text(
        df,
        pub_col="pub",
        limit=200,
        include_claims=True,
        include_description=True,
    )

    df2.to_parquet(OUT, index=False)

    print("OK saved:", OUT, df2.shape)

if __name__ == "__main__":
    main()
