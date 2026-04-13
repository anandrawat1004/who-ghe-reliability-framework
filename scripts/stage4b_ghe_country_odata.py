#!/usr/bin/env python3
"""
Stage 4B — GHE country-level annual deaths via WHO GHO OData API.

Pulls from GHE_FULL:
  DIM_COUNTRY_CODE, DIM_YEAR_CODE, DIM_GHECAUSE_CODE, DIM_GHECAUSE_TITLE,
  VAL_DTHS_COUNT_NUMERIC (death counts).
Filter: year 2000–2021, Both sexes, All ages. Paginates with $top/$skip;
caches raw JSON in GHE_MODELLED/ANNUAL_ODATA_CACHE/; merge → parquet + QA.

Usage:
  python3 scripts/stage4b_ghe_country_odata.py           # full pull + merge
  python3 scripts/stage4b_ghe_country_odata.py --discover  # print REF codes only
  python3 scripts/stage4b_ghe_country_odata.py --resume   # skip already-cached pages; retry 5xx
  python3 scripts/stage4b_ghe_country_odata.py --merge-only  # merge existing cache only (no API)

After a complete pull (last page < 10k rows), you do not need to run --resume. Use --merge-only to re-merge cache to parquet without calling the API.

Requires: pandas, pyarrow (for merge). Retries 5xx errors with backoff.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urljoin

MAX_RETRIES = 5
RETRY_BACKOFF_BASE = 2  # seconds; 2^attempt
REQUEST_TIMEOUT = 90

_REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://xmart-api-public.who.int/DEX_CMS/"
ENTITY = "GHE_FULL"
TOP = 10000
CACHE_DIR = _REPO_ROOT / "GHE_MODELLED" / "ANNUAL_ODATA_CACHE"
OUT_PARQUET = _REPO_ROOT / "DATA_PROCESSED" / "ghe_country_annual_deaths.parquet"
REPORTS_DIR = _REPO_ROOT / "REPORTS"

# Default filter codes (from REF_SEX_COD / REF_AGE_COD: Total = both sexes, TOTAL = all ages)
SEX_BOTH = "TOTAL"
AGE_ALL = "TOTAL"
YEAR_MIN = 2000
YEAR_MAX = 2021
USE_FLAG_SHOW = False  # Set True if GHE_FULL has FLAG_SHOW; else API may 400

SELECT = "DIM_COUNTRY_CODE,DIM_YEAR_CODE,DIM_GHECAUSE_CODE,DIM_GHECAUSE_TITLE,DIM_SEX_CODE,DIM_AGEGROUP_CODE,VAL_DTHS_COUNT_NUMERIC"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code and 400 <= e.code < 500:
                raise
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                print("  HTTP %s at attempt %d; retry in %ds..." % (e.code, attempt + 1, wait), file=sys.stderr)
                time.sleep(wait)
            else:
                raise
        except OSError as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                print("  %s; retry in %ds..." % (e, wait), file=sys.stderr)
                time.sleep(wait)
            else:
                raise last_err
    raise last_err


def discover_ref_codes() -> None:
    """Fetch REF_SEX_COD and REF_AGE_COD (or REF_AGEGROUP_CODE) to confirm filter codes."""
    for ref in ["REF_SEX_COD", "REF_AGE_COD", "REF_AGEGROUP_CODE"]:
        url = urljoin(BASE_URL, ref)
        try:
            data = _get(url)
            vals = data.get("value", [])
            print("%s: %d rows" % (ref, len(vals)))
            for row in vals[:15]:
                print("  ", row)
        except Exception as e:
            print("%s: %s" % (ref, e))


def pull_page(skip: int, sex_code: str, age_code: str) -> dict:
    filter_parts = [
        "DIM_YEAR_CODE ge %d and DIM_YEAR_CODE le %d" % (YEAR_MIN, YEAR_MAX),
        "DIM_SEX_CODE eq '%s'" % sex_code,
        "DIM_AGEGROUP_CODE eq '%s'" % age_code,
    ]
    if USE_FLAG_SHOW:
        filter_parts.append("FLAG_SHOW eq 1")
    params = {
        "$select": SELECT,
        "$filter": " and ".join(filter_parts),
        "$top": TOP,
        "$skip": skip,
    }
    url = urljoin(BASE_URL, ENTITY + "?" + urlencode(params))
    return _get(url)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 4B: Pull GHE country annual deaths from OData")
    parser.add_argument("--discover", action="store_true", help="Only fetch REF codes and exit")
    parser.add_argument("--resume", action="store_true", help="Skip pages already in cache")
    parser.add_argument("--merge-only", action="store_true", help="Only merge existing cache to parquet + QA (no API)")
    parser.add_argument("--sex", default=SEX_BOTH, help="Sex filter code (default TOTAL)")
    parser.add_argument("--age", default=AGE_ALL, help="Age group filter code (default TOTAL)")
    args = parser.parse_args()

    if args.discover:
        discover_ref_codes()
        return 0

    import pandas as pd

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _REPO_ROOT.joinpath("DATA_PROCESSED").mkdir(parents=True, exist_ok=True)

    if not args.merge_only:
        # Paginate: fetch until empty (or fail after retries; then merge what we have)
        skip = 0
        page_num = 0
        while True:
            cache_file = CACHE_DIR / ("ghe_full_page_%05d.json" % page_num)
            if args.resume and cache_file.exists():
                skip += TOP
                page_num += 1
                continue
            try:
                data = pull_page(skip, args.sex, args.age)
            except Exception as e:
                print("Pull failed at skip=%d after retries: %s" % (skip, e), file=sys.stderr)
                print("Merging existing cache (%d pages so far). Re-run with --resume to continue later." % page_num, file=sys.stderr)
                break
            vals = data.get("value", [])
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=0)
            print("Cached %s (%d rows)" % (cache_file.name, len(vals)))
            if len(vals) < TOP:
                break
            skip += TOP
            page_num += 1
            time.sleep(0.5)

    # Merge all cached pages
    all_rows = []
    for f in sorted(CACHE_DIR.glob("ghe_full_page_*.json")):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        all_rows.extend(data.get("value", []))
    if not all_rows:
        print("No data to merge.", file=sys.stderr)
        return 1

    df = pd.DataFrame(all_rows)
    rename = {
        "DIM_COUNTRY_CODE": "country_code",
        "DIM_YEAR_CODE": "year",
        "DIM_GHECAUSE_CODE": "cause_code",
        "DIM_GHECAUSE_TITLE": "cause_title",
        "DIM_SEX_CODE": "sex_code",
        "DIM_AGEGROUP_CODE": "age_group_code",
        "VAL_DTHS_COUNT_NUMERIC": "deaths_estimated",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for c in ["country_code", "year", "cause_code", "deaths_estimated"]:
        if c not in df.columns:
            print("Missing column %s" % c, file=sys.stderr)
            return 1
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["deaths_estimated"] = pd.to_numeric(df["deaths_estimated"], errors="coerce")
    df = df.dropna(subset=["country_code", "year"])
    df.to_parquet(OUT_PARQUET, index=False)
    print("Wrote %s (%d rows)" % (OUT_PARQUET, len(df)))

    # QA report
    qa = []
    qa.append("# GHE country annual — QA (Stage 4B)")
    qa.append("")
    qa.append("Source: WHO GHO OData **GHE_FULL**. Death counts: **VAL_DTHS_COUNT_NUMERIC**.")
    qa.append("")
    qa.append("## 1. Output")
    qa.append("- **ghe_country_annual_deaths.parquet**: %d rows" % len(df))
    qa.append("- Unique countries: **%d**" % df["country_code"].nunique())
    qa.append("- Year range: **%d – %d**" % (df["year"].min(), df["year"].max()))
    qa.append("- Unique causes: **%d**" % df["cause_code"].nunique())
    qa.append("- Min deaths_estimated: **%s**" % df["deaths_estimated"].min())
    qa.append("- Max deaths_estimated: **%s**" % df["deaths_estimated"].max())
    missing = df["deaths_estimated"].isna().sum()
    qa.append("- Missing deaths_estimated: **%d** (%.1f%%)" % (missing, 100.0 * missing / len(df) if len(df) else 0))
    dup_cols = [c for c in ["country_code", "year", "cause_code", "sex_code", "age_group_code"] if c in df.columns]
    dup = df.duplicated(subset=dup_cols).sum() if dup_cols else 0
    qa.append("- Duplicates (%s): **%d**" % (", ".join(dup_cols), dup))
    qa.append("")
    qa.append("## 2. Sample countries (first 10)")
    sample = df.groupby("country_code").agg({"year": "count", "deaths_estimated": "sum"}).rename(
        columns={"year": "n_rows", "deaths_estimated": "total_deaths_estimated"}
    ).head(10)
    qa.append("(n_rows = country×year×cause rows; total_deaths_estimated = sum over all causes/years.)")
    qa.append("```")
    qa.append(sample.to_string())
    qa.append("```")
    with open(REPORTS_DIR / "02B_GHE_COUNTRY_QA.md", "w", encoding="utf-8") as f:
        f.write("\n".join(qa))
    print("Wrote %s" % (REPORTS_DIR / "02B_GHE_COUNTRY_QA.md"))

    print("")
    print("Stage 4B summary: %d rows, %d countries, years %d–%d" % (
        len(df), df["country_code"].nunique(), int(df["year"].min()), int(df["year"].max())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
