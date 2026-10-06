
"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 02 – OPS Bibliographic Enrichment

Description
-----------
This script enriches the core tabular dataset ("tablon") with
bibliographic information retrieved via the OPS API.

Pipeline logic:
1. Load previously generated parquet dataset.
2. Build core engineered features.
3. Enrich with OPS bibliographic data (limited batch for safety).
4. Persist enriched dataset for downstream modeling.

The logic remains identical to the original implementation.
"""

from src.io_utils import read_any, write_parquet
from src.features_core import build_core_features
from src.ops_enrich import enrich_ops_biblio

# Column containing publication number (adjust if dataset schema changes)
PUB_COL = "publication_number"

# Safety limit for OPS calls (increase gradually in production runs)
LIMIT = 2000


def main():
    """
    Main enrichment pipeline execution.

    Steps:
    - Load raw tablon dataset
    - Compute core features
    - Enrich using OPS bibliographic service
    - Save enriched parquet output
    """

    # Load base dataset
    tablon = read_any("data/raw/tablon.parquet")

    # Build core engineered features
    tablon = build_core_features(tablon)

    # Enrich with OPS bibliographic data
    # NOTE: Logic preserved exactly as in original script
    tablon = enrich_ops_biblio(train, pub_col=PUB_COL, limit=LIMIT)

    # Persist enriched dataset
    write_parquet(tablon, "data/processed/tablon_enriched.parquet")

    print("OK: guardados data/processed/*_enriched.parquet")


if __name__ == "__main__":
    main()
