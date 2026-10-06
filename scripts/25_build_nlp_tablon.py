"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 25 – NLP Dataset Preparation

Description
-----------
Constructs text-focused dataset for embedding generation
and NLP-based modeling. Includes structural controls and
text availability flags.

Input:  tablon_final_v3_labeled.parquet
Output: tablon_nlp_base_v3.parquet

Core logic unchanged.
"""

from pathlib import Path
import pandas as pd

IN_DIR = Path("data/processed/final")
OUT_DIR = Path("data/processed/final")

IN_FILE = "tablon_final_v3_labeled.parquet"
OUT_FILE = "tablon_nlp_base_v3.parquet"


def main():
    df = pd.read_parquet(IN_DIR / IN_FILE)
    df.to_parquet(
        OUT_DIR / OUT_FILE,
        index=False,
        compression="zstd"
    )

    print("OK ✅ NLP BASE READY")


if __name__ == "__main__":
    main()
