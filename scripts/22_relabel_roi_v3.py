"""
EPO CodeFest 2026 – Patent Portfolio (e)valuation
Step 22 – ROI v3 Quantile Relabeling

Description
-----------
Transforms continuous ROI proxy v3 into ordinal classes using
quantile-based thresholds (33% / 66%).

Input:  tablon_final_v3.parquet
Output: tablon_final_v3_labeled.parquet

Core logic unchanged.
"""

from pathlib import Path
import pandas as pd

IN_DIR = Path("data/processed/final")
OUT_DIR = Path("data/processed/final")


def relabel(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    q1 = out["roi_proxy_v3"].quantile(0.33)
    q2 = out["roi_proxy_v3"].quantile(0.66)
    out["roi_class_v3"] = 0
    out.loc[out["roi_proxy_v3"] >= q1, "roi_class_v3"] = 1
    out.loc[out["roi_proxy_v3"] >= q2, "roi_class_v3"] = 2
    return out


def main():
    tablon = pd.read_parquet(IN_DIR / "tablon_final_v3.parquet")
    tablon2 = relabel(tablon)
    tablon2.to_parquet(OUT_DIR / "tablon_final_v3_labeled.parquet", index=False)

    print("OK ✅", tablon2.shape)


if __name__ == "__main__":
    main()
