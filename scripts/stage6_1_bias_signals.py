#!/usr/bin/env python3
"""
Stage 6.1 — Bias / divergence signals (country × year + country summary).

Input: FEATURES/panel_allcause_matched.parquet (from Stage 6.0).
Signals: pointwise ratio, log_ratio, pct_diff; per-country median log_ratio,
MAPD, share years ratio>threshold; rank tables; bias stability (std log_ratio).

Outputs:
  - FEATURES/bias_signals.parquet
  - REPORTS/04A_bias_signals.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES = _REPO_ROOT / "FEATURES"
REPORTS = _REPO_ROOT / "REPORTS"

RATIO_OVER_THRESHOLD = 1.1  # share of years where ratio > this


def main() -> int:
    panel_path = FEATURES / "panel_allcause_matched.parquet"
    if not panel_path.exists():
        print("Missing %s (run Stage 6.0 first)" % panel_path, file=sys.stderr)
        return 1

    REPORTS.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(panel_path)
    both = panel[panel["has_both"]].copy()

    if both.empty:
        print("No rows with has_both", file=sys.stderr)
        return 1

    eps = 1e-6
    both = both.assign(
        ratio=(both["deaths_estimated"].fillna(0) + eps) / (both["deaths_reported"].fillna(0) + eps),
    )
    if "log_ratio" not in both.columns:
        both["log_ratio"] = np.log(both["ratio"])
    if "abs_pct_diff" not in both.columns:
        both["abs_pct_diff"] = np.abs(both["deaths_estimated"] - both["deaths_reported"]) / (both["deaths_reported"] + eps)
    both["pct_diff"] = (both["deaths_estimated"] - both["deaths_reported"]) / (both["deaths_reported"] + eps)

    # Country-level aggregates
    agg = both.groupby("country_code").agg(
        median_log_ratio=("log_ratio", "median"),
        mean_abs_pct_diff=("abs_pct_diff", "mean"),
        share_ratio_above_threshold=("ratio", lambda s: (s > RATIO_OVER_THRESHOLD).mean()),
        std_log_ratio=("log_ratio", "std"),
        n_years=("year", "count"),
    ).reset_index()
    agg = agg.rename(columns={"mean_abs_pct_diff": "mapd"})
    agg["bias_stability_std_log_ratio"] = agg["std_log_ratio"]
    agg = agg.drop(columns=["std_log_ratio"], errors="ignore")

    # Pointwise + country summary: keep one row per (country, year) with pointwise + merge country stats
    pointwise = both[["country_code", "year", "sex", "ratio", "log_ratio", "pct_diff", "abs_pct_diff", "deaths_reported", "deaths_estimated"]].copy()
    pointwise = pointwise.merge(agg, on="country_code", how="left")
    pointwise.to_parquet(FEATURES / "bias_signals.parquet", index=False)

    # Rank tables
    agg_sorted = agg.sort_values("median_log_ratio")
    under_est = agg_sorted.head(10)[["country_code", "median_log_ratio", "mapd", "n_years"]]
    over_est = agg_sorted.tail(10)[["country_code", "median_log_ratio", "mapd", "n_years"]].iloc[::-1]

    # Report
    lines = [
        "# Bias / divergence signals (Stage 6.1)",
        "",
        "Direction, magnitude, and stability of divergence between reported (CRVS) and estimated (GHE) all-cause deaths.",
        "",
        "## 1. Outputs",
        "- **FEATURES/bias_signals.parquet**: pointwise (country × year) + country-level aggregates.",
        "- Pointwise: ratio, log_ratio, pct_diff, abs_pct_diff; country: median_log_ratio, mapd, share_ratio_above_%.1f, bias_stability_std_log_ratio." % RATIO_OVER_THRESHOLD,
        "",
        "## 2. Summary",
        "- Country-years with both: **%d**" % len(both),
        "- Countries: **%d**" % both["country_code"].nunique(),
        "",
        "## 3. Top 10 under-estimated (ratio < 1, GHE < reported)",
        "```",
        under_est.to_string(index=False),
        "```",
        "",
        "## 4. Top 10 over-estimated (ratio > 1, GHE > reported)",
        "```",
        over_est.to_string(index=False),
        "```",
        "",
        "## 5. Interpretation",
        "- **median_log_ratio** < 0 ⇒ estimated systematically below reported; > 0 ⇒ above.",
        "- **mapd** = mean absolute percent difference (magnitude of divergence).",
        "- **share_ratio_above_%.1f** = fraction of years where estimated/reported > %.1f." % (RATIO_OVER_THRESHOLD, RATIO_OVER_THRESHOLD),
        "- **bias_stability_std_log_ratio** = std of log_ratio across years (high ⇒ direction not consistent).",
        "",
    ]
    with open(REPORTS / "04A_bias_signals.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Wrote %s" % (FEATURES / "bias_signals.parquet"))
    print("Wrote %s" % (REPORTS / "04A_bias_signals.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
