#!/usr/bin/env bash
# Profile a dataset and return structured results
# Usage: profile.sh <dataset-path> [--format markdown|json|kitty]

set -e

DATASET_PATH="${1:-}"
FORMAT="${2:-markdown}"

if [[ -z "$DATASET_PATH" ]]; then
    echo "Usage: profile.sh <dataset-path> [--format markdown|json|kitty]" >&2
    exit 1
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
uv run python -m dex.mcp_app profile "$DATASET_PATH" --format "$FORMAT"
