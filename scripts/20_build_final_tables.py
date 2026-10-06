"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 20 – Train/Test Table Construction

Description
-----------
Builds consolidated train/test datasets from intermediate processed
artifacts. This stage ensures a clean separation between modeling and
feature engineering layers.

Input:  data/processed/*
Output: data/processed/final/tablon_final.parquet

Core logic remains unchanged.
"""

from src.table_builder import build_train_test_tables


def main():
    tablon_final = build_train_test_tables(
        processed_dir="data/processed",
        out_dir="data/processed/final",
        key="pub",
    )

    print("OK ✅")
    print("tablon_final:", tablon_final.shape)


if __name__ == "__main__":
    main()
