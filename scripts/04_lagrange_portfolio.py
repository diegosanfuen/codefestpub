
"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 04 – Lagrangian Portfolio Optimization

Description
-----------
This script applies a Lagrangian-based ranking strategy to construct
an optimized patent portfolio under budget constraints.

Pipeline logic:
1. Load scored test dataset.
2. Select the most appropriate cost proxy column available.
3. Define a budget constraint.
4. Apply Lagrangian ranking with diversification control.
5. Persist selected portfolio subset.

The computational logic remains identical to the original implementation.
"""

from src.io_utils import read_any, write_parquet
from src.model_lagrangian import lagrangian_rank


def main():
    """
    Main portfolio optimization execution.

    Steps:
    - Load scored dataset
    - Identify cost proxy column
    - Compute budget threshold
    - Apply Lagrangian ranking
    - Save selected portfolio
    """

    # Load scored dataset
    df = read_any("data/processed/test_scored.parquet")

    # Define COST proxy (select best available column)
    if "renewal_years" in df.columns:
        cost_col = "renewal_years"
    elif "family_size" in df.columns:
        cost_col = "family_size"
    elif "maintenance_proxy" in df.columns:
        cost_col = "maintenance_proxy"
    else:
        raise RuntimeError("No cost/proxy column found in dataset")

    # Technological diversification column (if available)
    ipc_col = "ops_ipc_main" if "ops_ipc_main" in df.columns else None

    # Budget definition example (adjust depending on scenario)
    budget = float(df[cost_col].fillna(0).quantile(0.30) * 300)

    # Apply Lagrangian ranking
    selected, total_cost = lagrangian_rank(
        df,
        score_col="score",
        cost_col=cost_col,
        budget=budget,
        ipc_col=ipc_col,
        min_ipc_share=0.05,
        lam_cost=1.0,
        lam_conc=0.2
    )

    print("Selected:", selected.shape, "Total cost:", total_cost)

    # Persist selected portfolio
    write_parquet(selected, "data/processed/test_selected_lagrange.parquet")
    print("OK: data/processed/test_selected_lagrange.parquet")


if __name__ == "__main__":
    main()
