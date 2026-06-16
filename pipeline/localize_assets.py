"""
localize_assets.py <built-dir> [--apply] [--no-video] — make templates truly
self-contained by replacing hot-linked `uploads-ssl.webflow.com` asset URLs with
LOCAL files, per template.

For every remote URL it either:
  * reuses an existing local copy (matched by filename, hash-prefix stripped), or
  * downloads the asset into the template's images/ (or videos/ for mp4/webm),
and then rewrites the reference to a relative local path (correct "../" depth for
files in subfolders).

Encoding reality this handles: filenames carry raw spaces, literal "()", and
"&amp;"; URLs sit in src="", style, data-poster-url="", and comma-separated
data-video-urls="". URLs are therefore delimited only by '"' or ','.

Safety: a reference is only rewritten if its local target exists or its download
SUCCEEDED — a failed download leaves the original remote URL untouched, so the
page never ends up pointing at a missing file. Run pipeline/qa.py afterwards.

--no-video skips downloading mp4/webm (icons + images only).
"""
import os, re, sys, glob, html, urllib.parse, subprocess, shutil

ROOT = os.path.abspath(sys.argv[1])
APPLY = "--apply" in sys.argv
NO_VIDEO = "--no-video" in sys.argv

# Both Webflow asset CDNs: legacy uploads-ssl.webflow.com and current
# *.website-files.com (e.g. cdn.prod.website-files.com).
URLRE = re.compile(r'https://(?:uploads-ssl\.webflow\.com|[a-z0-9.-]*website-files\.com)[^",<>]+')
VIDEO_EXT = (".mp4", ".webm")


def strip_hashes(name):
    """Drop one-or-more leading '<hex>_' upload-hash prefixes."""
    while re.match(r'^[0-9a-fA-F]{8,}_', name):
        name = name.split("_", 1)[1]
    return name


def decoded_basename(raw):
    s = html.unescape(raw)                      # &amp; -> &
    s = urllib.parse.unquote(s)                 # %20 -> space, %2F -> /
    return s.split("/")[-1]


def fetch_url(raw):
    s = html.unescape(raw).replace("%2F", "/")  # real path separators
    return urllib.parse.quote(s, safe="/:?#[]@!$&'()*+,;=~%")  # encode spaces etc.


def safe_filename(name):
    """Web-safe local filename for a freshly downloaded asset."""
    name = strip_hashes(name)
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"[^\w.-]+", "-", stem).strip("-") or "asset"
    stem = re.sub(r"-{2,}", "-", stem)
    return stem + ext.lower()


def index_local(tpl):
    exact, norm, stem = {}, {}, {}
    for r, _, fs in os.walk(tpl):
        for f in fs:
            rel = os.path.relpath(os.path.join(r, f), tpl)
            exact.setdefault(f, rel)
            n = strip_hashes(f)
            norm.setdefault(n, rel)
            stem.setdefault(os.path.splitext(n)[0].lower(), rel)
    return exact, norm, stem


def main():
    downloads = {}     # fetch_url -> set of absolute dest paths (deduped fetch, many dests)
    edits = []         # (filepath, raw_token, target_rel, target_abs)
    stat = {"reuse": 0, "download": 0, "skip_video": 0, "files": set()}

    for tpl in sorted(glob.glob(os.path.join(ROOT, "*"))):
        if not os.path.isdir(tpl):
            continue
        exact, norm, stem = index_local(tpl)
        for fp in sorted(glob.glob(os.path.join(tpl, "**", "*.html"), recursive=True)):
            html_txt = open(fp, encoding="utf-8").read()
            if "webflow.com" not in html_txt and "website-files.com" not in html_txt:
                continue
            depth = os.path.relpath(fp, tpl).count(os.sep)
            prefix = "../" * depth
            for m in URLRE.finditer(html_txt):
                raw = m.group(0).rstrip()
                base = decoded_basename(raw)
                ext = os.path.splitext(base)[1].lower()
                # 1) reuse existing local copy
                hit = (exact.get(base) or norm.get(strip_hashes(base))
                       or stem.get(os.path.splitext(strip_hashes(base))[0].lower()))
                if hit:
                    stat["reuse"] += 1
                    edits.append((fp, raw, prefix + hit.replace(os.sep, "/"),
                                  os.path.join(tpl, hit)))
                    stat["files"].add(fp)
                    continue
                # 2) needs download
                if ext in VIDEO_EXT and NO_VIDEO:
                    stat["skip_video"] += 1
                    continue
                folder = "videos" if ext in VIDEO_EXT else "images"
                fn = safe_filename(base)
                dest = os.path.join(tpl, folder, fn)
                downloads.setdefault(fetch_url(raw), set()).add(dest)
                stat["download"] += 1
                edits.append((fp, raw, prefix + folder + "/" + fn, dest))
                stat["files"].add(fp)

    print(f"References: reuse-local {stat['reuse']}, download {stat['download']}, "
          f"skipped-video {stat['skip_video']}  across {len(stat['files'])} files")
    print(f"Unique downloads: {len(downloads)}")
    if not APPLY:
        print("\nDRY-RUN (no downloads, no edits). Pass --apply to execute.")
        return

    # download each unique URL once, then copy to every template dest that needs it
    failed = 0
    print("\nDownloading…")
    items = sorted(downloads.items())
    for i, (url, dests) in enumerate(items, 1):
        dests = sorted(dests)
        first = dests[0]
        os.makedirs(os.path.dirname(first), exist_ok=True)
        rc = subprocess.run(
            ["curl", "-sSL", "--fail", "--retry", "3", "--retry-delay", "2",
             "--max-time", "300", "-o", first, url],
            capture_output=True).returncode
        if rc == 0 and os.path.exists(first) and os.path.getsize(first) > 0:
            for d in dests[1:]:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copyfile(first, d)
        else:
            failed += 1
            if os.path.exists(first):
                os.remove(first)
            print(f"  FAILED ({rc}): {url[:90]}")
        if i % 25 == 0:
            print(f"  …{i}/{len(items)}")
    print(f"Downloaded OK: {len(items) - failed}/{len(items)}")

    # rewrite refs — ONLY when the local target file now exists on disk.
    # (failed download / still-missing asset -> ref stays remote, never broken)
    by_file, skipped = {}, 0
    for fp, raw, target, target_abs in edits:
        if os.path.exists(target_abs):
            by_file.setdefault(fp, []).append((raw, target))
        else:
            skipped += 1
    changed = 0
    for fp, reps in by_file.items():
        txt = open(fp, encoding="utf-8").read()
        for raw, target in reps:
            txt = txt.replace(raw, target)
        open(fp, "w", encoding="utf-8").write(txt)
        changed += 1
    print(f"Rewrote refs in {changed} files. Left remote (missing local): {skipped}")


if __name__ == "__main__":
    main()
