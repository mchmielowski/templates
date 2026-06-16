#!/usr/bin/env python3
"""
fix_screenshots.py <folder> [--apply] — replace Webflow page-SCREENSHOT images used
as visible content/background with real content photos.

Detection is by DIMENSION: Webflow exports page screenshots at 1440x1080 (plus 4:3
responsive variants) — far more reliable than filenames. og:image <meta> is left
alone. Without --apply it only reports.
"""
import glob, itertools, os, re, struct, sys

ROOT = os.path.abspath(sys.argv[1])
APPLY = "--apply" in sys.argv
NAME = os.path.basename(ROOT.rstrip("/"))
H = lambda *p: os.path.join(ROOT, *p)
read = lambda f: open(f, encoding="utf-8", errors="ignore").read()
relp = lambda f: os.path.relpath(f, ROOT)
base_stem = lambda fn: re.sub(r"-p-\d+$", "", os.path.splitext(fn)[0])
is_logo = lambda fn: fn.lower().endswith(".svg") or re.search(r"logo|icon|favicon|webclip|brand", fn.lower())
REF = re.compile(r'images/([^"\')\s]+\.(?:webp|avif|jpe?g|png|gif))', re.I)


def img_size(path):
    try:
        d = open(path, "rb").read(4096)
    except OSError:
        return None
    try:
        if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
            fmt = d[12:16]
            if fmt == b"VP8 ":
                return (int.from_bytes(d[26:28], "little") & 0x3FFF, int.from_bytes(d[28:30], "little") & 0x3FFF)
            if fmt == b"VP8L":
                b = int.from_bytes(d[21:25], "little")
                return ((b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1)
            if fmt == b"VP8X":
                return (1 + int.from_bytes(d[24:27], "little"), 1 + int.from_bytes(d[27:30], "little"))
        if d[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", d[16:24])
        # AVIF/HEIF (ISOBMFF): width/height live in the 'ispe' box
        if b"ftyp" in d[:32] and (b"avif" in d[:64] or b"heic" in d[:64] or b"mif1" in d[:64]):
            i = d.find(b"ispe")
            if i >= 0 and i + 16 <= len(d):
                return (int.from_bytes(d[i + 8:i + 12], "big"), int.from_bytes(d[i + 12:i + 16], "big"))
        # JPEG: scan SOF markers
        if d[:2] == b"\xff\xd8":
            j = 2
            while j + 9 < len(d):
                if d[j] != 0xFF:
                    j += 1; continue
                m = d[j + 1]
                if m in (0xC0, 0xC1, 0xC2, 0xC3):
                    return (int.from_bytes(d[j + 7:j + 9], "big"), int.from_bytes(d[j + 5:j + 7], "big"))
                j += 2 + int.from_bytes(d[j + 2:j + 4], "big")
    except Exception:
        return None
    return None


import collections
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
nbase = lambda fn: norm(base_stem(fn))
imgs = [os.path.basename(p) for p in glob.glob(H("images/*")) if os.path.isfile(p)]
dims = {fn: img_size(H("images", fn)) for fn in imgs}

# Discover this template's screenshot dimension(s): Webflow names page screenshots
# after pages, at one consistent size (varies per template: 1440x1080, 1600x1400…).
COMMON = {"og", "ogimage", "ogsales", "homepage", "homea", "homeb", "homec", "index",
          "password", "signin", "resetpassword", "createaccount", "styleguide", "404", "401"}
page_stems = {norm(os.path.splitext(os.path.basename(p))[0]) for p in glob.glob(f"{ROOT}/**/*.html", recursive=True)} | COMMON
dimc = collections.Counter(dims[fn] for fn in imgs if nbase(fn) in page_stems and dims[fn])
# naming-agnostic signal: Webflow makes ~1 screenshot per page, so MANY distinct base
# images share the exact same large dimension (content photos have varied sizes).
base_imgs = [fn for fn in imgs if not re.search(r"-p-\d+\.", fn)]
bydim = collections.Counter(dims[fn] for fn in base_imgs if dims.get(fn) and dims[fn][0] >= 800)
shot_dims = {d for d, c in dimc.items() if c >= 2} | {d for d, c in bydim.items() if c >= 6} | {(1440, 1080)}

shot_stems = {base_stem(fn) for fn in imgs if dims.get(fn) in shot_dims}
screenshots = {fn for fn in imgs if base_stem(fn) in shot_stems and not is_logo(fn)}
content = sorted(
    fn for fn in imgs
    if base_stem(fn) not in shot_stems and not is_logo(fn)
    and fn.lower().endswith((".webp", ".avif", ".jpg", ".jpeg", ".png")) and not re.search(r"-p-\d+\.", fn)
    and (dims.get(fn) or (999, 999))[0] >= 500 and (dims.get(fn) or (999, 999))[1] >= 300
)
pool = itertools.cycle(content) if content else None
used, swaps = set(), [0]


def refs_shot(seg):
    fns = [os.path.basename(m.group(0)) for m in REF.finditer(seg)]
    hit = [f for f in fns if f in screenshots]
    used.update(hit)
    return bool(hit)


for p in (glob.glob(f"{ROOT}/**/*.html", recursive=True) if (APPLY or True) else []):
    t = read(p)
    rel = "../" * (len(relp(p).split(os.sep)) - 1)

    def fix_img(m):
        tag = m.group(0)
        empty = re.search(r'\bsrc="\s*"', tag) is not None  # blank image slot
        if not (empty or refs_shot(tag)) or not (APPLY and pool):
            return tag
        photo = next(pool); swaps[0] += 1
        if re.search(r'\bsrc="', tag):
            tag = re.sub(r'\bsrc="[^"]*"', f'src="{rel}images/{photo}"', tag, count=1)
        else:
            tag = tag[:-1].rstrip("/").rstrip() + f' src="{rel}images/{photo}" />'
        tag = re.sub(r'\s*srcset="[^"]*"', "", tag)
        return tag

    def fix_bg(m):
        seg = m.group(0)
        if not refs_shot(seg) or not (APPLY and pool):
            return seg
        swaps[0] += 1
        return re.sub(r'images/[^"\')\s]+', f"images/{next(pool)}", seg, count=1)

    t = re.sub(r"<img\b[^>]*>", fix_img, t, flags=re.I | re.S)
    t = re.sub(r"background-image:\s*url\([^)]*\)", fix_bg, t, flags=re.I)
    if APPLY:
        open(p, "w", encoding="utf-8").write(t)

# also fix screenshots referenced as background images IN the stylesheets (css is in
# css/, so content refs use ../images/)
def fix_css_url(m):
    seg = m.group(0)
    if not refs_shot(seg) or not (APPLY and pool):
        return seg
    swaps[0] += 1
    return re.sub(r"(?:\.\./)*images/[^\"')\s]+", f"../images/{next(pool)}", seg, count=1)

for p in glob.glob(f"{ROOT}/css/*.css"):
    t = re.sub(r"url\([^)]*\)", fix_css_url, read(p), flags=re.I)
    if APPLY:
        open(p, "w", encoding="utf-8").write(t)

print(f"{NAME}: screenshot-imgs={len(screenshots)} used-as-content={len(used)} "
      f"swaps={swaps[0] if APPLY else 'DRY'} content-pool={len(content)}")
