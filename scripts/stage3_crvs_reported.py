#!/usr/bin/env python3
"""
Stage 3 — Build CRVS "reported mortality" layer.

Reads Morticd10_part1..6 and Population and live births; restricts to Stage 0
included country-years (stage0_included_country_years.csv). Compare country as
string everywhere to avoid 840 vs "840" mismatches.

Outputs:
  - DATA_PROCESSED/reported_mortality_raw.parquet
  - DATA_PROCESSED/reported_allcause_2000_2021.parquet
  - REPORTS/01_CRVS_QA.md (populated with actual QA stats)

Requires: pandas, pyarrow. Depends on Stage 2 (stage0_included_country_years.csv).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Repo root for configs and paths
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from configs.constants import ALL_CAUSE_CAUSE  # noqa: E402

LIST_101 = 101
AUDIT_YEAR_MIN = 2000
AUDIT_YEAR_MAX = 2021


def _load_stage0_included(repo: Path) -> set[tuple[str, int]]:
    """Load (country_code str, year) set from stage0_included_country_years.csv."""
    path = repo / "DATA_PROCESSED" / "stage0_included_country_years.csv"
    df = pd.read_csv(path, dtype={"country_code": str, "year": int})
    return set(zip(df["country_code"].astype(str), df["year"].astype(int)))


def _load_country_names(repo: Path) -> pd.DataFrame:
    """Load RAW_DATA/country_codes -> country_numeric (str), country_name."""
    path = repo / "RAW_DATA" / "country_codes"
    df = pd.read_csv(path)
    # Column names may be 'country','name' or 'country_code','country'
    if "country" in df.columns and "name" in df.columns:
        df = df.rename(columns={"country": "country_numeric", "name": "country_name"})
    elif "country_code" in df.columns and "country" in df.columns:
        df = df.rename(columns={"country_code": "country_numeric", "country": "country_name"})
    else:
        df = df.rename(columns={df.columns[0]: "country_numeric", df.columns[1]: "country_name"})
    df["country_numeric"] = df["country_numeric"].astype(str)
    return df[["country_numeric", "country_name"]]


def _load_iso3_if_available(repo: Path) -> pd.DataFrame | None:
    """Load MAPPINGS/country_numeric_to_iso3.csv if it exists and has iso3 column; else None."""
    path = repo / "MAPPINGS" / "country_numeric_to_iso3.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=True)
    except Exception:
        return None
    if "country_numeric" not in df.columns or "iso3" not in df.columns:
        return None
    # Allow file with only header (no data rows) — merge will still add nullable iso3
    df = df[df["country_numeric"].notna() & (df["country_numeric"].astype(str).str.strip() != "")]
    if df.empty:
        return None
    df["country_numeric"] = df["country_numeric"].astype(str)
    return df[["country_numeric", "iso3"]]


def main() -> int:
    repo = Path(_REPO_ROOT)
    raw_dir = repo / "RAW_DATA"
    out_dir = repo / "DATA_PROCESSED"
    reports_dir = repo / "REPORTS"
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # --- Load Stage 0 inclusion (compare as string)
    included_cy = _load_stage0_included(repo)
    country_names = _load_country_names(repo)
    iso3_df = _load_iso3_if_available(repo)

    qa: list[str] = []
    qa.append("# CRVS layer — QA report (Stage 3)")
    qa.append("")
    qa.append("Stage 0 inclusion (audit universe) is defined by `stage0_included_country_years.csv`; see `scripts/stage2_audit_universe.py` and METHODOLOGY/02.")
    qa.append("")
    qa.append("---")
    qa.append("")
    qa.append("## 1. Inputs")
    qa.append("- Stage 0 included country-years: **%d**" % len(included_cy))
    qa.append("- All-cause cause code (List 101): **%d** (from configs/constants.py ALL_CAUSE_CAUSE)" % ALL_CAUSE_CAUSE)
    qa.append("")

    # --- Concatenate Morticd10 parts
    # Cause can be numeric (1000) or ICD-10 string (e.g. A00) in some parts/lists; read as object then coerce
    parts = []
    for part_num in range(1, 7):
        path = raw_dir / ("Morticd10_part%d" % part_num)
        if not path.exists():
            qa.append("WARNING: Missing %s" % path.name)
            continue
        df = pd.read_csv(path, dtype={"Country": str}, low_memory=False)
        df["source_part"] = part_num
        parts.append(df)
    if not parts:
        qa.append("ERROR: No Morticd10 parts found.")
        with open(reports_dir / "01_CRVS_QA.md", "w", encoding="utf-8") as f:
            f.write("\n".join(qa))
        return 1

    raw = pd.concat(parts, ignore_index=True)
    qa.append("## 2. Filter steps (row counts)")
    qa.append("- After concat (all parts): **%d**" % len(raw))

    # Coerce List, Year, Cause, Sex to numeric (some parts have Cause as ICD-10 string e.g. A00 for List 103)
    raw["List"] = pd.to_numeric(raw["List"], errors="coerce")
    raw["Year"] = pd.to_numeric(raw["Year"], errors="coerce").astype("Int64")
    raw["Cause"] = pd.to_numeric(raw["Cause"], errors="coerce")
    raw["Sex"] = pd.to_numeric(raw["Sex"], errors="coerce")

    # National level
    raw = raw[(raw["Admin1"].isna() | (raw["Admin1"].astype(str).str.strip() == "")) &
              (raw["SubDiv"].isna() | (raw["SubDiv"].astype(str).str.strip() == ""))]
    qa.append("- After Admin1/SubDiv empty (national): **%d**" % len(raw))

    raw = raw[raw["List"] == LIST_101]
    qa.append("- After List=101: **%d**" % len(raw))

    raw = raw[(raw["Year"] >= AUDIT_YEAR_MIN) & (raw["Year"] <= AUDIT_YEAR_MAX)]
    qa.append("- After Year in [2000..2021]: **%d**" % len(raw))

    raw["Country"] = raw["Country"].astype(str)
    raw["_cy"] = list(zip(raw["Country"], raw["Year"]))
    raw = raw[raw["_cy"].isin(included_cy)].drop(columns=["_cy"])
    qa.append("- After restrict to Stage 0 included country-years: **%d**" % len(raw))

    # Guardrail: confirm cause with max Deaths1 per country-year is all-cause (1000)
    raw["Deaths1_num"] = pd.to_numeric(raw["Deaths1"], errors="coerce").fillna(0)
    cause_max = raw.loc[raw.groupby(["Country", "Year"])["Deaths1_num"].idxmax(), ["Country", "Year", "Cause"]]
    n_cy = cause_max.shape[0]
    n_match = (cause_max["Cause"] == ALL_CAUSE_CAUSE).sum()
    qa.append("- All-cause verification: cause with max Deaths1 per country-year equals %d for **%d / %d** country-years" % (ALL_CAUSE_CAUSE, n_match, n_cy))
    raw = raw.drop(columns=["Deaths1_num"])

    # Coerce death columns to numeric
    death_cols = [c for c in raw.columns if c.startswith("Deaths")]
    for c in death_cols:
        raw[c] = pd.to_numeric(raw[c], errors="coerce").fillna(0).astype("Int64")

    # Negative / null check
    neg_deaths = (raw[death_cols] < 0).any(axis=1).sum()
    qa.append("- Rows with any negative death count: **%d**" % neg_deaths)
    if neg_deaths > 0:
        raw = raw[~((raw[death_cols] < 0).any(axis=1))]

    # Duplicates (country-year-sex-cause) before aggregation
    dup_key = ["Country", "Year", "Sex", "Cause"]
    dupes = raw.duplicated(subset=dup_key, keep=False)
    n_dup = dupes.sum()
    qa.append("- Duplicate check key: **(country_numeric, year, cause, sex)**. Duplicate rows: **%d** (kept in raw; all-cause is one row per country-year so no duplicate key there)" % (n_dup // 2 if n_dup else 0))
    qa.append("")

    # Build reported_mortality_raw.parquet (lowercase columns)
    raw_out = raw.copy()
    raw_out = raw_out.rename(columns={
        "Country": "country_numeric",
        "Year": "year",
        "List": "list",
        "Cause": "cause",
        "Sex": "sex",
        "Frmat": "frmat",
    })
    for c in list(raw_out.columns):
        if c.startswith("Deaths"):
            raw_out = raw_out.rename(columns={c: c.lower()})
    if "IM_Frmat" in raw_out.columns:
        raw_out = raw_out.drop(columns=["IM_Frmat"])
    raw_out = raw_out.drop(columns=["Admin1", "SubDiv"], errors="ignore")
    raw_out = raw_out.merge(country_names, on="country_numeric", how="left")
    if iso3_df is not None:
        raw_out = raw_out.merge(iso3_df, on="country_numeric", how="left")
    else:
        raw_out["iso3"] = pd.NA
    death_cols_sorted = sorted([c for c in raw_out.columns if c.startswith("deaths") and c[6:].isdigit()], key=lambda x: int(x[6:]))
    im_cols = sorted([c for c in raw_out.columns if c.startswith("im_")])
    cols_raw = ["country_numeric", "country_name", "iso3", "year", "list", "cause", "sex", "frmat"] + death_cols_sorted + im_cols + ["source_part"]
    cols_raw = [c for c in cols_raw if c in raw_out.columns]
    raw_out = raw_out[cols_raw]
    raw_out.to_parquet(out_dir / "reported_mortality_raw.parquet", index=False)
    qa.append("## 3. Outputs")
    qa.append("- **reported_mortality_raw.parquet**: %d rows" % len(raw_out))
    qa.append("")

    # --- All-cause: cause == ALL_CAUSE_CAUSE; Sex=3 where present else aggregate 1+2
    ac = raw[raw["Cause"] == ALL_CAUSE_CAUSE].copy()
    ac["Deaths1"] = pd.to_numeric(ac["Deaths1"], errors="coerce").fillna(0)
    # One row per (country, year): prefer Sex=3, else sum Sex 1+2
    has_3 = ac[ac["Sex"] == 3][["Country", "Year", "Deaths1"]].rename(columns={"Deaths1": "deaths_allcause"})
    has_3 = has_3.groupby(["Country", "Year"], as_index=False)["deaths_allcause"].sum()
    only_12 = ac[ac["Sex"].isin([1, 2])].groupby(["Country", "Year"], as_index=False)["Deaths1"].sum().rename(columns={"Deaths1": "deaths_allcause"})
    # Prefer Sex=3 where it exists
    both = has_3.merge(only_12, on=["Country", "Year"], how="outer", suffixes=("", "_12"))
    if "deaths_allcause_12" in both.columns:
        both["deaths_allcause"] = both["deaths_allcause"].fillna(both["deaths_allcause_12"])
        both = both.drop(columns=["deaths_allcause_12"])
    both = both[["Country", "Year", "deaths_allcause"]].rename(columns={"Country": "country_numeric", "Year": "year"})
    both["country_numeric"] = both["country_numeric"].astype(str)
    both = both.merge(country_names, on="country_numeric", how="left")
    if iso3_df is not None:
        both = both.merge(iso3_df, on="country_numeric", how="left")
    else:
        both["iso3"] = pd.NA
    both["sex"] = "Both"

    # Population: total = sum(Pop1..Pop26) per row (age bands), then sum across Sex by (Country, Year).
    # Defensible whether Pop1 is "all ages" or first age band — summing all bands gives total population.
    pop_path = raw_dir / "Population and live births"
    if not pop_path.exists():
        qa.append("WARNING: Population file not found; pop_all and crude_rate will be missing.")
        both["pop_all"] = pd.NA
        both["crude_rate"] = pd.NA
        pop_merge_ok = 0
        pop_merge_fail = len(both)
    else:
        pop = pd.read_csv(pop_path, dtype={"Country": str}, low_memory=False)
        pop = pop[(pop["Admin1"].isna() | (pop["Admin1"].astype(str).str.strip() == "")) &
                  (pop["SubDiv"].isna() | (pop["SubDiv"].astype(str).str.strip() == ""))]
        pop["Year"] = pd.to_numeric(pop["Year"], errors="coerce")
        pop = pop[(pop["Year"] >= AUDIT_YEAR_MIN) & (pop["Year"] <= AUDIT_YEAR_MAX)]
        pop_cols = [c for c in pop.columns if c.startswith("Pop") and c[3:].isdigit()]
        pop["pop_row"] = sum(pd.to_numeric(pop[c], errors="coerce").fillna(0) for c in pop_cols)
        pop = pop.groupby(["Country", "Year"], as_index=False)["pop_row"].sum().rename(columns={"Country": "country_numeric", "Year": "year", "pop_row": "pop_all"})
        pop["country_numeric"] = pop["country_numeric"].astype(str)
        n_before = len(both)
        both = both.merge(pop, on=["country_numeric", "year"], how="left")
        pop_merge_ok = both["pop_all"].notna().sum()
        pop_merge_fail = n_before - pop_merge_ok
        # Crude rate per 100k; guard against zero population
        both["crude_rate"] = (both["deaths_allcause"] / both["pop_all"].replace(0, pd.NA) * 100000).round(2)
    qa.append("- Population definition: **sum(Pop1..Pop26)** per row (all age bands), then sum across Sex by (Country, Year). Crude rate = (deaths_allcause / pop_all) × 100,000; zero population → NA.")
    qa.append("- Sex in all-cause table: **Both** (Sex=3 where present, else aggregated 1+2); single value for consistency.")

    allcause_cols = ["country_numeric", "country_name", "iso3", "year", "sex", "deaths_allcause", "pop_all", "crude_rate"]
    both = both[[c for c in allcause_cols if c in both.columns]]
    both.to_parquet(out_dir / "reported_allcause_2000_2021.parquet", index=False)

    qa.append("- **reported_allcause_2000_2021.parquet**: %d rows" % len(both))
    qa.append("- Population merge: **%d** matched, **%d** missing" % (pop_merge_ok, pop_merge_fail))
    expected_cy = len(included_cy)
    achieved_cy = both.groupby(["country_numeric", "year"]).ngroups if "year" in both.columns else 0
    achieved_cy = len(both[["country_numeric", "year"]].drop_duplicates()) if "year" in both.columns else 0
    qa.append("- Included country-years: expected **%d**, in all-cause table **%d**" % (expected_cy, achieved_cy))
    if pop_merge_fail > 0:
        fail_df = both[both["pop_all"].isna()][["country_numeric", "year"]].drop_duplicates()
        qa.append("- Country-years with failed population join: %s" % (fail_df.values.tolist()[:30] if len(fail_df) > 30 else fail_df.values.tolist()))
    qa.append("")

    # Summary for console
    qa.append("## 4. Summary (for audit)")
    qa.append("- Rows (all-cause): **%d**" % len(both))
    qa.append("- Unique countries: **%d**" % both["country_numeric"].nunique())
    qa.append("- Year range: **%d** – **%d**" % (both["year"].min(), both["year"].max()))
    qa.append("- Min deaths_allcause: **%s**" % both["deaths_allcause"].min())
    qa.append("- Max deaths_allcause: **%s**" % both["deaths_allcause"].max())
    qa.append("- Population join success: **%d / %d**" % (pop_merge_ok, len(both)))

    with open(reports_dir / "01_CRVS_QA.md", "w", encoding="utf-8") as f:
        f.write("\n".join(qa))

    print("Wrote %s" % (out_dir / "reported_mortality_raw.parquet"))
    print("Wrote %s" % (out_dir / "reported_allcause_2000_2021.parquet"))
    print("Wrote %s" % (reports_dir / "01_CRVS_QA.md"))
    print("")
    print("Stage 3 summary:")
    print("  Rows (all-cause): %d" % len(both))
    print("  Countries: %d" % both["country_numeric"].nunique())
    print("  Years: %d – %d" % (both["year"].min(), both["year"].max()))
    print("  Min deaths: %s" % both["deaths_allcause"].min())
    print("  Max deaths: %s" % both["deaths_allcause"].max())
    print("  Population join success: %d / %d" % (pop_merge_ok, len(both)))

    return 0


if __name__ == "__main__":
    sys.exit(main())
