#!/usr/bin/env python3
"""
Stage 5 — Join reported (CRVS) vs estimated (GHE) panels.

Prerequisites:
  - MAPPINGS/country_numeric_to_iso3.csv with country_numeric, iso3 (run scripts/build_country_mapping.py).
  - MAPPINGS/cause_mapping_crvs101_to_ghe.csv (all-cause row: cause_group, mdb_cause_codes, ghe_cause_name).
  - DATA_PROCESSED/reported_allcause_2000_2021.parquet (Stage 3).
  - DATA_PROCESSED/ghe_country_annual_deaths.parquet (Stage 4B).

Builds:
  - reported panel: (country_code=ISO3, year, cause_group, sex, reported_deaths)
  - estimated panel: (country_code, year, cause_group, sex, estimated_deaths) for all-cause
  - full outer join → joined_reported_vs_estimated_allcause.parquet with in_audit_universe from Stage 0.

Outputs:
  - DATA_PROCESSED/joined_reported_vs_estimated_allcause.parquet
  - REPORTS/03_JOIN_QA.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = _REPO_ROOT / "DATA_PROCESSED"
MAPPINGS = _REPO_ROOT / "MAPPINGS"
REPORTS = _REPO_ROOT / "REPORTS"

CAUSE_GROUP_ALL = "All cause"
GHE_CAUSE_NAME_ALL = "All causes"


def _load_country_iso3(repo: Path) -> pd.DataFrame:
    p = repo / "MAPPINGS" / "country_numeric_to_iso3.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, dtype=str)
    if "country_numeric" not in df.columns or "iso3" not in df.columns:
        return pd.DataFrame()
    df = df[df["country_numeric"].notna() & (df["iso3"].notna()) & (df["iso3"].str.strip() != "")]
    return df[["country_numeric", "iso3"]].drop_duplicates()


def _load_cause_mapping_allcause(repo: Path) -> tuple[str, str, str | None]:
    """Returns (cause_group, ghe_cause_name, ghe_cause_code_str)."""
    p = repo / "MAPPINGS" / "cause_mapping_crvs101_to_ghe.csv"
    if not p.exists():
        return CAUSE_GROUP_ALL, GHE_CAUSE_NAME_ALL, "0"
    df = pd.read_csv(p)
    if "cause_group" not in df.columns or "ghe_cause_name" not in df.columns:
        return CAUSE_GROUP_ALL, GHE_CAUSE_NAME_ALL, "0"
    ac = df[df["cause_group"].str.strip().str.lower() == CAUSE_GROUP_ALL.lower()]
    if ac.empty:
        return CAUSE_GROUP_ALL, GHE_CAUSE_NAME_ALL, "0"
    row = ac.iloc[0]
    ghe_code = None
    if "ghe_cause_code" in df.columns:
        v = row.get("ghe_cause_code")
        if pd.notna(v) and str(v).strip() != "":
            try:
                ghe_code = str(int(float(v)))
            except (ValueError, TypeError):
                pass
    return str(row["cause_group"]).strip(), str(row["ghe_cause_name"]).strip(), ghe_code


def main() -> int:
    repo = _REPO_ROOT
    country_iso = _load_country_iso3(repo)
    if country_iso.empty:
        print("No valid rows in MAPPINGS/country_numeric_to_iso3.csv. Run scripts/build_country_mapping.py first.", file=sys.stderr)
        return 1

    cause_group, ghe_cause_name, ghe_cause_code = _load_cause_mapping_allcause(repo)

    reported_path = DATA / "reported_allcause_2000_2021.parquet"
    ghe_path = DATA / "ghe_country_annual_deaths.parquet"
    stage0_path = DATA / "stage0_included_country_years.csv"
    if not reported_path.exists():
        print("Missing %s (run Stage 3)" % reported_path, file=sys.stderr)
        return 1
    if not ghe_path.exists():
        print("Missing %s (run Stage 4B)" % ghe_path, file=sys.stderr)
        return 1
    if not stage0_path.exists():
        print("Missing %s (run Stage 2)" % stage0_path, file=sys.stderr)
        return 1

    rep = pd.read_parquet(reported_path)
    rep["country_numeric"] = rep["country_numeric"].astype(str)
    # Drop existing iso3 from parquet (may be from Stage 3) so merge adds a single iso3 from mapping
    rep = rep.drop(columns=["iso3"], errors="ignore")
    rep = rep.merge(country_iso, on="country_numeric", how="left", validate="m:1")
    rep_matched = rep["iso3"].notna().sum() if "iso3" in rep.columns else 0
    if rep_matched == 0:
        print("No reported rows got iso3. Check country_numeric_to_iso3.csv.", file=sys.stderr)
        return 1
    rep = rep[rep["iso3"].notna()].copy()
    rep = rep.rename(columns={"iso3": "country_code", "deaths_allcause": "reported_deaths"})
    rep["cause_group"] = cause_group
    reported_panel = rep[["country_code", "year", "cause_group", "sex", "reported_deaths"]].copy()

    ghe = pd.read_parquet(ghe_path)
    ghe["year"] = pd.to_numeric(ghe["year"], errors="coerce")
    # All-cause: match by cause_code (0) or cause_title
    if "cause_code" in ghe.columns and ghe_cause_code is not None:
        ghe_ac = ghe[ghe["cause_code"].astype(str).str.strip() == ghe_cause_code]
    else:
        ghe_ac = ghe[ghe["cause_title"].str.strip().str.lower().str.contains("all cause", na=False)]
    if ghe_ac.empty and "cause_title" in ghe.columns:
        ghe_ac = ghe[ghe["cause_title"].str.strip().str.lower() == ghe_cause_name.lower()]
    death_col = "deaths_estimated" if "deaths_estimated" in ghe_ac.columns else "VAL_DTHS_COUNT_NUMERIC"
    if death_col not in ghe_ac.columns:
        print("GHE all-cause subset missing death column", file=sys.stderr)
        return 1
    est = ghe_ac.groupby(["country_code", "year"], as_index=False)[death_col].sum()
    est = est.rename(columns={death_col: "estimated_deaths", "country_code": "country_code"})
    est["cause_group"] = cause_group
    est["sex"] = "Both"

    # Full outer join on (country_code, year, cause_group, sex)
    joined = reported_panel.merge(
        est,
        on=["country_code", "year", "cause_group", "sex"],
        how="outer",
    )
    cols = ["country_code", "year", "cause_group", "sex", "reported_deaths", "estimated_deaths"]
    joined = joined[[c for c in cols if c in joined.columns]]

    # in_audit_universe: (country_code, year) in Stage 0 after mapping country_numeric → iso3
    stage0 = pd.read_csv(stage0_path, dtype={"country_code": str, "year": int})
    stage0 = stage0.rename(columns={"country_code": "country_numeric"})
    stage0["country_numeric"] = stage0["country_numeric"].astype(str)
    stage0 = stage0.merge(country_iso, on="country_numeric", how="left", validate="m:1")
    stage0_with_iso = stage0[stage0["iso3"].notna()]
    stage0_cy = set(zip(stage0_with_iso["iso3"].astype(str), stage0_with_iso["year"]))
    joined["in_audit_universe"] = joined.apply(
        lambda r: (str(r["country_code"]), int(r["year"])) in stage0_cy, axis=1
    )

    out_path = DATA / "joined_reported_vs_estimated_allcause.parquet"
    joined.to_parquet(out_path, index=False)
    print("Wrote %s (%d rows)" % (out_path, len(joined)))

    # QA report
    qa = [
        "# Join QA (Stage 5)",
        "",
        "All-cause join: reported (CRVS) vs estimated (GHE) on (country_code, year, cause_group, sex).",
        "",
        "## 1. Inputs",
        "- reported_allcause_2000_2021.parquet: %d rows (after iso3 match: %d)" % (len(rep), rep_matched),
        "- GHE all-cause rows: %d" % len(ghe_ac),
        "- cause_group: **%s**" % cause_group,
        "",
        "## 2. Joined panel",
        "- **joined_reported_vs_estimated_allcause.parquet**: %d rows" % len(joined),
        "- Unique country_code: **%d**" % joined["country_code"].nunique(),
        "- Year range: **%d – %d**" % (joined["year"].min(), joined["year"].max()),
        "- Rows with both reported and estimated: **%d**" % joined[(joined["reported_deaths"].notna()) & (joined["estimated_deaths"].notna())].shape[0],
        "- Rows reported only: **%d**" % joined[(joined["reported_deaths"].notna()) & (joined["estimated_deaths"].isna())].shape[0],
        "- Rows estimated only: **%d**" % joined[(joined["reported_deaths"].isna()) & (joined["estimated_deaths"].notna())].shape[0],
        "- in_audit_universe True: **%d**" % joined["in_audit_universe"].sum(),
        "",
    ]
    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / "03_JOIN_QA.md", "w", encoding="utf-8") as f:
        f.write("\n".join(qa))
    print("Wrote %s" % (REPORTS / "03_JOIN_QA.md"))

    print("")
    print("Stage 5 summary: %d rows, %d with both reported and estimated" % (
        len(joined),
        joined[(joined["reported_deaths"].notna()) & (joined["estimated_deaths"].notna())].shape[0],
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
