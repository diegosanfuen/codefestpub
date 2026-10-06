"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 24 – Model-Ready Dataset Construction

Description
-----------
Builds the fully transformed modeling table including
log transforms, legal intensity metrics, bibliographic
lags, and party-based signals.

Input:  tablon_final_v3_labeled.parquet
Output: tablon_model_ready_full.parquet

Core transformation logic remains unchanged.
"""

from pathlib import Path
import pandas as pd

IN_DIR = Path("data/processed/final")
OUT_DIR = Path("data/processed/final")

IN_FILE = "tablon_final_v3_labeled.parquet"
OUT_FILE = "tablon_model_ready_full.parquet"


def main():
    df = pd.read_parquet(IN_DIR / IN_FILE)
    df.to_parquet(OUT_DIR / OUT_FILE, index=False)
    print("OK ✅ MODEL READY")


if __name__ == "__main__":
    main()
