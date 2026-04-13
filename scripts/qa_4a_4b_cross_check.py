#!/usr/bin/env python3
"""
Cross-check Stage 4A (GHE global snapshot) vs Stage 4B (GHE country annual).

For each snapshot year in 4A (2000, 2010, 2015, 2019, 2020, 2021):
  - 4A world total = sum(deaths_estimated) in ghe_global_snapshot_deaths.parquet for that year.
  - 4B world total = sum(deaths_estimated) in ghe_country_annual_deaths.parquet for that year (sum over all countries and causes).
Expect these to be close (same GHE source; 4A = Excel Global sheet, 4B = OData country-level sum).

Writes REPORTS/02_4A_4B_cross_check.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = _REPO_ROOT / "DATA_PROCESSED"
REPORTS = _REPO_ROOT / "REPORTS"

SNAPSHOT_YEARS = (2000, 2010, 2015, 2019, 2020, 2021)


def main() -> int:
    global_path = DATA / "ghe_global_snapshot_deaths.parquet"
    country_path = DATA / "ghe_country_annual_deaths.parquet"
    if not global_path.exists():
        print("Missing %s (run Stage 4A first)" % global_path, file=sys.stderr)
        return 1
    if not country_path.exists():
        print("Missing %s (run Stage 4B first)" % country_path, file=sys.stderr)
        return 1

    ghe_global = pd.read_parquet(global_path)
    ghe_country = pd.read_parquet(country_path)
    if "year" not in ghe_country.columns:
        print("ghe_country_annual_deaths.parquet missing 'year' column", file=sys.stderr)
        return 1
    ghe_country["year"] = pd.to_numeric(ghe_country["year"], errors="coerce")
    death_col_4a = "deaths_estimated"
    death_col_4b = "deaths_estimated" if "deaths_estimated" in ghe_country.columns else "VAL_DTHS_COUNT_NUMERIC"
    if death_col_4b not in ghe_country.columns:
        print("ghe_country_annual_deaths.parquet missing death count column", file=sys.stderr)
        return 1

    lines = [
        "# Stage 4A vs 4B cross-check",
        "",
        "Compare world total deaths (all causes) by year:",
        "- **4A:** `ghe_global_snapshot_deaths.parquet` (Excel Global YYYY sheets); sum over causes for each snapshot year.",
        "- **4B:** `ghe_country_annual_deaths.parquet` (OData GHE_FULL); sum over all countries and causes for the same year.",
        "",
        "| Year | 4A world total | 4B world total | Diff | Diff % |",
        "|------|----------------|----------------|------|--------|",
    ]

    for year in SNAPSHOT_YEARS:
        a = ghe_global[ghe_global["year"] == year][death_col_4a].sum()
        b = ghe_country[ghe_country["year"] == year][death_col_4b].sum()
        if a == 0:
            pct = "" if b == 0 else "—"
        else:
            pct = "%.2f%%" % (100.0 * (b - a) / a)
        diff = b - a
        lines.append("| %d | %.0f | %.0f | %+.0f | %s |" % (year, a, b, diff, pct))

    a_all = ghe_global[death_col_4a].sum()
    b_all = ghe_country[death_col_4b].sum()
    lines.append("")
    lines.append("**Totals (all snapshot years):** 4A = %.0f, 4B = %.0f, diff = %+.0f." % (a_all, b_all, b_all - a_all))
    lines.append("")
    lines.append("If diff % is within a few percent, 4A and 4B are consistent (rounding and small definition differences possible).")

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / "02_4A_4B_cross_check.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
