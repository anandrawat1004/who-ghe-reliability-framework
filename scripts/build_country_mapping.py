#!/usr/bin/env python3
"""
Build MAPPINGS/country_numeric_to_iso3.csv from Stage 0 country list.

Reads unique (country_code, country) from stage0_included_country_years.csv,
resolves country name → ISO3 via pycountry (or a small fallback dict), and
writes country_numeric, country_name, iso3. Fill any missing iso3 manually.

Requires: pandas. Optional: pycountry (pip install pyarrow pycountry).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
STAGE0 = _REPO_ROOT / "DATA_PROCESSED" / "stage0_included_country_years.csv"
OUT = _REPO_ROOT / "MAPPINGS" / "country_numeric_to_iso3.csv"

# Fallback when pycountry is missing or name not found (WHO name → ISO3)
NAME_TO_ISO3 = {
    "Andorra": "AND", "United Arab Emirates": "ARE", "Afghanistan": "AFG", "Antigua and Barbuda": "ATG",
    "Albania": "ALB", "Armenia": "ARM", "Angola": "AGO", "Argentina": "ARG", "Austria": "AUT",
    "Australia": "AUS", "Azerbaijan": "AZE", "Bosnia and Herzegovina": "BIH", "Barbados": "BRB",
    "Bangladesh": "BGD", "Belgium": "BEL", "Burkina Faso": "BFA", "Bulgaria": "BGR", "Bahrain": "BHR",
    "Belarus": "BLR", "Belize": "BLZ", "Brunei Darussalam": "BRN", "Bolivia (Plurinational State of)": "BOL",
    "Brazil": "BRA", "Bahamas": "BHS", "Botswana": "BWA", "Canada": "CAN", "Switzerland": "CHE",
    "Chile": "CHL", "China": "CHN", "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB",
    "Cyprus": "CYP", "Czechia": "CZE", "Germany": "DEU", "Denmark": "DNK", "Dominican Republic": "DOM",
    "Ecuador": "ECU", "Egypt": "EGY", "Spain": "ESP", "Estonia": "EST", "Finland": "FIN",
    "France": "FRA", "United Kingdom of Great Britain and Northern Ireland": "GBR", "Georgia": "GEO",
    "Greece": "GRC", "Guatemala": "GTM", "Guyana": "GUY", "Hong Kong": "HKG",
    "Honduras": "HND", "Croatia": "HRV", "Haiti": "HTI", "Hungary": "HUN", "Indonesia": "IDN",
    "India": "IND", "Ireland": "IRL", "Iran (Islamic Republic of)": "IRN", "Iraq": "IRQ",
    "Iceland": "ISL", "Israel": "ISR", "Italy": "ITA", "Jamaica": "JAM", "Jordan": "JOR",
    "Japan": "JPN", "Kazakhstan": "KAZ", "Kenya": "KEN", "Kyrgyzstan": "KGZ", "Cambodia": "KHM",
    "Republic of Korea": "KOR", "Kuwait": "KWT", "Lao People's Democratic Republic": "LAO",
    "Lebanon": "LBN", "Sri Lanka": "LKA", "Lithuania": "LTU", "Luxembourg": "LUX", "Latvia": "LVA",
    "Morocco": "MAR", "Republic of Moldova": "MDA", "Mexico": "MEX", "North Macedonia": "MKD",
    "Malta": "MLT", "Myanmar": "MMR", "Montenegro": "MNE", "Mongolia": "MNG", "Mozambique": "MOZ",
    "Mauritius": "MUS", "Malaysia": "MYS", "Namibia": "NAM", "Nepal": "NPL", "Netherlands": "NLD",
    "Norway": "NOR", "New Zealand": "NZL", "Oman": "OMN", "Panama": "PAN", "Peru": "PER",
    "Philippines": "PHL", "Poland": "POL", "Portugal": "PRT", "Paraguay": "PRY", "Qatar": "QAT",
    "Romania": "ROU", "Russian Federation": "RUS", "Rwanda": "RWA", "Saudi Arabia": "SAU",
    "Sudan": "SDN", "Singapore": "SGP", "Slovenia": "SVN", "Slovakia": "SVK", "Senegal": "SEN",
    "El Salvador": "SLV", "Serbia": "SRB", "Suriname": "SUR", "Sweden": "SWE", "Thailand": "THA",
    "Tajikistan": "TJK", "Turkmenistan": "TKM", "Trinidad and Tobago": "TTO", "Tunisia": "TUN",
    "Turkey": "TUR", "Ukraine": "UKR", "Uruguay": "URY", "United States of America": "USA",
    "Uzbekistan": "UZB", "Venezuela (Bolivarian Republic of)": "VEN", "Viet Nam": "VNM",
    "Yemen": "YEM", "South Africa": "ZAF", "Zambia": "ZMB", "Zimbabwe": "ZWE",
    "San Marino": "SMR", "Seychelles": "SYC", "Syrian Arab Republic": "SYR",
}


def name_to_iso3(name: str) -> str | None:
    n = (name or "").strip()
    if n in NAME_TO_ISO3:
        return NAME_TO_ISO3[n]
    try:
        import pycountry
        c = pycountry.countries.search_fuzzy(n)
        if c:
            return c[0].alpha_3
    except Exception:
        pass
    return None


def main() -> int:
    if not STAGE0.exists():
        print("Missing %s (run Stage 2 first)" % STAGE0, file=sys.stderr)
        return 1

    df = pd.read_csv(STAGE0, dtype={"country_code": str})
    u = df[["country_code", "country"]].drop_duplicates()
    u = u.rename(columns={"country_code": "country_numeric", "country": "country_name"})
    u["iso3"] = u["country_name"].map(name_to_iso3)
    missing = u["iso3"].isna().sum()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    u.to_csv(OUT, index=False)
    print("Wrote %s (%d rows, %d with iso3, %d to fill manually)" % (OUT, len(u), len(u) - missing, missing))
    if missing:
        print("Missing iso3:", u[u["iso3"].isna()]["country_name"].tolist())
    return 0


if __name__ == "__main__":
    sys.exit(main())
