#!/usr/bin/env python3
"""
Stage 4A — GHE global snapshot (world totals from Excel "Global YYYY" sheets).

Parses WHO_GHE_2021_country_deaths_2000_2021.xlsx sheets: Global 2000, 2010, 2015, 2019, 2020, 2021.
These sheets are world totals by cause (no country column). Both sexes + Total (all ages) = column 6.
Data starts row 9; columns 0, 2, 6 = cause_code, cause_name_raw, deaths_estimated.

Outputs:
  - DATA_PROCESSED/ghe_global_snapshot_deaths.parquet
  - REPORTS/02A_GHE_GLOBAL_QA.md

Not used for CRVS join (no country); use for global context figures and cause validation.
Country-level GHE = Stage 4B (download or OData).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
XLSX = _REPO_ROOT / "GHE_MODELLED/RAW_DOWNLOAD/WHO_GHE_2021_country_deaths_2000_2021.xlsx"
SHEETS = ["Global 2000", "Global 2010", "Global 2015", "Global 2019", "Global 2020", "Global 2021"]
DATA_START_ROW = 9
COLS = [0, 2, 6]  # cause_code, cause_name_raw, deaths_estimated


def main() -> int:
    out_dir = _REPO_ROOT / "DATA_PROCESSED"
    reports_dir = _REPO_ROOT / "REPORTS"
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not XLSX.exists():
        print("Missing %s" % XLSX, file=sys.stderr)
        return 1

    qa: list[str] = []
    qa.append("# GHE global snapshot — QA (Stage 4A)")
    qa.append("")
    qa.append("Source: Excel **Global YYYY** sheets (world totals by cause). Not country-level; for join use Stage 4B output.")
    qa.append("")
    qa.append("## 1. Parsing")
    qa.append("- Sheets: %s" % ", ".join(SHEETS))
    qa.append("- Filters applied: **Both sexes**, **Total (all ages)** (column 6).")
    qa.append("")

    out = []
    for sh in SHEETS:
        m = re.search(r"(\d{4})$", sh)
        if not m:
            continue
        year = int(m.group(1))
        df = pd.read_excel(XLSX, sheet_name=sh, header=None)
        d = df.iloc[DATA_START_ROW:, COLS].copy()
        d.columns = ["cause_code", "cause_name_raw", "deaths_estimated"]
        d["cause_code"] = pd.to_numeric(d["cause_code"], errors="coerce")
        d["deaths_estimated"] = pd.to_numeric(d["deaths_estimated"], errors="coerce")
        d = d.dropna(subset=["cause_code"])
        d["cause_name_raw"] = d["cause_name_raw"].fillna("").astype(str)
        d = d.dropna(subset=["deaths_estimated"])
        d["year"] = year
        d["region"] = "Global"
        d["sex"] = "Both sexes"
        d["age_group"] = "Total (all ages)"
        d["source_sheet"] = sh
        n = len(d)
        out.append(d)
        qa.append("- **%s**: %d rows" % (sh, n))

    if not out:
        qa.append("ERROR: No data parsed.")
        with open(reports_dir / "02A_GHE_GLOBAL_QA.md", "w", encoding="utf-8") as f:
            f.write("\n".join(qa))
        return 1

    ghe_global = pd.concat(out, ignore_index=True)
    ghe_global = ghe_global[
        ["region", "year", "cause_code", "cause_name_raw", "sex", "age_group", "deaths_estimated", "source_sheet"]
    ]

    out_path = out_dir / "ghe_global_snapshot_deaths.parquet"
    ghe_global.to_parquet(out_path, index=False)

    qa.append("")
    qa.append("## 2. Output")
    qa.append("- **ghe_global_snapshot_deaths.parquet**: %d rows" % len(ghe_global))
    qa.append("- Unique causes (cause_code): **%d**" % ghe_global["cause_code"].nunique())
    qa.append("- Unique years: **%d** (%s)" % (ghe_global["year"].nunique(), sorted(ghe_global["year"].unique().tolist())))
    qa.append("- Min deaths_estimated: **%s**" % ghe_global["deaths_estimated"].min())
    qa.append("- Max deaths_estimated: **%s**" % ghe_global["deaths_estimated"].max())
    missing = ghe_global["deaths_estimated"].isna().sum()
    qa.append("- Missing deaths_estimated: **%d** (%.1f%%)" % (missing, 100.0 * missing / len(ghe_global) if len(ghe_global) else 0))
    qa.append("")
    qa.append("## 3. Summary (for audit)")
    qa.append("- Rows: **%d**" % len(ghe_global))
    qa.append("- Region: **Global** only (no country column in this file).")
    qa.append("- Sex / age: **Both sexes**, **Total (all ages)**.")

    with open(reports_dir / "02A_GHE_GLOBAL_QA.md", "w", encoding="utf-8") as f:
        f.write("\n".join(qa))

    print("Wrote %s" % out_path)
    print("Wrote %s" % (reports_dir / "02A_GHE_GLOBAL_QA.md"))
    print("")
    print("Stage 4A summary: %d rows, %d causes, years %s" % (
        len(ghe_global),
        ghe_global["cause_code"].nunique(),
        sorted(ghe_global["year"].unique().tolist()),
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
