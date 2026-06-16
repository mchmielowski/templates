"""
clean_webflow_css.py <built-dir> [--apply] — remove the remaining lowercase
"webflow" from CSS class names / identifiers, safely.

Three cases (see README):
  1. `.w-webflow-badge` rule blocks  -> DELETE. The badge HTML was already removed
     by build.py, so these rules style nothing (verified: 0 HTML refs).
  2. font-family 'webflow-icons'     -> RENAME to 'ui-icons'. It's a live icon font
     (the [class^="w-icon-"] glyphs), but the family name is an internal CSS-only
     identifier — HTML uses `w-icon-*`, which is untouched. Renamed in both the
     @font-face and the selector that consumes it.
  3. figma-x-webflow / webflow-x-figma class tokens -> RENAME (drop "webflow").
     These are live classes on a promo section, so the SAME rename is applied to
     CSS selectors and HTML class="" attributes to keep them matched.

Without --apply it reports; with --apply it rewrites in place. Run qa.py after.
"""
import os, re, sys, glob

ROOT = os.path.abspath(sys.argv[1])
APPLY = "--apply" in sys.argv

# flat-CSS rule whose selector group mentions .w-webflow-badge (no nested braces)
BADGE_RULE = re.compile(r'[^{}]*\.w-webflow-badge[^{}]*\{[^}]*\}\s*', re.S)


def rename_tokens(text):
    """Class/identifier renames applied identically to CSS and HTML."""
    text = text.replace("webflow-icons", "ui-icons")        # font-family name
    text = text.replace("figma-x-webflow", "figma")          # promo classes
    text = text.replace("webflow-x-figma", "figma")
    return text


def main():
    css_files = glob.glob(os.path.join(ROOT, "**", "*.css"), recursive=True)
    html_files = glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)
    badge_removed = renamed_css = renamed_html = 0

    for fp in css_files:
        txt = open(fp, encoding="utf-8").read()
        new = txt
        n = len(BADGE_RULE.findall(new))
        new = BADGE_RULE.sub("", new)
        before_rename = new
        new = rename_tokens(new)
        if new != txt:
            badge_removed += n
            if before_rename != new:
                renamed_css += 1
            if APPLY:
                open(fp, "w", encoding="utf-8").write(new)

    for fp in html_files:
        txt = open(fp, encoding="utf-8").read()
        if "figma-x-webflow" not in txt and "webflow-x-figma" not in txt:
            continue
        new = rename_tokens(txt)
        if new != txt:
            renamed_html += 1
            if APPLY:
                open(fp, "w", encoding="utf-8").write(new)

    mode = "APPLIED" if APPLY else "DRY-RUN (pass --apply)"
    print(f"{mode}: removed {badge_removed} .w-webflow-badge rule blocks; "
          f"renamed identifiers in {renamed_css} CSS + {renamed_html} HTML files.")


if __name__ == "__main__":
    main()
