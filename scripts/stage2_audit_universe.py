#!/usr/bin/env python3
"""
Stage 2 — Audit universe (Stage 0 inclusion).

Reads RAW_DATA/AVAILABILITY_list_ctry_years_feb2025.xlsx (sheets avail_mortality, avail_pop),
builds country-year availability, included list (mortality + population both present, 2000–2021),
and high-quality subset (≥3 consecutive years in 2000–2021).

Mortality availability is defined as List=101 (ICD-10) in the availability file; see stage0_manifest.yml.

Robustness: sheets resolved by name (workbook.xml + rels); sharedStrings optional; inlineStr supported;
list/year parsed via int(float(s)) so "101.0" and " 101 " work.

Outputs to DATA_PROCESSED/:
  - country_year_availability.csv
  - stage0_included_country_years.csv
  - stage0_high_quality_subset.csv
  - stage0_manifest.yml

Uses only Python standard library (zipfile, xml.etree).
"""

from __future__ import annotations

import csv
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Single source for HQ threshold (avoids drift from configs/constants.py)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from configs.constants import CONSECUTIVE_YEARS_HQ  # noqa: E402

NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
AUDIT_YEAR_MIN = 2000
AUDIT_YEAR_MAX = 2021
LIST_101 = 101  # ICD-10 in availability sheet


def col_letter_to_i(ref: str) -> int:
    m = re.match(r"^([A-Z]+)", ref)
    if not m:
        return 0
    s = m.group(1)
    i = 0
    for c in s:
        i = i * 26 + (ord(c) - ord("A") + 1)
    return i - 1


def get_sheet_paths(z: zipfile.ZipFile) -> dict[str, str]:
    """Resolve sheet name -> xl/worksheets/sheetN.xml via workbook.xml and workbook.xml.rels."""
    wb_root = ET.fromstring(z.read("xl/workbook.xml"))
    # Sheet elements: name + rId (relationship id)
    name_to_rid: dict[str, str] = {}
    for elem in wb_root.iter():
        if elem.tag.endswith("}sheet"):
            name = elem.get("name")
            rid = elem.get("{%s}id" % REL_NS) or elem.get("id")
            if name and rid:
                name_to_rid[name] = rid
    rels_root = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target: dict[str, str] = {}
    for rel in rels_root:
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target and "worksheet" in target:
            rid_to_target[rid] = "xl/" + target if not target.startswith("xl/") else target
    out = {}
    for name, rid in name_to_rid.items():
        if rid in rid_to_target:
            out[name] = rid_to_target[rid]
    return out


# Allow minor WHO naming changes: strip + lower match; try preferred then aliases
SHEET_ALIASES_MORTALITY = ("avail_mortality", "mortality", "mort_avail")
SHEET_ALIASES_POPULATION = ("avail_pop", "population", "pop_avail")


def _get_sheet_path(
    sheet_paths: dict[str, str], preferred_and_aliases: tuple[str, ...]
) -> str | None:
    """Return path for first matching sheet name (strip + lower); None if no match."""
    norm = {k.strip().lower(): v for k, v in sheet_paths.items()}
    for name in preferred_and_aliases:
        key = name.strip().lower()
        if key in norm:
            return norm[key]
    return None


def load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    """Load shared strings; return [] if file missing (e.g. workbook with only inline strings)."""
    try:
        ss_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in ss_root.findall(".//main:si", NS):
        t = "".join(elem.text or "" for elem in si.iter() if elem.text)
        out.append(t)
    return out


def _cell_value(c_el: ET.Element, shared_strings: list[str], ns: dict) -> str:
    """Get cell value: shared string (t='s'), inlineStr, or numeric (v)."""
    t = c_el.get("t")
    v_el = c_el.find("main:v", ns)
    val = (v_el.text or "").strip() if v_el is not None else ""
    if t == "s" and val.isdigit():
        idx = int(val)
        if 0 <= idx < len(shared_strings):
            return shared_strings[idx]
        return val
    if t == "inlineStr":
        is_el = c_el.find("main:is", ns)
        if is_el is not None:
            t_el = is_el.find("main:t", ns)
            if t_el is not None and t_el.text:
                return (t_el.text or "").strip()
            return "".join(elem.text or "" for elem in is_el.iter() if elem.text)
    return val


