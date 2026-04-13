#!/usr/bin/env bash
# Optional full regeneration test (destructive to derived outputs).
# Usage:
#   DRY_RUN_DELETE=1 bash scripts/reproducibility_dry_run.sh
#
# When DRY_RUN_DELETE=1, removes DATA_PROCESSED/*.parquet, FEATURES/*.parquet,
# ARTIFACTS/reliability_lens.csv, ARTIFACTS/country_cards/*.md (not raw inputs).
# Then runs the full pipeline. Requires RAW_DATA/ and GHE inputs in place.

set -e
cd "$(dirname "$0")/.."

if [ "${DRY_RUN_DELETE}" = "1" ]; then
  echo "DRY_RUN_DELETE=1: removing derived parquet and lens outputs..."
  rm -f DATA_PROCESSED/*.parquet FEATURES/*.parquet 2>/dev/null || true
  rm -f ARTIFACTS/reliability_lens.csv ARTIFACTS/dataset_card.md 2>/dev/null || true
  rm -rf ARTIFACTS/country_cards 2>/dev/null || true
  mkdir -p ARTIFACTS/country_cards
else
  echo "Skipping deletion (set DRY_RUN_DELETE=1 to wipe derived outputs first)."
fi

bash scripts/run_all.sh
echo "Dry run complete."
