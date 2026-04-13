#!/usr/bin/env python3
"""
Stage 6.3 — Volatility–resilience paradox (quadrant labels).

Per country (ts_eligible, has_both): volatility of reported V_rep (e.g. std of d1),
divergence magnitude D (e.g. median |log_ratio|). Quadrants by median split:
Q1 High V, High D; Q2 High V, Low D; Q3 Low V, High D; Q4 Low V, Low D.

Input: FEATURES/panel_allcause_matched.parquet (from Stage 6.0).
Outputs: FEATURES/volatility_matrix_labels.parquet, REPORTS/04C_volatility_paradox.md
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


def main() -> int:
    panel_path = FEATURES / "panel_allcause_matched.parquet"
    if not panel_path.exists():
        print("Missing %s (run Stage 6.0 first)" % panel_path, file=sys.stderr)
        return 1

    REPORTS.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(panel_path)
    sub = panel[panel["ts_eligible"] & panel["has_both"]].copy()
    if sub.empty:
        print("No ts_eligible rows with has_both", file=sys.stderr)
        return 1

    sub = sub.sort_values(["country_code", "year"])
    sub["log_rep"] = np.log(sub["deaths_reported"].fillna(0) + EPS)
    sub["log_est"] = np.log(sub["deaths_estimated"].fillna(0) + EPS)

    rows = []
    for cc, grp in sub.groupby("country_code"):
        grp = grp.sort_values("year")
        if len(grp) < 2:
            continue
        d1_rep = np.diff(grp["log_rep"].values)
        d1_est = np.diff(grp["log_est"].values)
        v_rep = float(np.std(d1_rep)) if len(d1_rep) > 0 else np.nan
        v_est = float(np.std(d1_est)) if len(d1_est) > 0 else np.nan
        d = float(np.median(np.abs(grp["log_ratio"].values))) if "log_ratio" in grp.columns else np.nan
        if np.isnan(d):
            d = float(np.median(np.abs(np.log((grp["deaths_estimated"].values + EPS) / (grp["deaths_reported"].values + EPS)))))
        rows.append({
            "country_code": cc,
            "volatility_reported": v_rep,
            "volatility_estimated": v_est,
            "divergence_magnitude": d,
            "n_years": len(grp),
        })

    if not rows:
        print("No country series", file=sys.stderr)
        return 1

    vol = pd.DataFrame(rows)
    # Median splits
    med_v = vol["volatility_reported"].median()
    med_d = vol["divergence_magnitude"].median()
    vol["high_volatility_reported"] = vol["volatility_reported"] >= med_v
    vol["high_divergence"] = vol["divergence_magnitude"] >= med_d
    # Quadrants: Q1 High V High D, Q2 High V Low D, Q3 Low V High D, Q4 Low V Low D
    vol["quadrant"] = "Q4"
    vol.loc[vol["high_volatility_reported"] & vol["high_divergence"], "quadrant"] = "Q1"
    vol.loc[vol["high_volatility_reported"] & ~vol["high_divergence"], "quadrant"] = "Q2"
    vol.loc[~vol["high_volatility_reported"] & vol["high_divergence"], "quadrant"] = "Q3"
    vol["quadrant_label"] = vol["quadrant"].map({
        "Q1": "High volatility, High divergence (red flag)",
        "Q2": "High volatility, Low divergence (model tracks chaos)",
        "Q3": "Low volatility, High divergence (suspicious smoothing / systematic bias)",
        "Q4": "Low volatility, Low divergence (stable + aligned)",
    })
    vol.to_parquet(FEATURES / "volatility_matrix_labels.parquet", index=False)

    lines = [
        "# Volatility–resilience paradox (Stage 6.3)",
        "",
        "Quadrants by median split: volatility of reported (V_rep = std of first differences of log deaths) × divergence magnitude (D = median |log_ratio|).",
        "",
        "## 1. Output",
        "- **FEATURES/volatility_matrix_labels.parquet**: country_code, volatility_reported, volatility_estimated, divergence_magnitude, quadrant, quadrant_label.",
        "",
        "## 2. Quadrant counts",
        "```",
        vol["quadrant"].value_counts().sort_index().to_string(),
        "```",
        "",
        "## 3. Quadrant definitions",
        "- **Q1**: High V_rep, High D — red flag.",
        "- **Q2**: High V_rep, Low D — model tracks chaos.",
        "- **Q3**: Low V_rep, High D — suspicious smoothing / systematic bias.",
        "- **Q4**: Low V_rep, Low D — stable + aligned.",
        "",
        "## 4. Sample by quadrant",
        "",
    ]
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        qq = vol[vol["quadrant"] == q][["country_code", "volatility_reported", "divergence_magnitude", "n_years"]].head(5)
        lines.append("### %s" % q)
        lines.append("```")
        lines.append(qq.to_string(index=False))
        lines.append("```")
        lines.append("")
    with open(REPORTS / "04C_volatility_paradox.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Wrote %s" % (FEATURES / "volatility_matrix_labels.parquet"))
    print("Wrote %s" % (REPORTS / "04C_volatility_paradox.md"))
    print("  Quadrants: " + ", ".join("%s=%d" % (q, (vol["quadrant"] == q).sum()) for q in ("Q1", "Q2", "Q3", "Q4")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
