"""
fix_staging_links.py <built-dir> [--apply] — rewrite dead `*.webflow.io` staging
links (the original author's demo site) to the matching LOCAL page, per template.

Each template is exported with CMS card/detail links pointing at an absolute
Webflow staging URL like:
    href="https://grained-template.webflow.io/blog/some-post"
For a buyer this leaks the origin and sends visitors off-site. The static export
ships a stand-in detail page per collection (detail_<collection>.html), so we map
by the URL's first path segment to a real local page:

    /blog/...      -> detail_blog.html      (falls back to blog.html)
    /product/...   -> detail_product.html   (falls back to product.html)
    /<seg>/...     -> detail_<seg>.html      (falls back to <seg>.html)
    bare domain    -> index.html
    no local match -> "#"

The chosen target must actually EXIST in that template's root (checked per
template), and links are written RELATIVE to each file's own depth, so links in
subfolders (template/, utility/, …) get the right "../" prefix.

Only href="…" values are touched. Without --apply it reports; with --apply it
rewrites in place. Run pipeline/qa.py afterwards.
"""
import os, re, sys, glob

ROOT = os.path.abspath(sys.argv[1])
APPLY = "--apply" in sys.argv

URL = re.compile(r'href="(https?://[a-z0-9-]+\.webflow\.io([^"]*))"', re.I)


def target_for(path, root_pages):
    """Map a staging URL path to a local root-level page filename, or '#'."""
    p = path.split("?")[0].split("#")[0].strip("/")
    if not p:
        return "index.html" if "index.html" in root_pages else "#"
    seg = p.split("/")[0].lower()
    for cand in (f"detail_{seg}.html", f"{seg}.html"):
        if cand in root_pages:
            return cand
    return "#"


def process_template(tpl):
    root_pages = {f for f in os.listdir(tpl)
                  if f.endswith(".html") and os.path.isfile(os.path.join(tpl, f))}
    stats = {"links": 0, "mapped": 0, "hash": 0, "files": 0}
    examples = []
    for fp in sorted(glob.glob(os.path.join(tpl, "**", "*.html"), recursive=True)):
        with open(fp, encoding="utf-8") as fh:
            html = fh.read()
        if ".webflow.io" not in html:
            continue
        depth = os.path.relpath(fp, tpl).count(os.sep)   # 0 at template root
        prefix = "../" * depth

        def repl(m):
            stats["links"] += 1
            tgt = target_for(m.group(2), root_pages)
            if tgt == "#":
                stats["hash"] += 1
                rel = "#"
            else:
                stats["mapped"] += 1
                rel = prefix + tgt
            if len(examples) < 3:
                examples.append(f'{m.group(1)}  ->  {rel}')
            return f'href="{rel}"'

        new = URL.sub(repl, html)
        if new != html:
            stats["files"] += 1
            if APPLY:
                with open(fp, "w", encoding="utf-8") as fh:
                    fh.write(new)
    return stats, examples


def main():
    grand = {"links": 0, "mapped": 0, "hash": 0, "files": 0}
    for tpl in sorted(glob.glob(os.path.join(ROOT, "*"))):
        if not os.path.isdir(tpl):
            continue
        stats, ex = process_template(tpl)
        if stats["links"] == 0:
            continue
        name = os.path.basename(tpl)
        print(f"  {name}: {stats['links']} links "
              f"({stats['mapped']} -> local, {stats['hash']} -> #) in {stats['files']} files")
        for e in ex:
            print("      " + e)
        for k in grand:
            grand[k] += stats[k]
    mode = "APPLIED" if APPLY else "DRY-RUN (no files written; pass --apply)"
    print(f"\n{mode}: {grand['links']} staging links across {grand['files']} files "
          f"-> {grand['mapped']} mapped to local pages, {grand['hash']} to '#'.")


if __name__ == "__main__":
    main()
