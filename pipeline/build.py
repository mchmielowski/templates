#!/usr/bin/env python3
"""
build.py — run the full DETERMINISTIC de-Webflow pipeline on ONE export folder,
in place. Auto-detects filenames/scripts so it works on any Webflow HTML export,
not just one template.

    python3 build.py /path/to/export

Steps (all generic — no per-template content/judgment):
  1. rename engine-named files (*.webflow.css -> styles.css, webflow.js -> main.js)
  2. strip Webflow attribution (comment, <meta generator>, badge)
  3. rebrand "powered by Webflow" + swap the fingerprinted jQuery CDN
  4. remove the byq demo overlay (.master_sales-cta) — set DEMO_OVERLAY_CLASSES
  5. normalize emoji/double-dash CSS custom properties -> clean kebab-case
  6. drop dead "<deleted|variable>" declarations
  7. vendor the loaded JS libraries locally + rewrite <script src> (depth-aware)
  8. prettify all HTML with prettier
  9. remove .w-dyn-empty fallbacks + fill w-dyn-bind-empty by field type
 10. prune unused images
 11. generate CLAUDE.md + .cursorrules (AI guide) from the page list

Adaptive steps (sample content, image curation) are intentionally NOT here —
run them as a per-template agent pass afterwards.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
H = lambda *p: os.path.join(ROOT, *p)
DEMO_OVERLAY_CLASSES = ["master_sales-cta", "master_sales-ctas"]  # byq demo widget
REBRAND_URL, REBRAND_TEXT = "https://byq.supply", "byq.supply"


def html_files():
    return glob.glob(H("**/*.html"), recursive=True)


def read(f):
    return open(f, encoding="utf-8", errors="ignore").read()


def write(f, t):
    open(f, "w", encoding="utf-8").write(t)


# --- 1. rename engine-named files --------------------------------------------
def rename_files():
    renames = {}
    for css in glob.glob(H("css/*.webflow.css")):
        renames["css/" + os.path.basename(css)] = "css/styles.css"
    if os.path.exists(H("css/webflow.css")):
        renames["css/webflow.css"] = "css/components.css"
    # main site script: webflow.js, or a single custom-named engine (e.g. unit01.js)
    LIBS = ("jquery", "gsap", "scrolltrigger", "splittext", "drawsvg", "normalize",
            "webflow", "lottie", "swiper", "three", "lenis", "barba")
    if os.path.exists(H("js/webflow.js")):
        renames["js/webflow.js"] = "js/main.js"
    else:
        customs = [os.path.basename(p) for p in glob.glob(H("js/*.js"))
                   if not any(l in os.path.basename(p).lower() for l in LIBS)
                   and os.path.basename(p) != "main.js"]
        if len(customs) == 1:
            renames[f"js/{customs[0]}"] = "js/main.js"
    for old, new in renames.items():
        if os.path.exists(H(old)):
            os.rename(H(old), H(new))
    return renames


# --- 5/6. CSS custom-property normalization ----------------------------------
_VARNAME = r"--[^\s:;,(){}'\"\[\]=<>]+"
DECL_RE = re.compile(rf"({_VARNAME})\s*:")
VAR_USE_RE = re.compile(rf"var\(\s*({_VARNAME})")
DEAD_VAR = re.compile(r"^[ \t]*--[^:\n]*[<>|\\][^:\n]*:[^;\n]*;[ \t]*\n?", re.M)


def cleanname(tok):
    s = re.sub(r"[^0-9A-Za-z]+", "-", tok.lstrip("-"))
    return "--" + s.strip("-").lower()


def build_var_map(css_files):
    tokens = set()
    for f in css_files:
        c = read(f)
        tokens |= set(DECL_RE.findall(c)) | set(VAR_USE_RE.findall(c))
    vmap, used = {}, {}
    for old in sorted(tokens):
        base, new, i = cleanname(old), cleanname(old), 2
        while new in used and used[new] != old:
            new, i = f"{base}-{i}", i + 1
        used[new] = old
        vmap[old] = new
    return vmap


# --- 3. attribution + rebrand + jQuery ---------------------------------------
SUBS = [
    (re.compile(r"<!--\s*(This site was created in Webflow|Last Published)[^>]*-->", re.I), ""),
    (re.compile(r'<meta[^>]*name="generator"[^>]*>', re.I), ""),
    (re.compile(r'<a [^>]*class="[^"]*w-webflow-badge[^"]*".*?</a>', re.I | re.S), ""),
    (re.compile(r'<script src="https://d3e54v103j8qbb\.cloudfront\.net[^"]*"[^>]*></script>'),
     '<script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>'),
    (re.compile(r'<a\s+href="https?://(?:www\.)?webflow\.com/?"[\s\S]*?>\s*Webflow\s*</a\s*>', re.I),
     f'<a href="{REBRAND_URL}" target="_blank" class="tone-medium">{REBRAND_TEXT}</a>'),
    # catch-all: neutralize any remaining webflow.com href (non-credit links)
    (re.compile(r'href="https?://(?:www\.)?webflow\.com/?[^"]*"', re.I), f'href="{REBRAND_URL}"'),
    (re.compile(r"Webflow HTML website template"), "SaaS Website Template"),
]


# --- 4. remove demo overlay / empty-state blocks (balanced div) ---------------
def remove_blocks(html, cls):
    # match a <div> whose class list CONTAINS cls (any other classes allowed)
    pat = re.compile(r'<div\b[^>]*\bclass="[^"]*(?<![\w-])' + re.escape(cls) + r'(?![\w-])[^"]*"[^>]*>')
    out, i = [], 0
    while True:
        m = pat.search(html, i)
        if not m:
            out.append(html[i:]); break
        j = m.start()
        k = j
        while k > 0 and html[k - 1] in " \t":
            k -= 1
        if k > 0 and html[k - 1] == "\n":
            k -= 1
        out.append(html[i:k])
        depth = 0
        for m in re.finditer(r"<(/?)div\b", html[j:]):
            depth += -1 if m.group(1) else 1
            if depth == 0:
                i = html.index(">", j + m.end()) + 1; break
    return "".join(out)


# --- 9. fill empty CMS fields (generic, by field-class) ----------------------
import itertools
# Only TEXT fields are filled generically. Image fields (covers/logos) are left as
# Webflow placeholders on purpose — image curation is adaptive, and QA flags them.
TEXT = {
    "title": ["Sample headline", "Another sample headline", "A third headline"],
    "category": ["Engineering", "Product", "Guides", "Insights"],
    "meta": ["5 min read", "4 min read", "6 min read"],
    "excerpt": ["A short sample description for this item."],
    "name": ["Alex Rivera", "Jordan Kim", "Sam Okafor"],
    "role": ["Engineer", "Product Lead", "Founder"],
    "rich": ["<p>Sample body copy for this item — replace with your own content.</p>"],
    "heading": ["Section headline"],
}
cyc = {k: itertools.cycle(v) for k, v in TEXT.items()}


def route_text(cls):
    if "w-richtext" in cls or "body_" in cls:
        return next(cyc["rich"])
    if any(h in cls for h in ("heading-style-h1", "heading-style-h3", "heading-style-h4")):
        return next(cyc["heading"])
    if "heading-style-h5" in cls:
        return next(cyc["title"])
    if "label-large" in cls:
        return next(cyc["category"])
    if "text-size-small" in cls:
        return next(cyc["meta"])
    if "text-size-large" in cls:
        return next(cyc["excerpt"])
    if "margin-0" in cls and "tone-medium" in cls:
        return next(cyc["role"])
    if "margin-0" in cls:
        return next(cyc["name"])
    return ""


strip_marker = lambda s: s.replace(" w-dyn-bind-empty", "").replace("w-dyn-bind-empty", "")
EMPTY_TAG_RE = re.compile(r"(<(?:div|h[1-6]|p|span|a)\b[^>]*?>)\s*</(?:div|h[1-6]|p|span|a)>", re.S)


def fill_empty(html):
    for cls in DEMO_OVERLAY_CLASSES:
        html = remove_blocks(html, cls)
    html = remove_blocks(html, "w-dyn-empty")

    def fix_tag(m):
        open_t = m.group(1)
        if "w-dyn-bind-empty" not in open_t:
            return m.group(0)
        cm = re.search(r'class="([^"]*)"', open_t, re.S)
        tag = re.match(r"<(\w+)", open_t).group(1)
        return strip_marker(open_t) + route_text(cm.group(1) if cm else "") + f"</{tag}>"

    html = EMPTY_TAG_RE.sub(fix_tag, html)
    return strip_marker(html)


# --- reconcile broken image refs (pre-existing Webflow filename mismatch) -----
def reconcile_images():
    """Webflow sometimes references `X-1.webp` while the exported file is `X (1).webp`.
    Match broken refs to disk files by alphanumeric-normalized name and rename the
    file to what the HTML expects, so the images resolve (and filenames get cleaner)."""
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    files = [os.path.basename(p) for p in glob.glob(H("images/*")) if os.path.isfile(p)]
    by_norm = {}
    for fn in files:
        by_norm.setdefault(norm(fn), []).append(fn)
    on_disk = set(files)
    refs = set()
    for f in html_files() + glob.glob(H("css/*.css")):
        refs |= set(re.findall(r'(?:\.\./)?images/([^"\')\s,]+\.(?:webp|avif|svg|jpe?g|png|gif))',
                               read(f), re.I))
    renamed = 0
    for ref in refs:
        base = os.path.basename(ref)
        if base in on_disk:
            continue
        cands = [c for c in by_norm.get(norm(base), []) if c in on_disk]
        if len(cands) == 1 and not os.path.exists(H("images", base)):
            os.rename(H("images", cands[0]), H("images", base))
            on_disk.discard(cands[0]); on_disk.add(base); renamed += 1
    # Pass 2: Webflow references a base name `X.ext` but only exported variants
    # (`X_1.ext`, `X-p-800.ext`). COPY the best variant to the base name so the
    # `src=` resolves (the variants stay for `srcset=`).
    for ref in refs:
        base = os.path.basename(ref)
        if base in on_disk or os.path.exists(H("images", base)):
            continue
        stem, _, ext = base.rpartition(".")
        nstem = norm(stem)
        if not nstem:
            continue
        variants = [f for f in on_disk
                    if f.lower().endswith("." + ext.lower())
                    and norm(os.path.splitext(f)[0]).startswith(nstem)]
        variants.sort(key=lambda f: ("-p-" in f, len(f)))  # prefer non-responsive, then shortest
        if variants:
            shutil.copy(H("images", variants[0]), H("images", base))
            on_disk.add(base); renamed += 1
    return renamed


# --- localize external Webflow-CDN images -------------------------------------
def localize_external_images():
    pat = re.compile(r'src="(https://[^"]*website-files[^"]*\.(?:webp|avif|svg|jpe?g|png|gif))"', re.I)
    urls = set()
    for f in html_files():
        urls |= set(pat.findall(read(f)))
    mapping = {}
    for u in urls:
        name = re.sub(r"[?#].*$", "", u).split("/")[-1]
        try:
            urllib.request.urlretrieve(u, H("images", name))
            mapping[u] = "images/" + name
        except Exception:  # noqa: BLE001 — dead CDN url; leave ref, QA will flag it
            pass
    return mapping


# --- 7. vendor JS libraries + rewrite refs -----------------------------------
def vendor_js():
    sample = read(H("index.html")) if os.path.exists(H("index.html")) else read(html_files()[0])
    urls = re.findall(r'<script src="(https?://[^"]+\.js[^"]*)"', sample)
    mapping = {}
    for u in urls:
        name = re.sub(r"[?#].*$", "", u).split("/")[-1]
        name = re.sub(r"jquery[.-].*", "jquery.min.js", name)  # normalize jquery filename
        local = f"js/{name}"
        try:
            urllib.request.urlretrieve(u, H(local))
            mapping[u] = local
        except Exception as e:  # noqa: BLE001
            print(f"    ! could not vendor {u}: {e}")
    return mapping


# --- main per-step application ------------------------------------------------
def main():
    import socket
    socket.setdefaulttimeout(20)  # never hang the overnight batch on a dead CDN
    print(f"building {ROOT}")
    renames = rename_files()
    css_files = glob.glob(H("css/*.css"))
    # Build the var map from CSS *and* HTML (Webflow embeds per-page <style> blocks
    # with their own custom-property declarations).
    vmap = build_var_map(css_files + html_files())
    sub_decl = lambda t: DECL_RE.sub(lambda m: f"{vmap.get(m.group(1), m.group(1))}:", t)
    sub_use = lambda t: VAR_USE_RE.sub(lambda m: f"var({vmap.get(m.group(1), m.group(1))}", t)

    js_map = vendor_js()
    img_map = localize_external_images()

    for f in html_files():
        t = read(f)
        for pat, rep in SUBS:
            t = pat.sub(rep, t)
        # update refs for every renamed file (css/*.webflow.css, webflow.js, custom engine)
        for old, new in renames.items():
            t = t.replace(old, new)
        # vendor/localized refs (depth-aware)
        depth = len(os.path.relpath(f, ROOT).split(os.sep)) - 1
        rel = "../" * depth
        for url, local in {**js_map, **img_map}.items():
            t = t.replace(url, rel + local)
        t = sub_decl(sub_use(t))  # normalize var usages AND inline <style> declarations
        t = fill_empty(t)
        write(f, t)

    for f in css_files:
        c = DEAD_VAR.sub("", read(f))
        write(f, sub_use(sub_decl(c)))

    reconcile_images()  # fix pre-existing Webflow filename mismatches

    print("  prettifying HTML…")
    subprocess.run(["npx", "--yes", "prettier@3", "--write", "**/*.html", "--log-level", "error"],
                   cwd=ROOT, check=False)

    subprocess.run(["python3", os.path.join(os.path.dirname(__file__), "gen_ai_guide.py"), ROOT], check=False)
    # NOTE: image pruning is deliberately NOT done here — it must run as the final
    # step AFTER the adaptive content/image pass, or it deletes the content images
    # that pass will use. Run `python3 finalize.py <folder>` last.
    print("  done (generic pass). Next: adaptive content pass, then finalize.py.")


if __name__ == "__main__":
    main()
