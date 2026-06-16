#!/usr/bin/env python3
"""prune.py <folder> — delete images not referenced in any HTML/CSS/JS."""
import glob, os, re, sys

ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
ref_re = re.compile(r'(?:\.\./)?images/([^"\')\s,]+\.(?:webp|avif|svg|jpe?g|png|gif))', re.I)
present = {os.path.basename(p) for p in glob.glob(f"{ROOT}/images/*") if os.path.isfile(p)}
ref = set()
for f in (glob.glob(f"{ROOT}/**/*.html", recursive=True)
          + glob.glob(f"{ROOT}/css/*.css") + glob.glob(f"{ROOT}/js/*.js")):
    ref |= {os.path.basename(m) for m in ref_re.findall(open(f, encoding="utf-8", errors="ignore").read())}
unused = sorted(present - ref)
for u in unused:
    os.remove(f"{ROOT}/images/{u}")
print(f"  pruned {len(unused)} unused images ({len(present) - len(unused)} kept)")
