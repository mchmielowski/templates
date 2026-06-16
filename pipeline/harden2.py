#!/usr/bin/env python3
"""
harden2.py <folder> — production hardening pass (deterministic, no agents):
  1. vendor jQuery locally (fix the external code.jquery.com ref)
  2. localize external Webflow-CDN images + og:image -> local files
  3. fill empty <title> tags (use the page's H1, else a humanized name)
  4. repair broken internal page links (fuzzy -> existing page, else '#')
Safe to re-run.
"""
import glob, os, re, socket, sys, urllib.request

socket.setdefaulttimeout(20)
ROOT = os.path.abspath(sys.argv[1])
NAME = os.path.basename(ROOT.rstrip("/"))
H = lambda *p: os.path.join(ROOT, *p)
pages = glob.glob(f"{ROOT}/**/*.html", recursive=True)
read = lambda f: open(f, encoding="utf-8", errors="ignore").read()
write = lambda f, t: open(f, "w", encoding="utf-8").write(t)
relp = lambda f: os.path.relpath(f, ROOT)
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
page_rels = {relp(p) for p in pages}
fixed = {"jquery": 0, "images": 0, "titles": 0, "links": 0}

# 1. vendor jQuery once
JQ = None
if any("code.jquery.com" in read(p) for p in pages):
    dest = H("js", "jquery.min.js")
    os.makedirs(H("js"), exist_ok=True)
    if not os.path.exists(dest):
        try:
            urllib.request.urlretrieve("https://code.jquery.com/jquery-3.5.1.min.js", dest)
        except Exception:
            dest = None
    JQ = "js/jquery.min.js" if dest else None

# 2. collect + download external Webflow-CDN images
img_map = {}
ext_img = re.compile(r'(?:src|content)="(https://[^"]*website-files[^"]*\.(?:png|jpe?g|webp|avif|svg|gif))"', re.I)
urls = set()
for p in pages:
    urls |= set(ext_img.findall(read(p)))
os.makedirs(H("images"), exist_ok=True)
for u in urls:
    nm = re.sub(r"[?#].*$", "", u).split("/")[-1]
    try:
        urllib.request.urlretrieve(u, H("images", nm))
        img_map[u] = "images/" + nm
    except Exception:
        pass


def fix_title(t, p):
    m = re.search(r"<title>\s*</title>", t)
    if not m:
        return t
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    title = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else ""
    title = re.sub(r"\s+", " ", title)[:70]
    if not title:
        stem = re.sub(r"[-_]", " ", os.path.splitext(os.path.basename(p))[0])
        stem = re.sub(r"^detail ", "", stem).strip().title()
        title = f"{stem} | {NAME}" if stem.lower() not in ("index", "home") else NAME
    fixed["titles"] += 1
    return t[:m.start()] + f"<title>{title}</title>" + t[m.end():]


def fix_links(t, p):
    page_dir = os.path.dirname(relp(p))
    for href in set(re.findall(r'href="([^"#?:]+\.html)"', t)):
        target = os.path.normpath(os.path.join(page_dir, href))
        if target in page_rels or os.path.exists(H(target)):
            continue
        # fuzzy: existing page whose basename normalizes close to the broken one
        k = norm(os.path.splitext(os.path.basename(href))[0])
        cand = next((rp for rp in page_rels
                     if norm(os.path.splitext(os.path.basename(rp))[0]) == k), None)
        if not cand:
            cand = next((rp for rp in page_rels
                         if norm(os.path.splitext(os.path.basename(rp))[0]).startswith(k[:8])), None)
        new = os.path.relpath(cand, page_dir) if cand else "#"
        t = re.sub(r'href="' + re.escape(href) + r'"', f'href="{new}"', t)
        fixed["links"] += 1
    return t


for p in pages:
    t = read(p)
    depth = len(relp(p).split(os.sep)) - 1
    rel = "../" * depth
    if JQ:
        t2 = t.replace("https://code.jquery.com/jquery-3.5.1.min.js", rel + JQ)
        if t2 != t:
            fixed["jquery"] += 1
            t = t2
    for u, loc in img_map.items():
        if u in t:
            t = t.replace(u, rel + loc)
            fixed["images"] += 1
    t = fix_title(t, p)
    t = fix_links(t, p)
    write(p, t)

print(f"{NAME}: jquery-refs={fixed['jquery']} images-localized={fixed['images']} "
      f"titles={fixed['titles']} links={fixed['links']}")
