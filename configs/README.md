# Configs

**`constants.py`** — Pipeline thresholds in one place.

- **CONSECUTIVE_YEARS_HQ** (Stage 0): minimum consecutive years for “high-quality subset” (default 3).
- **CONSECUTIVE_YEARS_TS** (Stage 6): minimum consecutive years for time-series feature computation (ASI, volatility, etc.); default 5; sensitivity T ∈ {3, 5, 8}.

Stage 2 uses its own local constant for HQ; Stage 6 (and any report) should import from here for T so the paper can state “T = 5, sensitivity T ∈ {3, 5, 8}”.
