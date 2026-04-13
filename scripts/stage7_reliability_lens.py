#!/usr/bin/env python3
"""
Stage 7 — Reliability lens (citable artefact).

Reads FEATURES from Stage 6 (ASI, volatility matrix, bias country-level),
applies transparent tier logic (see METHODOLOGY/05_Stage7_reliability_tier_logic.md),
and writes:
  - ARTIFACTS/reliability_lens.csv (country_code, tier, main_reasons, use_with_caution)
  - ARTIFACTS/country_cards/<ISO3>.md (one-pager per country)
  - ARTIFACTS/dataset_card.md

Tiers: A = robust, B = moderate, C = use with caution, D = high concern.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES = _REPO_ROOT / "FEATURES"
ARTIFACTS = _REPO_ROOT / "ARTIFACTS"
REPORTS = _REPO_ROOT / "REPORTS"

ASI_HIGH = 1.5
ASI_MODERATE = 1.2


def _tier_d(row: pd.Series) -> bool:
    """Tier D: Q1 and ASI > 1.5."""
    return row.get("quadrant") == "Q1" and row.get("asi", 0) > ASI_HIGH


def _tier_c(row: pd.Series) -> bool:
    """Tier C: Q1 or ASI > 1.5 or Q3."""
    return (
        row.get("quadrant") == "Q1"
        or row.get("asi", 0) > ASI_HIGH
        or row.get("quadrant") == "Q3"
    )


def _tier_b(row: pd.Series) -> bool:
    """Tier B: Q2 or (Q4 and (ASI in (1.2,1.5] or high_divergence))."""
    q = row.get("quadrant")
    asi = row.get("asi") or 0
    hd = row.get("high_divergence", False)
    if q == "Q2":
        return True
    if q == "Q4" and (ASI_MODERATE < asi <= ASI_HIGH or hd):
        return True
    return False


def _tier_a(row: pd.Series) -> bool:
    """Tier A: Q4 and ASI <= 1.2 and not high_divergence; ASI must be present."""
    asi = row.get("asi")
    if pd.isna(asi):
        return False
    return (
        row.get("quadrant") == "Q4"
        and asi <= ASI_MODERATE
        and not row.get("high_divergence", True)
    )


def main() -> int:
    asi_path = FEATURES / "artificial_smoothness_index.parquet"
    vol_path = FEATURES / "volatility_matrix_labels.parquet"
    bias_path = FEATURES / "bias_signals.parquet"
    for p in (asi_path, vol_path, bias_path):
        if not p.exists():
            print("Missing %s (run Stage 6)" % p, file=sys.stderr)
            return 1

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "country_cards").mkdir(parents=True, exist_ok=True)

    asi = pd.read_parquet(asi_path)[["country_code", "asi", "n_years"]]
    vol = pd.read_parquet(vol_path)[
        ["country_code", "quadrant", "quadrant_label", "divergence_magnitude", "volatility_reported", "n_years"]
    ]
    bias = pd.read_parquet(bias_path)
    # One row per country (country-level aggregates)
    bias_cols = [c for c in ["country_code", "median_log_ratio", "mapd", "n_years", "bias_stability_std_log_ratio"] if c in bias.columns]
    bias_agg = bias[bias_cols].drop_duplicates(subset=["country_code"], keep="first") if "country_code" in bias.columns else bias[bias_cols]

    df = vol.merge(asi, on="country_code", how="outer", suffixes=("", "_asi"))
    if "n_years_asi" in df.columns:
        df["n_years"] = df["n_years"].fillna(df["n_years_asi"])
        df = df.drop(columns=["n_years_asi"], errors="ignore")
    df = df.merge(bias_agg, on="country_code", how="left")
    # High divergence = above median
    med_d = df["divergence_magnitude"].median()
    df["high_divergence"] = df["divergence_magnitude"] >= med_d

    # Assign tier (first match D -> C -> B -> A)
    tier = []
    reasons = []
    for _, r in df.iterrows():
        reasons_i = []
        if r.get("quadrant") == "Q1":
            reasons_i.append("Q1_high_vol_high_div")
        if (r.get("asi") or 0) > ASI_HIGH:
            reasons_i.append("ASI>1.5")
        elif (r.get("asi") or 0) > ASI_MODERATE:
            reasons_i.append("ASI>1.2")
        if r.get("quadrant") == "Q3":
            reasons_i.append("Q3_low_vol_high_div")
        if r.get("high_divergence"):
            reasons_i.append("high_divergence")
        if r.get("quadrant") == "Q2":
            reasons_i.append("Q2_high_vol_low_div")
        if r.get("quadrant") == "Q4":
            reasons_i.append("Q4_stable_aligned")
        if pd.isna(r.get("asi")) and "asi" in df.columns:
            reasons_i.append("asi_missing")

        if _tier_d(r):
            t = "D"
        elif _tier_c(r):
            t = "C"
        elif _tier_b(r):
            t = "B"
        elif _tier_a(r):
            t = "A"
        else:
            t = "B"  # default moderate if no rule
        tier.append(t)
        reasons.append("; ".join(reasons_i) if reasons_i else "—")

    df["tier"] = tier
    df["main_reasons"] = reasons
    df["use_with_caution"] = df["tier"].isin(["C", "D"])

    lens_cols = ["country_code", "tier", "quadrant", "asi", "divergence_magnitude", "high_divergence", "main_reasons", "use_with_caution", "n_years"]
    lens = df[[c for c in lens_cols if c in df.columns]]
    lens.to_csv(ARTIFACTS / "reliability_lens.csv", index=False)
    print("Wrote %s (%d rows)" % (ARTIFACTS / "reliability_lens.csv", len(lens)))

    # Country cards (one-pager per country)
    for _, r in lens.iterrows():
        cc = str(r["country_code"]).strip()[:3]  # ISO3
        card = [
            "# Country card: %s" % cc,
            "",
            "| Field | Value |",
            "|------|-------|",
            "| **Tier** | %s |" % r["tier"],
            "| **Use with caution** | %s |" % r["use_with_caution"],
            "| **Quadrant** | %s |" % r.get("quadrant", "—"),
            "| **ASI** | %s |" % (round(r["asi"], 3) if pd.notna(r.get("asi")) else "—"),
            "| **Divergence magnitude** | %s |" % (round(r["divergence_magnitude"], 4) if pd.notna(r.get("divergence_magnitude")) else "—"),
            "| **Main reasons** | %s |" % r.get("main_reasons", "—"),
            "| **N years** | %s |" % r.get("n_years", "—"),
            "",
            "See METHODOLOGY/05_Stage7_reliability_tier_logic.md for tier definitions.",
            "",
        ]
        (ARTIFACTS / "country_cards" / ("%s.md" % cc)).write_text("\n".join(card), encoding="utf-8")
    print("Wrote %d country cards to %s" % (len(lens), ARTIFACTS / "country_cards"))

    # Dataset card
    dataset_card = [
        "# Reliability lens — dataset card",
        "",
        "**Purpose:** A third party can use the reliability lens without running the pipeline.",
        "",
        "## Contents",
        "- **reliability_lens.csv**: one row per eligible country; columns: country_code, tier, quadrant, asi, divergence_magnitude, main_reasons, use_with_caution, n_years.",
        "- **country_cards/<ISO3>.md**: one-pager per country with tier, quadrant, ASI, divergence, main_reasons.",
        "",
        "## Tier definitions (v1)",
        "- **A (robust):** Q4, ASI ≤ 1.2, low divergence. Low concern.",
        "- **B (moderate):** Q2 or Q4 with moderate ASI/divergence. Context-dependent.",
        "- **C (use with caution):** Q1 or Q3 or ASI > 1.5. Notable smoothing/divergence.",
        "- **D (high concern):** Q1 and ASI > 1.5. Red-flag volatility and smoothness.",
        "",
        "## How to use",
        "1. For a given country, open **country_cards/<ISO3>.md** or filter **reliability_lens.csv** by country_code.",
        "2. If **use_with_caution** is True, interpret estimates in context and report caveats.",
        "3. Tier logic: METHODOLOGY/05_Stage7_reliability_tier_logic.md.",
        "4. Pipeline: Stage 6 (bias, ASI, volatility) → Stage 7 (this lens).",
        "",
    ]
    (ARTIFACTS / "dataset_card.md").write_text("\n".join(dataset_card), encoding="utf-8")
    print("Wrote %s" % (ARTIFACTS / "dataset_card.md"))

    # QA report
    qa = [
        "# Reliability lens — QA (Stage 7)",
        "",
        "Tier logic: METHODOLOGY/05_Stage7_reliability_tier_logic.md.",
        "",
        "## Outputs",
        "- **ARTIFACTS/reliability_lens.csv**: %d rows" % len(lens),
        "- **ARTIFACTS/country_cards/**: %d one-pagers" % len(lens),
        "- **ARTIFACTS/dataset_card.md**: how to use the lens",
        "",
        "## Tier counts",
        "| Tier | Count |",
        "|------|-------|",
    ]
    for t in ["A", "B", "C", "D"]:
        qa.append("| %s | %d |" % (t, (lens["tier"] == t).sum()))
    qa.append("")
    qa.append("## Use with caution")
    qa.append("- **True:** %d" % lens["use_with_caution"].sum())
    qa.append("- **False:** %d" % (~lens["use_with_caution"]).sum())
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "05_reliability_lens_QA.md").write_text("\n".join(qa), encoding="utf-8")
    print("Wrote %s" % (REPORTS / "05_reliability_lens_QA.md"))

    print("")
    print("Stage 7 summary: %d countries, tiers A=%d B=%d C=%d D=%d" % (
        len(lens),
        (lens["tier"] == "A").sum(),
        (lens["tier"] == "B").sum(),
        (lens["tier"] == "C").sum(),
        (lens["tier"] == "D").sum(),
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
