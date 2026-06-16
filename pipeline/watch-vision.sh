#!/usr/bin/env bash
# Live progress meter for the vision-curation workflow. Run in a terminal:
#   bash ~/byq-templates/pipeline/watch-vision.sh
# Ctrl-C to stop. Counts templates whose finalize.py printed "✓ CLEAN ... (N pages)".
SUB="/Users/marcinchmielowski/.claude/projects/-Users-marcinchmielowski-Downloads-nerdstack-template-webflow/109fc4c4-3ac7-4e12-bfb9-42d556ea4ccb/subagents/workflows"
TOTAL="${1:-39}"
while true; do
  DIR=$(ls -dt "$SUB"/wf_* 2>/dev/null | head -1)
  done=$(grep -aohE '"status"[[:space:]]*:[[:space:]]*"CLEAN"' "$DIR"/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
  agents=$(ls "$DIR"/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
  bar=$(printf '%*s' "$done" '' | tr ' ' '#')
  clear
  echo "  VISION CURATION — live   ($(date +%H:%M:%S))"
  echo "  run: $(basename "$DIR")"
  echo
  printf "  done:   %2s / %s  [%s]\n" "$done" "$TOTAL" "$bar"
  echo "  agents spawned this run: $agents"
  echo
  echo "  (Ctrl-C to stop · refreshes every 12s)"
  sleep 12
done
