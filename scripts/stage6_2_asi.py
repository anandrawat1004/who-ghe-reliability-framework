#!/usr/bin/env python3
"""
Stage 6.2 — Artificial Smoothness Index (ASI).

For each country with ts_eligible consecutive years: compute roughness R as
median(|d2|) on log(deaths + eps). R_rep = roughness of reported series,
R_est = roughness of estimated series. ASI = R_rep / (R_est + eps).
ASI > 1 ⇒ estimated smoother than reported (potential smoothing).

Input: FEATURES/panel_allcause_matched.parquet (from Stage 6.0).
Outputs: FEATURES/artificial_smoothness_index.parquet, REPORTS/04B_artificial_smoothness.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES = _REPO_ROOT / "FEATURES"
REPORTS = _REPO_ROOT / "REPORTS"

EPS = 1e-6


def _roughness_median_abs_d2(x: np.ndarray) -> float:
    """Roughness = median(|second differences|). x should be 1d sorted by time."""
    if len(x) < 3:
        return np.nan
    d1 = np.diff(x)
    d2 = np.diff(d1)
    return float(np.median(np.abs(d2)))


def main() -> int:
    panel_path = FEATURES / "panel_allcause_matched.parquet"
    if not panel_path.exists():
        print("Missing %s (run Stage 6.0 first)" % panel_path, file=sys.stderr)
        return 1

    REPORTS.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(panel_path)
    # Restrict to ts_eligible and has_both for ASI
    sub = panel[panel["ts_eligible"] & panel["has_both"]].copy()
    if sub.empty:
        print("No ts_eligible rows with has_both", file=sys.stderr)
        return 1

    sub = sub.sort_values(["country_code", "year"])
    sub["log_reported"] = np.log(sub["deaths_reported"].fillna(0) + EPS)
    sub["log_estimated"] = np.log(sub["deaths_estimated"].fillna(0) + EPS)

    rows = []
    for cc, grp in sub.groupby("country_code"):
        grp = grp.sort_values("year")
        if len(grp) < 3:
            continue
        y_rep = grp["log_reported"].values
        y_est = grp["log_estimated"].values
        r_rep = _roughness_median_abs_d2(y_rep)
        r_est = _roughness_median_abs_d2(y_est)
        if np.isnan(r_rep) or np.isnan(r_est):
            continue
        asi = r_rep / (r_est + EPS)
        rows.append({
            "country_code": cc,
            "roughness_reported": r_rep,
            "roughness_estimated": r_est,
            "asi": asi,
            "n_years": len(grp),
        })

    if not rows:
        print("No country series with ≥3 years", file=sys.stderr)
        return 1

    asi_df = pd.DataFrame(rows)
    asi_df.to_parquet(FEATURES / "artificial_smoothness_index.parquet", index=False)

    # Report
    asi_sorted = asi_df.sort_values("asi", ascending=False)
    lines = [
        "# Artificial Smoothness Index (Stage 6.2)",
        "",
        "Roughness = median(|second differences|) on log(deaths + ε). "
        "ASI = R_reported / R_estimated. ASI > 1 ⇒ estimated smoother than reported.",
        "",
        "## 1. Output",
        "- **FEATURES/artificial_smoothness_index.parquet**: one row per country (ts_eligible, has_both).",
        "- Columns: country_code, roughness_reported, roughness_estimated, asi, n_years.",
        "",
        "## 2. Summary",
        "- Countries with ASI: **%d**" % len(asi_df),
        "- ASI > 1 (estimated smoother): **%d**" % (asi_df["asi"] > 1).sum(),
        "- ASI median: **%.3f**" % asi_df["asi"].median(),
        "- ASI mean: **%.3f**" % asi_df["asi"].mean(),
        "",
        "## 3. Top 10 highest ASI (estimated much smoother than reported)",
        "```",
        asi_sorted.head(10).to_string(index=False),
        "```",
        "",
        "## 4. Interpretation",
        "- ASI > 1: GHE series is smoother than CRVS (potential artificial smoothness).",
        "- ASI ~ 1: similar smoothness.",
        "- ASI < 1: GHE more volatile than reported (rare).",
        "",
    ]
    with open(REPORTS / "04B_artificial_smoothness.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Wrote %s" % (FEATURES / "artificial_smoothness_index.parquet"))
    print("Wrote %s" % (REPORTS / "04B_artificial_smoothness.md"))
    print("  Countries with ASI: %d | ASI>1: %d" % (len(asi_df), (asi_df["asi"] > 1).sum()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
