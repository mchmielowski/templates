# byq.supply — Webflow → clean HTML template library

Converts byq.supply's Webflow template exports into **clean, self-contained, AI-ready,
sellable HTML/CSS/JS templates** — for customers who vibe-code (Cursor, Claude Code).
This repo tracks the processed output + the pipeline that produces it.

> **New session? Read this whole file first** — it's the source of truth for what's
> done, what's left, and how to continue.

---

## Current status (63 templates)

All 63 live in `built/<Template>/` and pass QA.

| Aspect | State |
| --- | --- |
| De-Webflowed *visible branding* (attribution, emoji tokens, demo overlay, "Webflow" word, file renames) | ✅ all 63 |
| Webflow *runtime markers* (`data-w-id`, `w-*`, `data-wf-page`) | ⚠️ **retained on purpose** — `js/main.js` IS the IX2 interactions engine; removing them breaks every animation/nav/slider (see each CLAUDE.md). Not a leak that can be stripped without re-authoring all motion in GSAP. |
| Zero external requests (jQuery + GSAP + **fonts** vendored locally; dead Google-Fonts preconnects removed) | ✅ all 63 — `clean_leftovers.py` |
| 401 password page (dead `/.wf_auth` action + unrendered `<%WF_FORM_VALUE%>` tokens neutralized) | ✅ all 63 — `clean_leftovers.py` |
| Content filled (CMS cards, listings) with realistic on-theme copy | ✅ all 63 |
| Placeholder/lorem text removed (except intentional `style-guide.html` specimens) | ✅ all 63 |
| Blank `<img src="">` filled | ✅ all 63 (239 fixed) |
| Page-screenshots removed from content (webp/png/avif/jpeg · HTML + CSS) | ✅ common cases all 63 |
| **Vision image curation** (images matched to topics by *seeing* them) | ⚠️ ~52/63 (see below) |
| QA CLEAN (`pipeline/qa.py`) | ✅ 63/63 |
| Pushed to GitHub | ✅ (videos excluded — see Git notes) |

### ⚠️ Known remaining work (the honest list)
1. **Screenshot long-tail** — a few *composite/montage* screenshots (e.g. `Sections.webp`)
   and *nav-dropdown page-preview* screenshots still appear in **some** templates. These
   are square/odd-shaped or used site-wide, so dimension/filename detection can't catch
   them — **only an eyes-on vision pass can.** `Halden Miller`'s `Sections.webp` was fixed
   manually as an example.
2. **Thorough vision sweep on 12 featured templates was started then stopped** (platform
   throttling). Run: `wf_bd176aff-469`. Resume it **off-peak** when the API isn't
   overloaded: `Workflow({scriptPath: ".../vision-thorough-featured-wf_bd176aff-469.js", resumeFromRunId: "wf_bd176aff-469"})`.
3. **Per-template buyer config (normal for any template, documented in each CLAUDE.md):**
   forms have no `action` (need a handler like Formspree); `og:image` may point to an
   external URL (buyer sets their own).
4. **Content/images are AI-generated** — strong, but a human spot-check per template is
   the right final gate before listing.

---

## Directory layout (workspace = repo root `~/byq-templates`)

```
pipeline/   the conversion + QA scripts (tracked)
built/      processed, publish-ready templates — one folder per template (tracked)
exports/    raw unzipped Webflow exports (SOURCE, git-ignored)
reports/    batch reports + run logs (logs git-ignored)
```

## Pipeline scripts (`pipeline/`)
| Script | Purpose |
| --- | --- |
| `ingest.py <exports-dir> <download-dirs…>` | unzip `.webflow` exports into `exports/` |
| `build.py <folder>` | deterministic de-Webflow on one export (rename, tokens, prettify, vendor JS, reconcile broken image names, remove overlay, fill empty text, AI guide) |
| `batch.py <exports> <built>` | run `build.py` + `qa.py` over all, in parallel; writes `reports/batch-report.txt` |
| `qa.py <folder>` | publish-invariant gate → exit 0 CLEAN / 3 needs-content / 1 hard-fail |
| `fix_screenshots.py <folder> [--apply]` | detect & swap page-screenshots/blank `<img>` for content photos (dimension-based, webp/png/avif/jpeg, HTML + CSS) |
| `clean_leftovers.py <dir> [--apply]` | remove non-functional Webflow leftovers safely: dead Google-Fonts preconnect hints (fonts are local), `/.wf_auth` action + `<%WF_FORM_VALUE%>` tokens on the 401 page. Leaves the load-bearing IX2 runtime (`data-w-id`/`w-*`) intact |
| `prune.py <folder>` | delete unreferenced images |
| `finalize.py <folder>` | prune + QA (run after any content pass) |
| `gen_ai_guide.py <folder>` | write per-template `CLAUDE.md` + `.cursorrules` |
| `watch-vision.sh [N]` | live terminal progress meter for a running vision workflow |
| `overnight.sh` | ingest + batch in one unattended run |

## How it was produced (the process)
1. **Deterministic pass** (`build.py`/`batch.py`) — the ~80% identical for every export.
2. **Content pass** — agents filled empty CMS with on-theme copy (ran as background
   Workflows; survived session limits/529s via the resume mechanism).
3. **Vision image curation** — agents that *open and view* images, matching each to its
   slot's topic (Bobolobo proved it; capped-Sonnet version did the bulk).
4. **Screenshot + blank-image fixes** — `fix_screenshots.py`, hardened repeatedly
   (dimension detection → varying sizes → `_1` suffixes → AVIF parsing → CSS backgrounds).
5. **Git** — committed; videos excluded.

## Hard-won gotchas (so we don't relearn them)
- **Don't reinvent Webflow designs in React** — keep the exported CSS, port markup. (An
  early React experiment lives at `~/Downloads/nerdstack-react`; the HTML-kit approach won.)
- **Screenshots hide in many forms:** full-page captures (varying dims per template),
  `_1`-suffixed names, AVIF (needs ISOBMFF `ispe` parse), CSS `background-image`, and
  composite montages/nav-previews (only vision catches these).
- **Agents pick images by filename unless told to *view* them** — that's why a "Food"
  image landed on a "play" post; the vision pass fixes it.
- **Background workflows + resume** are how we beat session limits / 529 overloads — each
  retry caches completed agents and only re-runs the rest. Capped image-viewing on
  **Sonnet** is ~3-5× cheaper/faster than Opus for these passes.

## Git / versioning notes
- Remote: `https://github.com/mchmielowski/templates.git` (branch `main`).
- **`videos/` (5.9 GB) and `exports/` are git-ignored.** Templates fall back to video
  poster frames without the mp4s. To version videos, set up **Git LFS** (needs a paid
  data pack beyond the 1 GB free tier).
- Revert a template: `git checkout <commit> -- "built/<Template>"`.

## Running on a NEW batch of exports
```bash
python3 pipeline/ingest.py exports ~/Downloads/<new-export-dirs>
python3 pipeline/batch.py exports built          # deterministic + QA
# then content + vision Workflows for the adaptive 20% (see process above)
```
