# Release Notes - v1.0 (2026)

## Data Sources

* WHO Mortality Database (CRVS), availability snapshot: Feb 2025
* WHO Global Health Estimates (GHE), release: 2021

## Scope

* All-cause mortality only (v1)
* Years: 2000–2021
* 7-country pilot (time-series eligible subset)

## Methods

* T = 5 consecutive years (default)
* Sensitivity: T ∈ {3, 5, 8}
* Metrics:

  * Bias / divergence
  * Artificial Smoothness Index (ASI)
  * Volatility–divergence matrix

## Outputs

* FEATURES/
* ARTIFACTS/reliability_lens.csv
* ARTIFACTS/country_cards/
* REPORTS/

## Exclusions

* No DALY/YLL/YLD in v1
* No cause-specific analysis beyond all-cause

## Reproducibility

* `run_all.sh` at repository root (or `scripts/run_all.sh`) executes the full pipeline
* Python environment via `requirements.txt`

## Version Control

* **Zenodo:** https://doi.org/10.5281/zenodo.19545271  
* Git commit hash: **bc4f6db** (initial v1.0 source snapshot: code, configs, methodology, white paper draft, figures; large raw WHO inputs not in git). For your checkout, run `git rev-parse HEAD`.

## Notes

This version is a pilot diagnostic framework and does not provide policy evaluation or causal inference.
