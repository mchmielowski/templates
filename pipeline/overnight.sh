#!/usr/bin/env bash
# Deterministic overnight run: unzip every export, then build + QA all of them.
# Safe & unattended. The adaptive content/image agent pass runs separately after.
set -euo pipefail
WS="$(cd "$(dirname "$0")/.." && pwd)"
PIPE="$WS/pipeline"
DL="${1:-/Users/marcinchmielowski/Downloads}"

echo "[$(date +%H:%M:%S)] ingesting…"
python3 "$PIPE/ingest.py" "$WS/exports" \
  "$DL"/drive-download-20260614T160230Z-3-00*

echo "[$(date +%H:%M:%S)] building + QA…"
python3 "$PIPE/batch.py" "$WS/exports" "$WS/built"
echo "[$(date +%H:%M:%S)] deterministic run complete."
