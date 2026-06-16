"""
remove_figma_promo.py <built-dir> [--apply] — remove the "buy the Figma file"
upsell from the templates, surgically (no layout damage).

The upsell is NOT one isolated section — it appears as:
  * a "View Figma File" anchor <a href="...figma.com/design...">…</a> in footers
    and inside sales-button-wrap blocks (next to a legitimate byq.supply button —
    so only the anchor is removed, the wrapper/sibling buttons stay), and
  * a few dedicated promo sections (class "figma-section" / "section_figma",
    the standalone block with the Figma-x-Webflow promo video).

So we remove: (1) every dedicated promo <section>… (balanced), then (2) every
remaining anchor that links to figma.com/design. Footers, CTAs and other buttons
are untouched. Run finalize.py (prune + qa) afterwards.
"""
import os, re, sys, glob

ROOT = os.path.abspath(sys.argv[1])
APPLY = "--apply" in sys.argv

SECTION_OPEN = re.compile(r'<section\b[^>]*class="[^"]*\b(?:figma-section|section_figma)\b[^"]*"[^>]*>', re.I)
# anchor whose opening tag links to a figma.com/design file; anchors don't nest here
FIGMA_ANCHOR = re.compile(r'<a\b[^>]*figma\.com/design[^>]*>.*?</a>\s*', re.I | re.S)


def remove_balanced_sections(html):
    """Remove each <section …figma-section…> … </section> with brace-style depth."""
    out, i, removed = [], 0, 0
    while True:
        m = SECTION_OPEN.search(html, i)
        if not m:
            out.append(html[i:]); break
        out.append(html[i:m.start()])
        depth = 0
        for t in re.finditer(r'<(/?)section\b', html[m.start():]):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = html.index('>', m.start() + t.end()) + 1
                # also swallow trailing whitespace/newline
                while end < len(html) and html[end] in " \t":
                    end += 1
                if end < len(html) and html[end] == "\n":
                    end += 1
                i = end; removed += 1; break
        else:
            out.append(html[m.start():]); i = len(html); break  # unbalanced: stop
    return "".join(out), removed


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True))
    sec_total = anchor_total = files_changed = 0
    sample = None
    for fp in files:
        html = open(fp, encoding="utf-8").read()
        if "figma.com/design" not in html and "figma-section" not in html and "section_figma" not in html:
            continue
        new, nsec = remove_balanced_sections(html)
        nanch = len(FIGMA_ANCHOR.findall(new))
        new = FIGMA_ANCHOR.sub("", new)
        if new != html:
            sec_total += nsec
            anchor_total += nanch
            files_changed += 1
            if sample is None:
                sample = (os.path.relpath(fp, ROOT), nsec, nanch)
            if APPLY:
                open(fp, "w", encoding="utf-8").write(new)
    mode = "APPLIED" if APPLY else "DRY-RUN (pass --apply)"
    print(f"{mode}: removed {sec_total} promo sections + {anchor_total} Figma-file "
          f"anchors across {files_changed} files.")
    if sample:
        print(f"  e.g. {sample[0]}: {sample[1]} section(s), {sample[2]} anchor(s)")


if __name__ == "__main__":
    main()
