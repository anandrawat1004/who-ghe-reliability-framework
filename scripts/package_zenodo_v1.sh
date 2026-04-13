#!/usr/bin/env bash
# Build a Zenodo-ready folder + ZIP at repository root.
# Does NOT include RAW_DATA/ or large GHE Excel (obtain separately for full reproduction).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${REPO}/ZENODO_v1.0_bundle"
ZIP="${REPO}/ZENODO_v1.0_bundle.zip"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

copy_if() {
  local src="$1" dest="$2"
  if [ -e "$src" ]; then
    mkdir -p "$(dirname "$dest")"
    cp -R "$src" "$dest"
    echo "OK  $src"
  else
    echo "MISSING (skipped) $src"
  fi
}

echo "=== Packaging Zenodo v1.0 bundle ==="
echo "Output: $OUT_DIR"
echo ""

# --- Required (Zenodo minimum) ---
copy_if "$REPO/WHITEPAPER/main_draft.pdf" "$OUT_DIR/WHITEPAPER/main_draft.pdf"
copy_if "$REPO/ARTIFACTS/reliability_lens.csv" "$OUT_DIR/ARTIFACTS/reliability_lens.csv"
copy_if "$REPO/DATA_PROCESSED/joined_reported_vs_estimated_allcause.parquet" "$OUT_DIR/DATA_PROCESSED/joined_reported_vs_estimated_allcause.parquet"

# --- Manuscript sources ---
copy_if "$REPO/WHITEPAPER/main_draft.md" "$OUT_DIR/WHITEPAPER/main_draft.md"
copy_if "$REPO/WHITEPAPER/main_draft.tex" "$OUT_DIR/WHITEPAPER/main_draft.tex"

# --- Strongly recommended ---
copy_if "$REPO/LICENSE" "$OUT_DIR/LICENSE"
copy_if "$REPO/README.md" "$OUT_DIR/README.md"
copy_if "$REPO/RELEASE_NOTES_v1.0.md" "$OUT_DIR/RELEASE_NOTES_v1.0.md"
copy_if "$REPO/requirements.txt" "$OUT_DIR/requirements.txt"
copy_if "$REPO/run_all.sh" "$OUT_DIR/run_all.sh"
copy_if "$REPO/data_manifest.yml" "$OUT_DIR/data_manifest.yml"
copy_if "$REPO/ZENODO_UPLOAD.md" "$OUT_DIR/ZENODO_UPLOAD.md"

copy_if "$REPO/scripts" "$OUT_DIR/scripts"
copy_if "$REPO/configs" "$OUT_DIR/configs"
copy_if "$REPO/METHODOLOGY" "$OUT_DIR/METHODOLOGY"
copy_if "$REPO/MAPPINGS" "$OUT_DIR/MAPPINGS"

copy_if "$REPO/FIGURES/fig01_pipeline.png" "$OUT_DIR/FIGURES/fig01_pipeline.png"
copy_if "$REPO/FIGURES/fig02_country_comparison.png" "$OUT_DIR/FIGURES/fig02_country_comparison.png"
copy_if "$REPO/FIGURES/fig03_volatility_matrix.png" "$OUT_DIR/FIGURES/fig03_volatility_matrix.png"
copy_if "$REPO/FIGURES/fig04_tiers.png" "$OUT_DIR/FIGURES/fig04_tiers.png"
copy_if "$REPO/FIGURES/figure_plan.md" "$OUT_DIR/FIGURES/figure_plan.md"

copy_if "$REPO/FEATURES" "$OUT_DIR/FEATURES"
copy_if "$REPO/REPORTS" "$OUT_DIR/REPORTS"
copy_if "$REPO/ARTIFACTS/country_cards" "$OUT_DIR/ARTIFACTS/country_cards"
copy_if "$REPO/ARTIFACTS/dataset_card.md" "$OUT_DIR/ARTIFACTS/dataset_card.md"

# Other processed tables (optional but useful)
for f in "$REPO"/DATA_PROCESSED/*.parquet; do
  [ -e "$f" ] || continue
  copy_if "$f" "$OUT_DIR/DATA_PROCESSED/$(basename "$f")"
done

# Manifest for Zenodo curators / users
MANIFEST="$OUT_DIR/ZENODO_BUNDLE_README.txt"
{
  echo "WHO/GHE audit — Zenodo bundle v1.0 (2026)"
  echo "Generated: $(date -u +%Y-%m-%dT%H:%MZ)"
  echo ""
  echo "REQUIRED FOR MINIMUM ZENODO RECORD:"
  echo "  - WHITEPAPER/main_draft.pdf"
  echo "  - ARTIFACTS/reliability_lens.csv"
  echo "  - DATA_PROCESSED/joined_reported_vs_estimated_allcause.parquet"
  echo ""
  echo "NOT INCLUDED (too large or third-party; add separately if needed):"
  echo "  - RAW_DATA/ (WHO Mortality Database)"
  echo "  - GHE_MODELLED/RAW_DOWNLOAD/ (WHO GHE Excel and caches)"
  echo "  - .venv/"
  echo ""
  echo "Zenodo DOI (v1.0): https://doi.org/10.5281/zenodo.19545271"
} > "$MANIFEST"
echo "Wrote $MANIFEST"

# Remove artefacts that must not ship (Finder cruft, bytecode, LaTeX junk if any)
find "$OUT_DIR" -name '.DS_Store' -delete 2>/dev/null || true
while IFS= read -r -d '' d; do rm -rf "$d"; done < <(find "$OUT_DIR" -type d -name '__pycache__' -print0 2>/dev/null) || true
find "$OUT_DIR" -name '*.pyc' -delete 2>/dev/null || true
while IFS= read -r -d '' d; do rm -rf "$d"; done < <(find "$OUT_DIR" -type d -name '.ipynb_checkpoints' -print0 2>/dev/null) || true
find "$OUT_DIR" \( -name '*.log' -o -name '*.tmp' -o -name '*.aux' -o -name '*.synctex.gz' \) -delete 2>/dev/null || true

# ZIP
rm -f "$ZIP"
( cd "$REPO" && zip -rq "ZENODO_v1.0_bundle.zip" "$(basename "$OUT_DIR")" )
echo ""
echo "Done."
echo "  Folder: $OUT_DIR"
echo "  ZIP:    $ZIP"
echo ""
if [ ! -f "$OUT_DIR/WHITEPAPER/main_draft.pdf" ]; then
  echo "WARNING: main_draft.pdf was not found. Build it (pdflatex) then re-run this script."
  exit 1
fi
if [ ! -f "$OUT_DIR/ARTIFACTS/reliability_lens.csv" ] || [ ! -f "$OUT_DIR/DATA_PROCESSED/joined_reported_vs_estimated_allcause.parquet" ]; then
  echo "WARNING: Run ./run_all.sh (or scripts) to produce missing parquets/CSV, then re-run."
  exit 1
fi
exit 0
