# byq templates — conversion workflow

Workspace for turning Webflow exports into clean, publish-ready, AI-friendly HTML kits
at scale. Lives at `~/byq-templates/` (deliberately **outside** Downloads).

## Directory layout

```
~/byq-templates/
├─ pipeline/        the tooling (scripts) — the only thing you edit
├─ exports/         unzipped raw Webflow exports — SOURCE, never modified
├─ built/           processed, publish-ready output — one folder per template
└─ reports/         batch reports + run logs
```

Raw `.webflow.zip` exports stay in `~/Downloads/drive-download-…/`; `ingest.py` unzips
them into `exports/`.

## The three stages

### 1. Ingest (unzip)  →  `exports/`
```bash
python3 pipeline/ingest.py exports ~/Downloads/drive-download-20260614T160230Z-3-00*
```

### 2. Deterministic pass (automated, unattended)  →  `built/`
The ~80% that's identical for every export: strip attribution, prettify HTML,
normalize CSS tokens, rename engine files, vendor jQuery/GSAP locally, swap CDNs,
rebrand, drop dead vars, **reconcile broken image filenames**, localize external CDN
images, remove the byq demo overlay, remove empty-states, fill empty *text*, generate
the AI guide. Then QA each.
```bash
python3 pipeline/batch.py exports built      # parallel; writes reports/batch-report.txt
```
Or both stages at once, overnight:
```bash
bash pipeline/overnight.sh   > reports/overnight.log 2>&1 &
```

QA sorts every template into:
- **CLEAN** — publish-ready as-is.
- **ADAPTIVE** — deterministically clean, but has empty CMS / placeholder images that
  need the content pass (stage 3).
- **HARD** — a real failure (a new Webflow quirk to fix in `build.py`). Should be rare.

### 3. Adaptive pass (agent per template)  →  content + images
Each built template contains a `CLAUDE.md` describing its structure. For every
ADAPTIVE template, run one agent to fill real content and pick fitting images:
```bash
cd built/<template>
claude -p "Following CLAUDE.md: replace sample/empty copy with realistic content that
           fits this template's theme, and give every card/listing a fitting image
           from /images. Don't touch js/main.js or the data-w-id attributes."
```
This parallelizes — one agent per template. Then finalize (prune unused images + QA):
```bash
python3 pipeline/finalize.py built/<template>
```

## Per-template tools
`build.py` · `qa.py` · `prune.py` · `finalize.py` · `gen_ai_guide.py` ·
`ingest.py` · `batch.py` · `overnight.sh`

## When a new HARD failure appears
It means a template has a Webflow quirk the deterministic pass doesn't handle yet.
Fix it once in `build.py` (or add a class to `DEMO_OVERLAY_CLASSES`), and it's covered
for every future template. The pipeline was hardened this way on the first 5.

## Prerequisites
Python 3 · Node (for `npx prettier`) · network (to vendor jQuery/GSAP & localize images).
```
