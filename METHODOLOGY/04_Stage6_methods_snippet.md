# Stage 6 — Methods snippet (for white paper / manuscript)

**Drop-in text for Methods: Forensic framework (bias, ASI, volatility).**

---

## Unit of analysis and eligibility

We built a single analysis panel with one row per (country_code, year, sex, cause_group) with both reported (CRVS) and estimated (GHE) all-cause deaths where available. Time-series features (bias stability, Artificial Smoothness Index, volatility matrix) were computed only for countries with at least T consecutive years in the matched panel; default T = 5 (configs/constants.py). We report stability of rankings and quadrant assignments across T ∈ {3, 5, 8}. Cause scope in v1 is all-cause only.

---

## Bias and divergence (6.1)

We computed pointwise and country-level divergence: absolute and relative gaps (estimated − reported), ratio and log-ratio, mean absolute percent difference (MAPD), and the share of years in which the ratio exceeded a threshold. “Bias stability” was the standard deviation of log-ratio across years. Highest-divergence countries and (where cause mappings exist) most distorted causes are identifiable and reproducible from FEATURES/bias_signals.parquet and REPORTS/04A_bias_signals.md.

---

## Artificial Smoothness Index (6.2)

We quantified “too smooth” behaviour in the estimated series relative to the reported series. For each eligible country we defined the annual series on log(deaths + ε) (deaths, not crude rates; crude rate in the panel is for descriptive checks only). Roughness R is the median of the absolute second discrete differences of this series. We computed R_rep and R_est and defined the Artificial Smoothness Index as ASI = R_rep / (R_est + ε). ASI > 1 indicates that the estimated series is smoother than the reported series (potential artificial smoothing). Results: FEATURES/artificial_smoothness_index.parquet, REPORTS/04B_artificial_smoothness.md.

---

## Volatility–resilience paradox (6.3)

We classified countries into volatility regimes for the reliability lens (Stage 7). For each eligible country we computed: (x-axis) volatility of the reported series = volatility_reported = standard deviation of the first differences of log(deaths); (y-axis) divergence magnitude = median(|log_ratio|) over years. Quadrants were assigned by median split (descriptive partition; not inferential): Q1 High volatility–High divergence (red flag), Q2 High volatility–Low divergence (model tracks chaos), Q3 Low volatility–High divergence (suspicious smoothing / systematic bias), Q4 Low volatility–Low divergence (stable and aligned). We state caveats for small-n and median-split behaviour. Results: FEATURES/volatility_matrix_labels.parquet, REPORTS/04C_volatility_paradox.md.

---

*Aligned with MASTER_ROADMAP_STAGE_WISE_SUMMARY.md Stage 6 and implemented scripts (stage6_0–stage6_3).*
