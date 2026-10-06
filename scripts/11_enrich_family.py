"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 11 – Patent Family Enrichment

Description
-----------
This script enriches the base dataset with simple patent family metrics
retrieved via OPS.

Objective
---------
Incorporate family-level indicators (e.g., family size proxies)
to strengthen valuation-related signals in the portfolio dataset.

Pipeline Overview
-----------------
1. Load previously generated tablon dataset.
2. Enrich with family-level information via OPS.
3. Persist enriched dataset for downstream modeling.

Assumptions
-----------
- enrich_family_simple returns a pandas DataFrame.
- Publication identifier column is named "pub".
- Family-related features are prefixed with "family_".

Reproducibility
---------------
Input:  data/processed/tablon.parquet
Output: data/processed/tablon_family.parquet

Core computational logic has not been modified.
"""

# scripts/11_enrich_family.py

from pathlib import Path
import pandas as pd

from src.ops_build import enrich_family_simple

OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    """
    Main family enrichment pipeline.
    """

    tablon_path = OUT_DIR / "tablon.parquet"

    # Load base dataset
    tablon = pd.read_parquet(tablon_path)

    # Enrich with family-level features
    # limit can be set for quick testing; None means full dataset
    tablon2 = enrich_family_simple(
        tablon,
        pub_col="pub",
        limit=None
    )

    # Persist enriched dataset
    out_path = OUT_DIR / "tablon_family.parquet"
    tablon2.to_parquet(out_path, index=False)

    print("OK ✅ saved:")
    print(" -", out_path, tablon2.shape)

    # Display sample family-related columns
    print(
        "\nSample family columns:",
        [c for c in tablon2.columns if c.startswith("family_")][:10]
    )


if __name__ == "__main__":
    main()
