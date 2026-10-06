"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 12 – Legal Status Enrichment

Description
-----------
This script enriches the base patent dataset with legal event information
retrieved via OPS.

Objective
---------
Incorporate legal status indicators (e.g., legal events count, procedural
signals) that may serve as proxies for patent lifecycle dynamics and value.

Pipeline Overview
-----------------
1. Load previously generated tablon dataset.
2. Enrich with legal event data via OPS.
3. Persist enriched dataset for downstream modeling.

Assumptions
-----------
- enrich_legal returns a pandas DataFrame.
- Publication identifier column is named "pub".
- Legal-related features are prefixed with "legal_".

Reproducibility
---------------
Input:  data/processed/tablon.parquet
Output: data/processed/tablon_legal.parquet

Core computational logic has not been modified.
"""

# scripts/12_enrich_legal.py

from pathlib import Path
import pandas as pd

from src.ops_build import enrich_legal

OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    """
    Main legal enrichment pipeline.
    """

    # Load base dataset
    tablon = pd.read_parquet(OUT_DIR / "tablon.parquet")

    # Enrich with legal status information
    # limit can be set (e.g., 20) for quick testing
    tablon2 = enrich_legal(
        tablon,
        pub_col="pub",
        limit=None
    )

    # Persist enriched dataset
    out_path = OUT_DIR / "tablon_legal.parquet"
    tablon2.to_parquet(out_path, index=False)

    print("OK ✅ saved:")
    print(" -", out_path, tablon2.shape)

    # Display sample legal-related columns
    print(
        "Sample legal columns:",
        [c for c in tablon2.columns if c.startswith("legal_")][:20]
    )


if __name__ == "__main__":
    main()
