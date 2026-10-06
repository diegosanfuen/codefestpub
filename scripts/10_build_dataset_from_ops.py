"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 10 – Dataset Construction from OPS

Description
-----------
This script retrieves patent publication records from the EPO OPS API
and constructs a structured dataset for downstream patent valuation.

Pipeline Overview
-----------------
1. Build OPS query filtered by publication year.
2. Retrieve publications in controlled batches.
3. Apply polite rate-limiting and exponential backoff.
4. Construct tabular dataset from raw publication objects.
5. Generate ROI proxy features.
6. Persist final dataset in parquet format.

Assumptions
-----------
- OPS configuration parameters are defined in src.config.
- build_dataset_from_pubs returns a pandas DataFrame.
- make_roi_proxy enriches the dataset with ROI proxy variables.

Reproducibility
---------------
Input:  OPS API
Output: data/processed/tablon.parquet

Note: Core computational logic has not been modified.
"""

# scripts/10_build_dataset_from_ops.py

from pathlib import Path
import time
import random

from src.ops_build import ops_search_publications, build_dataset_from_pubs
from src.roi_proxy import make_roi_proxy
from src.config import (
    OPS_QUERY,
    OPS_N_PATENTS,
    OPS_BATCH_LEN,
    OPS_MAX_TRIES,
    OPS_START,
    OPS_PUB_YEAR,
)

OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def polite_sleep(base=1.6, jitter=1.2):
    """
    Apply randomized sleep to reduce risk of OPS rate limiting.
    Sleeps between base and base + jitter seconds.
    """
    time.sleep(base + random.random() * jitter)


def build_query_for_pub_year(base_query: str, year: int):
    """
    Construct alternative OPS queries filtered by publication year.

    Two syntaxes are attempted:
    1) Standard CQL syntax: pd=[start TO end]
    2) Alternative range syntax: pd=start-end

    This improves robustness against wrapper or OPS parsing differences.
    """
    start = f"{year}0101"
    end = f"{year}1231"

    q1 = f"{base_query} and pd=[{start} TO {end}]"
    q2 = f"{base_query} and pd={start}-{end}"

    return q1, q2


def main():
    """
    Main dataset construction pipeline.
    """

    base_query = OPS_QUERY
    total = OPS_N_PATENTS
    batch = OPS_BATCH_LEN
    start = OPS_START
    max_tries = OPS_MAX_TRIES

    q1, q2 = build_query_for_pub_year(base_query, OPS_PUB_YEAR)

    query = q1
    print("OPS query (attempting):", query)

    pubs_all = []

    while len(pubs_all) < total:
        tries = 0

        while True:
            try:
                pubs = ops_search_publications(
                    query=query,
                    start=start,
                    rows=batch
                )
                break

            except RuntimeError as e:
                msg = str(e)

                if (
                    ("400" in msg or "Bad Request" in msg or "parse" in msg.lower())
                    and query == q1
                ):
                    query = q2
                    print("⚠️ Date syntax fallback activated:", query)
                    start = OPS_START
                    pubs_all = []
                    tries = 0
                    continue

                if "403" in msg and "RobotDetected" in msg:
                    tries += 1
                    if tries > max_tries:
                        raise
                    wait = (30 * (2 ** (tries - 1))) + random.randint(0, 15)
                    print(
                        f"RobotDetected. Waiting {wait}s "
                        f"(attempt {tries}/{max_tries})..."
                    )
                    time.sleep(wait)
                    continue

                raise

        if not pubs:
            print("OPS returned 0 publications. Stopping.")
            break

        pubs_all.extend(pubs)
        start += batch

        print(f"Collected: {len(pubs_all)}/{total} (start={start})")
        polite_sleep()

        if (start // batch) % 10 == 0:
            time.sleep(8 + random.random() * 4)

    pubs_all = pubs_all[:total]
    print("Publications retrieved:", len(pubs_all))

    df = build_dataset_from_pubs(pubs_all, max_n=len(pubs_all))
    df = make_roi_proxy(df)

    out_path = OUT_DIR / "tablon.parquet"
    df.to_parquet(out_path, index=False)

    print("OK ✅", df.shape)
    print("Saved:", out_path)


if __name__ == "__main__":
    main()
