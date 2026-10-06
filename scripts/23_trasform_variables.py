"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 23 – Variable Normalization & Cleaning

Description
-----------
Applies final cleaning transformations before modeling:
- Missing value handling
- Datetime normalization
- Legal variable stabilization

Input:  tablon_final_v3_labeled.parquet
Output: tablon_final_v3_labeled_tx.parquet

Core logic unchanged.
"""

from pathlib import Path
import pandas as pd

IN_DIR = Path("data/processed/final")
OUT_DIR = Path("data/processed/final")


def main():
    tablon = pd.read_parquet(IN_DIR / "tablon_final_v3_labeled.parquet")
    tablon["legal_events_count"] = tablon["legal_events_count"].fillna(0)
    tablon["ops_pub_date_tx"] = pd.to_datetime(
        tablon["ops_pub_date"], format="%Y%m%d", errors="coerce"
    )

    tablon.to_parquet(
        OUT_DIR / "tablon_final_v3_labeled_tx.parquet", index=False
    )

    print("OK ✅", tablon.shape)


if __name__ == "__main__":
    main()
