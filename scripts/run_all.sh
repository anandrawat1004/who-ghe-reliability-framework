#!/usr/bin/env bash
# Full pipeline: Stage 2 (audit universe) through Stage 7 (reliability lens).
# Run from repository root. Uses relative paths only.
#
# Recommended:
#   python3 -m venv .venv
#   source .venv/bin/activate   # Windows: .venv\Scripts\activate
#   pip install -r requirements.txt
#   ./run_all.sh
#
# Or: bash scripts/run_all.sh
#
# Stage 4B (GHE OData) requires network; failures are non-fatal (|| true).

set -e
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
fi

mkdir -p DATA_PROCESSED FEATURES REPORTS ARTIFACTS WHITEPAPER FIGURES MAPPINGS

echo "=== WHO/GHE audit pipeline (using: $PYTHON) ==="
echo "Stage 0–1: Identity and raw data (see README)."
echo "Stage 2: Audit universe..."
$PYTHON scripts/stage2_audit_universe.py
echo "Stage 3: CRVS layer..."
$PYTHON scripts/stage3_crvs_reported.py
echo "Stage 4A: GHE global snapshot..."
$PYTHON scripts/stage4a_ghe_global_snapshot.py
echo "Stage 4B: GHE country annual (network)..."
$PYTHON scripts/stage4b_ghe_country_odata.py || true
echo "Country mapping (if missing)..."
$PYTHON scripts/build_country_mapping.py 2>/dev/null || true
echo "Stage 5: Join reported vs estimated..."
$PYTHON scripts/stage5_join_reported_estimated.py || true
echo "Stage 6.0: Analysis panel..."
$PYTHON scripts/stage6_0_build_panel.py || true
echo "Stage 6.1: Bias signals..."
$PYTHON scripts/stage6_1_bias_signals.py || true
echo "Stage 6.2: Artificial Smoothness Index..."
$PYTHON scripts/stage6_2_asi.py || true
echo "Stage 6.3: Volatility matrix..."
$PYTHON scripts/stage6_3_volatility_matrix.py || true
echo "Stage 7: Reliability lens..."
$PYTHON scripts/stage7_reliability_lens.py || true
echo "Figures (publication, 300 DPI)..."
MPLCONFIGDIR="${MPLCONFIGDIR:-$PWD/FIGURES/.mplconfig}" $PYTHON scripts/figures_generate.py || true
echo "Done."
