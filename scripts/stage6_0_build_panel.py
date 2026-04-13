#!/usr/bin/env python3
"""
Stage 6.0 — Build the analysis panel (canonical table for 6.1–6.3).

One row per (country_code, year, sex) with reported + estimated + derived signals.
Input: joined_reported_vs_estimated_allcause.parquet.
Population for crude rates: from reported_allcause (via country mapping).

Outputs:
  - FEATURES/panel_allcause_matched.parquet
  - REPORTS/04_STAGE6_PANEL_QA.md

Must-have: country_code, year, sex, deaths_reported, deaths_estimated,
crude_rate_reported, crude_rate_estimated (where pop available), in_audit_universe,
has_both, ts_eligible (T≥5 consecutive years), log_ratio, abs_pct_diff, signed_pct_diff.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = _REPO_ROOT / "DATA_PROCESSED"
FEATURES = _REPO_ROOT / "FEATURES"
REPORTS = _REPO_ROOT / "REPORTS"
MAPPINGS = _REPO_ROOT / "MAPPINGS"

EPS = 1e-6

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from configs.constants import CONSECUTIVE_YEARS_TS  # noqa: E402


def _consecutive_blocks(years: pd.Series) -> list[list[int]]:
    """Return list of consecutive year blocks (each block sorted)."""
    y = sorted(years.dropna().astype(int).unique().tolist())
    if not y:
        return []
    blocks: list[list[int]] = []
    cur: list[int] = [y[0]]
    for v in y[1:]:
        if v == cur[-1] + 1:
            cur.append(v)
        else:
            blocks.append(cur)
            cur = [v]
    blocks.append(cur)
    return blocks


def _ts_eligible_series(years: pd.Series, t: int) -> set[int]:
    """Years that belong to some block of length >= t."""
    blocks = _consecutive_blocks(years)
    eligible = set()
    for b in blocks:
        if len(b) >= t:
            eligible.update(b)
    return eligible


def main() -> int:
    joined_path = DATA / "joined_reported_vs_estimated_allcause.parquet"
    reported_path = DATA / "reported_allcause_2000_2021.parquet"
    mapping_path = MAPPINGS / "country_numeric_to_iso3.csv"
    if not joined_path.exists():
        print("Missing %s (run Stage 5)" % joined_path, file=sys.stderr)
        return 1
    if not reported_path.exists() or not mapping_path.exists():
        print("Missing reported_allcause or country mapping", file=sys.stderr)
        return 1

    FEATURES.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    join_df = pd.read_parquet(joined_path)
    join_df["year"] = pd.to_numeric(join_df["year"], errors="coerce")
    join_df["country_code"] = join_df["country_code"].astype(str)

    # Rename to canonical names
    if "reported_deaths" in join_df.columns:
        join_df = join_df.rename(columns={"reported_deaths": "deaths_reported", "estimated_deaths": "deaths_estimated"})
    join_df["has_both"] = join_df["deaths_reported"].notna() & join_df["deaths_estimated"].notna()

    # Population for crude rates: reported_allcause has country_numeric, year, pop_all
    rep = pd.read_parquet(reported_path)
    rep["country_numeric"] = rep["country_numeric"].astype(str)
    rep = rep.drop(columns=["iso3"], errors="ignore")  # avoid iso3_x/iso3_y when merging
    iso = pd.read_csv(mapping_path, dtype=str)
    iso = iso[iso["country_numeric"].notna() & iso["iso3"].notna()]
    rep = rep.merge(iso[["country_numeric", "iso3"]], on="country_numeric", how="left", validate="m:1")
    rep = rep.rename(columns={"iso3": "country_code"})
    pop_df = rep[["country_code", "year", "pop_all"]].drop_duplicates()
    pop_df["year"] = pd.to_numeric(pop_df["year"], errors="coerce")

    panel = join_df.merge(pop_df, on=["country_code", "year"], how="left", validate="m:1")
    pop_avail = panel["pop_all"].notna() & (panel["pop_all"] > 0)
    panel["crude_rate_reported"] = np.where(
        pop_avail,
        panel["deaths_reported"] / panel["pop_all"] * 100_000,
        np.nan,
    )
    panel["crude_rate_estimated"] = np.where(
        pop_avail,
        panel["deaths_estimated"] / panel["pop_all"] * 100_000,
        np.nan,
    )

    # ts_eligible: (country, year) in a block of >= T consecutive years (among years with has_both)
    both = panel[panel["has_both"]].copy()
    eligible_per_country = both.groupby("country_code")["year"].apply(
        lambda s: _ts_eligible_series(s, CONSECUTIVE_YEARS_TS)
    )
    panel["ts_eligible"] = False
    for cc, years_ok in eligible_per_country.items():
        mask = (panel["country_code"] == cc) & panel["year"].isin(years_ok)
        panel.loc[mask, "ts_eligible"] = True

    # Derived: only where has_both
    rep_ = panel["deaths_reported"].fillna(0) + EPS
    est_ = panel["deaths_estimated"].fillna(0) + EPS
    panel["log_ratio"] = np.where(panel["has_both"], np.log(est_ / rep_), np.nan)
    panel["abs_pct_diff"] = np.where(
        panel["has_both"],
        np.abs(panel["deaths_estimated"] - panel["deaths_reported"]) / (panel["deaths_reported"] + EPS),
        np.nan,
    )
    panel["signed_pct_diff"] = np.where(
        panel["has_both"],
        (panel["deaths_estimated"] - panel["deaths_reported"]) / (panel["deaths_reported"] + EPS),
        np.nan,
    )

    out_cols = [
        "country_code", "year", "sex",
        "deaths_reported", "deaths_estimated",
        "crude_rate_reported", "crude_rate_estimated",
        "in_audit_universe", "has_both", "ts_eligible",
        "log_ratio", "abs_pct_diff", "signed_pct_diff",
    ]
    if "cause_group" in panel.columns:
        out_cols.insert(3, "cause_group")
    panel_out = panel[[c for c in out_cols if c in panel.columns]].copy()
    out_path = FEATURES / "panel_allcause_matched.parquet"
    panel_out.to_parquet(out_path, index=False)

    # QA
    n_both = panel["has_both"].sum()
    n_ts_eligible_cy = panel["ts_eligible"].sum()
    countries_with_both = panel[panel["has_both"]]["country_code"].nunique()
    ts_eligible_countries = panel[panel["ts_eligible"]]["country_code"].nunique()
    qa = [
        "# Stage 6 panel — QA",
        "",
        "Canonical analysis panel for Stage 6.1–6.3. One row per (country_code, year, sex).",
        "",
        "## 1. Output",
        "- **FEATURES/panel_allcause_matched.parquet**: %d rows" % len(panel_out),
        "- Unique country_code: **%d**" % panel_out["country_code"].nunique(),
        "- Year range: **%d – %d**" % (int(panel_out["year"].min()), int(panel_out["year"].max())),
        "",
        "## 2. Matched and time-series eligibility",
        "- Rows with **both** reported and estimated (**has_both**): **%d**" % n_both,
        "- **%d countries** have at least one year with both." % countries_with_both,
        "- **ts_eligible** = (country, year) in a block of **≥ %d consecutive years** (CONSECUTIVE_YEARS_TS)." % CONSECUTIVE_YEARS_TS,
        "- Country-years **ts_eligible**: **%d**" % n_ts_eligible_cy,
        "- **%d countries** have at least one ts_eligible year." % ts_eligible_countries,
        "",
        "> Stage 6 is framed as: **%d countries** have eligible consecutive time series (T≥%d), comprising **%d** country-years."
        % (ts_eligible_countries, CONSECUTIVE_YEARS_TS, n_ts_eligible_cy),
        "",
        "## 3. Fields",
        "- ids: country_code, year, sex",
        "- reported: deaths_reported, crude_rate_reported (where pop available)",
        "- estimated: deaths_estimated, crude_rate_estimated",
        "- flags: in_audit_universe, has_both, ts_eligible",
        "- derived: log_ratio, abs_pct_diff, signed_pct_diff (where has_both)",
        "",
    ]
    with open(REPORTS / "04_STAGE6_PANEL_QA.md", "w", encoding="utf-8") as f:
        f.write("\n".join(qa))

    print("Wrote %s (%d rows)" % (out_path, len(panel_out)))
    print("Wrote %s" % (REPORTS / "04_STAGE6_PANEL_QA.md"))
    print("  has_both: %d rows | ts_eligible: %d rows | %d countries with ts_eligible" % (n_both, n_ts_eligible_cy, ts_eligible_countries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
