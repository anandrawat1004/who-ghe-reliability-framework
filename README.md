# Auditing the Architecture of Global Health Estimates

DOI: https://doi.org/10.5281/zenodo.19545271

## Overview

This repository provides a **reproducible diagnostic framework** to audit divergence between **reported mortality** (CRVS, via the WHO Mortality Database) and **estimated mortality** (WHO Global Health Estimates, GHE) where both exist. It operationalises a reliability-oriented audit by computing:

- bias/divergence signals between reported and estimated all-cause deaths
- an **Artificial Smoothness Index (ASI)** to detect structural smoothness differences in time series
- a **volatility–divergence matrix** (quadrants Q1–Q4)
- a **reliability lens** (tiers A–D) that can be communicated and cited

The accompanying white paper (PDF) is included under `WHITEPAPER/` and is the version deposited on Zenodo.

## Key contributions

- **Audit universe framework**: explicit inclusion/exclusion rules and join schema for CRVS–GHE comparison
- **Bias/divergence signals**: transparent country- and year-level divergence metrics
- **Artificial Smoothness Index (ASI)**: a reproducible smoothness diagnostic on log-deaths
- **Volatility matrix (Q1–Q4)**: a descriptive volatility × divergence regime classification
- **Reliability tier (A–D)**: a rule-based synthesis that supports “use with caution” communication

## What this DOES

- **Diagnostic framework** for interpretability and reliability signals when reported and estimated series coexist
- **Reproducible pipeline** (Stages 2–7) to recreate features, QA reports, figures, and the reliability lens
- **Data reliability lens** intended for transparent reporting, governance dialogue, and research reuse

## What this DOES NOT do

- **No causal claims**: diagnostics are descriptive and non-inferential
- **No policy recommendations**
- **No DALY/YLL/YLD analysis** (v1.0)
- **All-cause mortality only** (v1.0; cause-specific extensions are future work)

## Repository structure

This public GitHub repo is intentionally lightweight (no raw WHO datasets; no large parquets). The full reproducible outputs and the manuscript are available via Zenodo.

- `scripts/`: pipeline stages (audit universe → CRVS → GHE → join → features → reliability lens → figures)
- `configs/`: constants/parameters (including default \(T=5\) consecutive years) and configuration notes
- `METHODOLOGY/`: documentation (inclusion rules, join schema, Stage 6 methods snippet, Stage 7 tier logic)
- `WHITEPAPER/main_draft.pdf`: final white paper PDF (Zenodo-deposited)
- `sample_outputs/`: small examples for quick inspection
  - `reliability_lens_sample.csv`: a tiny sample of the reliability lens output
  - `example_figures.png`: an example figure asset
- `requirements.txt`: Python dependencies
- `run_all.sh`: repository-root entry point (calls `scripts/run_all.sh`)
- `RELEASE_NOTES_v1.0.md`: release notes for v1.0
- `LICENSE`: MIT license

## How to run

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install -r requirements.txt

chmod +x run_all.sh scripts/run_all.sh
./run_all.sh
```

Notes:

- `scripts/run_all.sh` uses **relative paths only**.
- Stage 4B (GHE OData) requires network access; if it fails, earlier cached outputs may still allow downstream stages.
- You must supply the WHO input files locally (see the methods docs and `data_manifest.yml` for expected inputs). This repository **does not redistribute** raw WHO datasets.

## Data sources

- **WHO Mortality Database** (CRVS): ICD-10 (List 101), availability snapshot (e.g. Feb 2025)
- **WHO Global Health Estimates (GHE)**: country-level all-cause deaths (2000–2021; release 2021)

Use of WHO data is subject to WHO terms of use.

## Disclaimer

This work is an independent research effort and does not represent the views, decisions, or policies of the World Health Organization (WHO) or any affiliated institution.

## Citation

Rawat, A. (2026). Auditing the Architecture of Global Health Estimates: Bias, Artificial Smoothness, and a Reliability Lens (Version 1.0). Zenodo. https://doi.org/10.5281/zenodo.19545271

