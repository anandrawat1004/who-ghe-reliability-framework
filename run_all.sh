#!/usr/bin/env bash
# Repository-root entry point for the full pipeline (Stages 2–7).
# Relative paths only. Equivalent to: bash scripts/run_all.sh
set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
exec bash "$REPO_ROOT/scripts/run_all.sh"
