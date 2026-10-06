"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 21 – Derived Feature Engineering

Description
-----------
Adds derived valuation-relevant features (legal, temporal, family,
and technology proxies) to the final modeling dataset.

Input:  data/processed/final/tablon_final.parquet
Output: data/processed/final/tablon_final_v3.parquet

Core feature logic remains unchanged.
"""

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import date

from src.feature_derived import add_derived_features

IN_DIR = Path("data/processed/final")
OUT_DIR = Path("data/processed/final")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    tablon = pd.read_parquet(IN_DIR / "tablon_final.parquet")

    tablon2 = add_derived_features(
        tablon,
        today=date(2026, 1, 2),
        alpha_alive=0.6,
        beta_recent=0.4,
    )

    tablon2.to_parquet(OUT_DIR / "tablon_final_v3.parquet", index=False)

    print("OK ✅ saved:", tablon2.shape)


if __name__ == "__main__":
    main()
