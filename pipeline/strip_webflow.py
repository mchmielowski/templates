"""
strip_webflow.py <folder> [--apply] — remove the visible WORD "Webflow" from
HTML *text*, safely, across every .html under <folder> (recurses subfolders).

Pure-deletion + cleanup mode: deletes the word and tidies the orphaned spacing /
"X" connectors it leaves behind (e.g. "Figma X Webflow X GSAP" -> "Figma X GSAP").

SAFE BY CONSTRUCTION — it never touches load-bearing code:
  * <script>...</script> and <style>...</style> bodies are extracted to
    placeholders before any edit, so window.Webflow / Webflow.push survive intact.
  * Inside tags, only human-visible attributes are cleaned
    (content, alt, aria-label, placeholder, title). Code attributes that may hold
    the literal value "Webflow" (id, for, name, data-name, class) are left alone,
    so label<->input pairing and the animation engine's hooks stay consistent.
  * w-* classes and data-wf-* attributes are not the literal word "Webflow" and
    are never matched anyway.

Without --apply it only reports per-file counts + a sample diff. With --apply it
rewrites the files in place. Run pipeline/qa.py afterwards.
"""
import os, re, sys, glob

ROOT = os.path.abspath(sys.argv[1])
APPLY = "--apply" in sys.argv

WORD = re.compile(r"Webflow", re.I)
# human-visible attributes whose values are safe to clean
VISIBLE_ATTRS = ("content", "alt", "aria-label", "placeholder", "title")

SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)


def clean_core(core):
    """Delete the word and tidy what it leaves behind, on a tag-free string."""
    # 1) delete the word together with an adjacent " X " connector, both orders
    core = re.sub(r"\s*\b[Xx×]\b\s*Webflow\b", "", core, flags=re.I)
    core = re.sub(r"\bWebflow\b\s*\b[Xx×]\b\s*", "", core, flags=re.I)
    # 2) delete any remaining bare occurrences
    core = WORD.sub("", core)
    # 3) tidy spacing the deletion left behind
    core = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", core)  # collapse only interior
                                                          # runs (keep indentation)
    core = re.sub(r"[ \t]+([.,;:!?])", r"\1", core)      # " ." -> "."
    core = re.sub(r"\(\s*\)", "", core)            # empty "()"
    core = re.sub(r"^[\s.,;:·|/–—-]+", "", core)  # leading orphan punct/sep
    core = re.sub(r"[\s·|/]+$", "", core)     # trailing orphan sep (keep . ! ?)
    return core


def clean_text(s):
    """Clean a text node, preserving its outer indentation whitespace."""
    if not WORD.search(s):
        return s
    lead = re.match(r"\s*", s).group()
    trail = re.search(r"\s*$", s).group()
    core = s[len(lead): len(s) - len(trail)] if trail else s[len(lead):]
    return lead + clean_core(core) + trail


def clean_tag(tag):
    """Clean only the visible-attribute values inside a single tag token."""
    if not WORD.search(tag):
        return tag
    for attr in VISIBLE_ATTRS:
        # handle both double- and single-quoted values (\2 = the matching quote)
        pat = re.compile(r'(\b' + re.escape(attr) + r'\s*=\s*(["\']))(.*?)(\2)', re.I | re.S)
        tag = pat.sub(lambda m: m.group(1) + clean_core(m.group(3)) + m.group(4), tag)
    return tag


def transform(html):
    # protect script/style bodies
    blocks = []
    def stash(m):
        blocks.append(m.group(0))
        return "\x00B%d\x00" % (len(blocks) - 1)
    safe = SCRIPT_STYLE.sub(stash, html)

    # tokenize into tags vs text; clean each appropriately
    out = []
    for tok in re.split(r"(<[^>]*>)", safe):
        if tok.startswith("<") and tok.endswith(">"):
            out.append(clean_tag(tok))
        else:
            out.append(clean_text(tok))
    safe = "".join(out)

    # restore protected blocks
    safe = re.sub(r"\x00B(\d+)\x00", lambda m: blocks[int(m.group(1))], safe)
    return safe


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True))
    total_before = total_after = changed = 0
    sample_shown = False
    for fp in files:
        with open(fp, encoding="utf-8") as fh:
            html = fh.read()
        before = len(WORD.findall(html))
        if before == 0:
            continue
        new = transform(html)
        after = len(WORD.findall(new))
        total_before += before
        total_after += after
        if new != html:
            changed += 1
            rel = os.path.relpath(fp, ROOT)
            print(f"  {rel}: {before} -> {after} remaining")
            if not sample_shown and not APPLY:
                # show a few example deletions for sanity
                a = re.findall(r".{0,30}Webflow.{0,30}", html)[:4]
                for ln in a:
                    print("      - " + ln.strip().replace("\n", " "))
                sample_shown = True
            if APPLY:
                with open(fp, "w", encoding="utf-8") as fh:
                    fh.write(new)
    mode = "APPLIED" if APPLY else "DRY-RUN (no files written; pass --apply)"
    print(f"\n{mode}: {changed} files, {total_before} -> {total_after} 'Webflow' "
          f"in visible text (remaining are inside protected <script>/code attrs).")


if __name__ == "__main__":
    main()