def sheet_to_rows(
    z: zipfile.ZipFile,
    sheet_path: str,
    shared_strings: list[str],
    header_row_1based: int,
) -> list[dict[int, str]]:
    """Return list of row dicts: col_index -> cell value (string)."""
    root = ET.fromstring(z.read(sheet_path))
    rows_el = root.findall(".//main:row", NS)
    out = []
    for row_el in rows_el:
        r_attr = row_el.get("r")
        r_num = int(r_attr) if r_attr and r_attr.isdigit() else len(out) + 1
        cells = {}
        for c in row_el.findall("main:c", NS):
            ref = c.get("r") or ""
            col = col_letter_to_i(ref)
            val = _cell_value(c, shared_strings, NS)
            cells[col] = val
        out.append((r_num, cells))
    return [cells for r_num, cells in out if r_num > header_row_1based]


def _safe_int(s: str) -> int | None:
    """Parse string to int; handles '101', '101.0', ' 101 '."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def parse_mortality_sheet(
    z: zipfile.ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> set[tuple[str, str, int]]:
    """Return set of (country_code, country_name, year) for List=101 (ICD-10)."""
    # Cols A=code, B=name, E=Year, F=List
    rows = sheet_to_rows(z, sheet_path, shared_strings, header_row_1based=8)
    out = set()
    for cells in rows:
        list_int = _safe_int(cells.get(5, ""))  # F = 5
        if list_int != LIST_101:
            continue
        code = (cells.get(0) or "").strip()
        name = (cells.get(1) or "").strip()
        year = _safe_int(cells.get(4, ""))  # E = 4
        if year is None or not code or not name:
            continue
        out.add((code, name, year))
    return out


def parse_population_sheet(
    z: zipfile.ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> set[tuple[str, str, int]]:
    """Return set of (country_code, country_name, year)."""
    rows = sheet_to_rows(z, sheet_path, shared_strings, header_row_1based=8)
    out = set()
    for cells in rows:
        code = (cells.get(0) or "").strip()
        name = (cells.get(1) or "").strip()
        year = _safe_int(cells.get(4, ""))
        if year is None or not code or not name:
            continue
        out.add((code, name, year))
    return out


def max_consecutive_years(years: list[int]) -> int:
    if not years:
        return 0
    s = sorted(set(years))
    best = 1
    cur = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1] + 1:
            cur += 1
        else:
            cur = 1
        best = max(best, cur)
    return best


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    raw_dir = repo / "RAW_DATA"
    out_dir = repo / "DATA_PROCESSED"
    xlsx = raw_dir / "AVAILABILITY_list_ctry_years_feb2025.xlsx"
    if not xlsx.exists():
        print(f"Missing {xlsx}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(xlsx, "r") as z:
        sheet_paths = get_sheet_paths(z)
        mort_path = _get_sheet_path(sheet_paths, SHEET_ALIASES_MORTALITY)
        pop_path = _get_sheet_path(sheet_paths, SHEET_ALIASES_POPULATION)
        if not mort_path or not pop_path:
            print(
                "Missing sheet paths: need one of %s and one of %s. Got: %s"
                % (SHEET_ALIASES_MORTALITY, SHEET_ALIASES_POPULATION, list(sheet_paths.keys())),
                file=sys.stderr,
            )
            return 1
        shared_strings = load_shared_strings(z)
        mortality_set = parse_mortality_sheet(z, mort_path, shared_strings)
        population_set = parse_population_sheet(z, pop_path, shared_strings)

    # All (country_code, country_name, year) in audit window
    all_cy = set()
    for code, name, year in mortality_set:
        if AUDIT_YEAR_MIN <= year <= AUDIT_YEAR_MAX:
            all_cy.add((code, name, year))
    for code, name, year in population_set:
        if AUDIT_YEAR_MIN <= year <= AUDIT_YEAR_MAX:
            all_cy.add((code, name, year))

    # Build rows for availability table
    rows_avail = []
    for code, name, year in sorted(all_cy, key=lambda x: (x[1], x[2])):
        mort = (code, name, year) in mortality_set
        pop = (code, name, year) in population_set
        included = mort and pop and (AUDIT_YEAR_MIN <= year <= AUDIT_YEAR_MAX)
        rows_avail.append(
            {
                "country_code": code,
                "country": name,
                "year": year,
                "mortality_available": mort,
                "population_available": pop,
                "included": included,
            }
        )

    # Add n_consecutive_years and in_high_quality_subset per (country, year)
    # Per-country included years
    country_included_years: dict[tuple[str, str], list[int]] = {}
    for r in rows_avail:
        if not r["included"]:
            continue
        key = (r["country_code"], r["country"])
        country_included_years.setdefault(key, []).append(r["year"])

    for r in rows_avail:
        key = (r["country_code"], r["country"])
        years = country_included_years.get(key, [])
        n_consec = max_consecutive_years(years) if r["included"] else 0
        r["n_consecutive_years"] = n_consec
        r["in_high_quality_subset"] = r["included"] and (n_consec >= CONSECUTIVE_YEARS_HQ)

    # Write country_year_availability.csv (all in audit window with both flags)
    avail_path = out_dir / "country_year_availability.csv"
    with open(avail_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "country_code",
                "country",
                "year",
                "mortality_available",
                "population_available",
                "included",
                "n_consecutive_years",
                "in_high_quality_subset",
            ],
        )
        w.writeheader()
        w.writerows(rows_avail)
    print(f"Wrote {avail_path} ({len(rows_avail)} rows)")

    # stage0_included_country_years.csv
    included_rows = [r for r in rows_avail if r["included"]]
    inc_path = out_dir / "stage0_included_country_years.csv"
    with open(inc_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "country_code",
                "country",
                "year",
                "mortality_available",
                "population_available",
                "included",
                "n_consecutive_years",
                "in_high_quality_subset",
            ],
        )
        w.writeheader()
        w.writerows(included_rows)
    print(f"Wrote {inc_path} ({len(included_rows)} rows)")

    # stage0_high_quality_subset.csv
    hq_rows = [r for r in rows_avail if r["in_high_quality_subset"]]
    hq_path = out_dir / "stage0_high_quality_subset.csv"
    with open(hq_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "country_code",
                "country",
                "year",
                "mortality_available",
                "population_available",
                "included",
                "n_consecutive_years",
                "in_high_quality_subset",
            ],
        )
        w.writeheader()
        w.writerows(hq_rows)
    print(f"Wrote {hq_path} ({len(hq_rows)} rows)")

    # Optional manifest
    manifest_path = out_dir / "stage0_manifest.yml"
    manifest_lines = [
        "# Stage 0 audit universe manifest (produced by pipeline Stage 2)",
        "data_source: WHO Mortality Database — Availability file (Feb 2025)",
        "source_file: AVAILABILITY_list_ctry_years_feb2025.xlsx",
        "audit_window: [2000, 2021]",
        "list_filter: 101",
        "audit_universe_definition: mortality_available(List=101) AND population_available",
        "inclusion_rule: mortality_available (List=101) and population_available, year in 2000–2021",
        "high_quality_rule: included and >= %s consecutive years in 2000–2021" % CONSECUTIVE_YEARS_HQ,
        "column_assumption: mortality sheet A=country_code, B=country_name, E=year, F=list; population sheet A=country_code, B=country_name, E=year (if WHO changes layout, update script).",
        "outputs:",
        "  - country_year_availability.csv",
        "  - stage0_included_country_years.csv",
        "  - stage0_high_quality_subset.csv",
    ]
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(manifest_lines) + "\n")
    print(f"Wrote {manifest_path}")

    # One-line summary for reviewers (reproducible from CSV; reuse country_included_years)
    n_included = len(included_rows)
    n_countries = len(country_included_years)
    years_per_country = [len(years) for years in country_included_years.values()]
    min_years = min(years_per_country) if years_per_country else 0
    max_years = max(years_per_country) if years_per_country else 0
    print(
        f"Stage 0 summary: {n_included} country-years across {n_countries} countries "
        f"(min years per country = {min_years}, max = {max_years}). See stage0_included_country_years.csv."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
