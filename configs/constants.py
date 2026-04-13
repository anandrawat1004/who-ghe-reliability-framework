"""
Pipeline constants — single place for thresholds used across stages.

Stage 0 (inclusion): CONSECUTIVE_YEARS_HQ = 3 (high-quality subset).
Stage 6 (time-series features): CONSECUTIVE_YEARS_TS = T; country-years with
  fewer than T consecutive years remain in descriptive comparisons but are
  excluded from ASI, volatility, curvature, change-point computation.
"""

# Stage 0 high-quality subset (≥ this many consecutive years in 2000–2021)
CONSECUTIVE_YEARS_HQ = 3

# Stage 6 time-series eligibility: ≥ T consecutive years required for
# ASI, volatility, curvature, change-point metrics. Default 5; sensitivity 3, 5, 8.
CONSECUTIVE_YEARS_TS = 5

# For sensitivity analyses (document in Methods): T ∈ {3, 5, 8}
CONSECUTIVE_YEARS_TS_SENSITIVITY = (3, 5, 8)

# CRVS List 101 all-cause cause code (confirm from WHO Mortality DB Documentation Annex; commonly 1000)
ALL_CAUSE_CAUSE = 1000
