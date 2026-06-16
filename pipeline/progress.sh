#!/usr/bin/env bash
# Quick progress check for the adaptive content pass. Run anytime.
WS="$(cd "$(dirname "$0")/.." && pwd)"; cd "$WS"
total=0; done=0; pending=()
while IFS= read -r name; do
  [ -z "$name" ] && continue
  d="built/$name"; [ -d "$d" ] || continue
  total=$((total+1))
  if grep -rqlE --include='*.html' 'Sample headline|Section headline|Sample body copy|short sample description|placeholder\.[0-9a-f]+\.svg' "$d" 2>/dev/null; then
    pending+=("$name")
  else
    done=$((done+1))
  fi
done < <(python3 -c "import json;print(chr(10).join(json.load(open('reports/todo.json'))))")
echo "Adaptive content pass:  $done / $total done"
[ ${#pending[@]} -gt 0 ] && printf 'pending: %s\n' "$(IFS=,; echo "${pending[*]}")"
