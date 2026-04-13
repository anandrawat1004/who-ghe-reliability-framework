#!/usr/bin/env bash
# Build WHITEPAPER/main_draft.pdf from main_draft.tex (requires pdflatex).
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO/WHITEPAPER"
if command -v pdflatex >/dev/null 2>&1; then
    pdflatex -interaction=nonstopmode main_draft.tex
    pdflatex -interaction=nonstopmode main_draft.tex
    echo "Built: $REPO/WHITEPAPER/main_draft.pdf"
else
    echo "pdflatex not found. Install TeX Live or MacTeX, or run from WHITEPAPER: pdflatex main_draft.tex"
    exit 1
fi
