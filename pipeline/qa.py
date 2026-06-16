#!/usr/bin/env python3
"""
qa.py <folder> — assert publish invariants. Two buckets:
  HARD     — deterministic-pass failures that must NOT happen (real bugs)
  ADAPTIVE — expected TODOs the content/image agent pass handles (not failures)

Exit: 0 = clean, 3 = clean but needs adaptive pass, 1 = HARD failure.
"""
import glob, os, re, sys

ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
html = glob.glob(f"{ROOT}/**/*.html", recursive=True)
css = glob.glob(f"{ROOT}/css/*.css")
hard, adaptive = [], []


def grep(files, pattern, label, bucket):
    rx = re.compile(pattern)
    hits = [os.path.relpath(f, ROOT) for f in files if rx.search(open(f, encoding="utf-8", errors="ignore").read())]
    if hits:
        bucket.append(f"{label}: {len(hits)} file(s) — e.g. {hits[0]}")


# HARD — must be clean after the deterministic pass
grep(html, r"created in Webflow|name=[\"']generator[\"']", "Webflow attribution", hard)
grep(html, r"www\.webflow\.com", "webflow.com links", hard)
grep(html + css, r"--_[^\s:;,]", "Webflow emoji-prefixed CSS vars", hard)
grep(html, r'class="[^"]*master_sales', "byq demo overlay", hard)
grep(html, r'<img[^>]+src="https?://[^"]*website-files[^"]*\.(svg|png|jpe?g|webp|avif)"', "external Webflow-CDN images", hard)

ref_re = re.compile(r'(?:\.\./)?images/([^"\')\s,]+\.(?:webp|avif|svg|jpe?g|png|gif))', re.I)
nrm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
disk = [os.path.basename(p) for p in glob.glob(f"{ROOT}/images/*") if os.path.isfile(p)]
stem_norms = [nrm(os.path.splitext(f)[0]) for f in disk]
broken = set()
for f in html + css:
    for m in ref_re.findall(open(f, encoding="utf-8", errors="ignore").read()):
        if not os.path.exists(f"{ROOT}/images/{os.path.basename(m)}"):
            broken.add(os.path.basename(m))
# split: a disk candidate exists -> reconcile bug (HARD); none -> missing source (ADAPTIVE)
fixable = {b for b in broken
           if any(n.startswith(nrm(os.path.splitext(b)[0])) for n in stem_norms)}
missing = broken - fixable
if fixable:
    hard.append(f"broken image refs (candidate exists — reconcile bug): {len(fixable)} — e.g. {sorted(fixable)[0]}")
if missing:
    adaptive.append(f"missing source images (not in export — substitute): {len(missing)} — e.g. {sorted(missing)[0]}")
if not os.path.exists(f"{ROOT}/js/main.js"):
    hard.append("js/main.js missing")
if html and not glob.glob(f"{ROOT}/js/*jquery*"):
    hard.append("jQuery not vendored locally")

# ADAPTIVE — expected; the content/image agent pass resolves these
grep(html, r"w-dyn-bind-empty|w-dyn-empty", "empty CMS fields/states", adaptive)
grep(html, r'placeholder\.[0-9a-f]+\.svg|w-dyn-bind-empty', "placeholder images", adaptive)

name = os.path.basename(ROOT.rstrip("/"))
if hard:
    print(f"✗ HARD {name}: {len(hard)} issue(s)")
    for i in hard:
        print(f"    - {i}")
    sys.exit(1)
if adaptive:
    print(f"~ ADAPTIVE {name}: needs content pass ({adaptive[0]})")
    sys.exit(3)
print(f"✓ CLEAN {name} ({len(html)} pages)")
sys.exit(0)
