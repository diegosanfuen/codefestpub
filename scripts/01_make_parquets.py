"""
EPO CodeFest helper script
--------------------------

Purpose
~~~~~~~
Convert selected raw CSV files under ``data/raw/`` into Parquet format.
This is a small, idempotent utility: if the target Parquet already exists,
it will be skipped.

Notes
~~~~~
- Input:  ``data/raw/<name>.csv``
- Output: ``data/raw/<name>.parquet`` (same folder by design)
- The actual read/write implementations live in ``src.io_utils``.
"""

from pathlib import Path

from src.io_utils import read_any, write_parquet

# Raw data folder (CSV source files live here)
RAW = Path("data/raw")

# Parquet output folder. Kept explicit for readability and future refactors.
# (Currently the same as RAW on purpose.)
OUT = Path("data/raw")


def main() -> None:
    """Entry point: convert the configured datasets from CSV to Parquet."""
    # Extend this list when new datasets are added (e.g., "claims", "families", ...)
    for name in ["tablon"]:
        csv = RAW / f"{name}.csv"
        pq = OUT / f"{name}.parquet"

        # Idempotent behaviour: do nothing if the Parquet already exists.
        if pq.exists():
            print(f"OK: already exists -> {pq}")
            continue

        # If the CSV is present, convert it; otherwise report what's missing.
        if csv.exists():
            df = read_any(csv)
            write_parquet(df, pq)
            print(f"Converted {csv} -> {pq} | shape={df.shape}")
        else:
            print(f"Missing {csv} or {pq} in data/raw/")


if __name__ == "__main__":
    main()
