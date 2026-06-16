# byq template pipeline — Webflow export → clean, AI-ready HTML kit, at scale

Turns a folder of Webflow HTML exports into clean, de-Webflowed, self-contained,
AI-ready templates. Built from the validated Nerdstack conversion.

## The model: deterministic vs. adaptive

| | What | How |
| --- | --- | --- |
| **Deterministic** (~80%) | strip attribution, prettify, normalize CSS tokens, rename engine files, swap jQuery CDN, rebrand, drop dead vars, vendor JS, remove the byq demo overlay, remove empty-states, fill empty *text* fields, generate the AI guide | one script, unattended, runs over all 160 |
| **Adaptive** (~20%) | sample *content* that fits the template, *which* image suits each thumbnail, multiplying CMS cards (class names differ per template) | an **AI agent per template**, or light human input |

The deterministic part is a pure function of the export. The adaptive part needs
judgment per template — which is exactly what an LLM agent does well.

## Commands

```bash
# One template, generic pass (in place):
python3 build.py    /path/to/export

# All templates in a directory, in parallel (copies to <dir>-built, never touches src):
python3 batch.py    ~/byq-exports           # -> ~/byq-exports-built/ + pass/fail report

# After the adaptive content pass on a template, prune unused images + QA:
python3 finalize.py /path/to/built-template

# Just validate the publish invariants (used as the gate):
python3 qa.py       /path/to/built-template
```

## Recommended flow for 160 templates

1. **Export all 160** from Webflow into `~/byq-exports/<template-name>/`.
2. **`python3 batch.py ~/byq-exports`** — every template gets the deterministic
   treatment + a QA report. Templates that are content-complete pass immediately.
3. **Adaptive pass on the ones QA flags** (placeholder images / empty CMS). Each built
   template already contains a `CLAUDE.md` telling an agent exactly how it's structured.
   Run an agent per template, e.g. headless Claude Code:
   ```bash
   cd ~/byq-exports-built/<template>
   claude -p "Following CLAUDE.md: replace the sample copy with realistic content that
              fits this template's theme, and give every card/listing a fitting image
              from /images. Don't touch js/main.js."
   ```
   This parallelizes — one agent per template.
4. **`python3 finalize.py <template>`** on each → prune + QA. Green = publishable.

## Prerequisites
- Python 3, Node (for `npx prettier`), network (to vendor jQuery/GSAP).

## Honest caveats (read before running all 160)
- **Validate on 3–5 diverse templates first.** This was built/tested on one template.
  Webflow projects vary — different card class names, page sets, GSAP plugins, and the
  demo overlay class (`DEMO_OVERLAY_CLASSES` in build.py) may differ. Expect to harden
  the generic steps on the first few, after which most run hands-off.
- **The deterministic pass fills empty *text* with placeholder copy** ("Sample
  headline") so nothing is broken — the adaptive pass replaces it with real content.
- **Image curation is adaptive** — the generic pass leaves Webflow image placeholders,
  and `qa.py` flags them, so you know exactly which templates need the image pass.
- **`og:image` and forms** are left for the buyer to configure (documented in each
  template's README/CLAUDE.md), as with any template.

## Files
- `build.py` — deterministic pipeline for one export
- `batch.py` — run build + qa over a directory, in parallel
- `prune.py` — delete unreferenced images
- `gen_ai_guide.py` — write CLAUDE.md + .cursorrules from the page list
- `finalize.py` — prune + QA (run after the adaptive pass)
- `qa.py` — assert publish invariants (the gate)
