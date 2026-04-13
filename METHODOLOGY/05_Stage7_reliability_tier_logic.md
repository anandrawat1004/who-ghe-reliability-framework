# Stage 7 — Reliability lens: tier logic (transparent scoring)

**Purpose:** Define how we assign a reliability tier (A/B/C/D) to each country in the lens, so the framework is reproducible and defensible.

**Inputs (from Stage 6 FEATURES):** one row per eligible country from:
- `artificial_smoothness_index.parquet` (asi, n_years)
- `volatility_matrix_labels.parquet` (quadrant Q1–Q4, divergence_magnitude)
- Country-level bias from `bias_signals.parquet` (mapd, median_log_ratio; one row per country)

**Rules (v1, all-cause; descriptive, not inferential):**

1. **Tier D (high concern / fragile)**  
   Quadrant Q1 (high volatility, high divergence) **and** ASI > 1.5.  
   Interpretation: Red-flag volatility and strong artificial smoothness; use with caution.

2. **Tier C (use with caution)**  
   Any of: Quadrant Q1; or ASI > 1.5; or quadrant Q3 (low volatility, high divergence).  
   Interpretation: Notable smoothing and/or systematic divergence; interpret in context.

3. **Tier B (moderate)**  
   Quadrant Q2 (high volatility, low divergence) or (Q4 and (ASI in (1.2, 1.5] or high divergence by median split)).  
   Interpretation: Moderate concern; some smoothing or divergence; context-dependent.

4. **Tier A (robust)**  
   Quadrant Q4 (low volatility, low divergence) **and** ASI ≤ 1.2 **and** divergence below median.  
   Interpretation: Low concern; estimates align with reported; series show plausible volatility.

**Order of application:** Assign the **first** tier whose conditions are met when evaluating in order D → C → B → A (so the most conservative tier wins).

**Thresholds (configurable in script):**
- ASI high: > 1.5  
- ASI moderate: > 1.2  
- High divergence: above median of divergence_magnitude (or mapd) among eligible countries.

**Missing data:** If a country has no ASI (e.g. too few years) but has quadrant/divergence, tier is based on quadrant/divergence only; we flag "asi_missing" in main_reasons.

**Output:** `ARTIFACTS/reliability_lens.csv` (country_code, tier, main_reasons, use_with_caution), plus `ARTIFACTS/country_cards/<ISO3>.md` and `ARTIFACTS/dataset_card.md`.

---

*Aligned with MASTER_ROADMAP_STAGE_WISE_SUMMARY.md Stage 7 and scripts/stage7_reliability_lens.py.*
