#!/usr/bin/env python3
"""
ingest.py <exports-dir> <download-dir> [<download-dir> ...]
Unzip every *.webflow.zip found under the download dirs into <exports-dir>/<Name>/,
where <Name> is the template's folder name. Skips already-extracted templates.
"""
import glob, os, shutil, sys, zipfile

EXPORTS = os.path.abspath(sys.argv[1])
DOWNLOADS = [os.path.abspath(d) for d in sys.argv[2:]]
os.makedirs(EXPORTS, exist_ok=True)

n = 0
for d in DOWNLOADS:
    for zp in glob.glob(f"{d}/**/*.zip", recursive=True):
        name = os.path.basename(os.path.dirname(zp)).strip()  # the <Template> folder name
        dest = os.path.join(EXPORTS, name)
        if os.path.exists(os.path.join(dest, "index.html")):
            continue  # already ingested
        os.makedirs(dest, exist_ok=True)
        try:
            with zipfile.ZipFile(zp) as z:
                z.extractall(dest)
            # some exports nest one level — flatten if index.html is in a subdir
            if not os.path.exists(os.path.join(dest, "index.html")):
                subs = glob.glob(f"{dest}/*/index.html")
                if subs:
                    inner = os.path.dirname(subs[0])
                    for item in os.listdir(inner):
                        os.rename(os.path.join(inner, item), os.path.join(dest, item))
            # validate it's actually a Webflow export (has index.html); else skip
            if os.path.exists(os.path.join(dest, "index.html")):
                n += 1
                print(f"  ingested: {name}")
            else:
                shutil.rmtree(dest, ignore_errors=True)
                print(f"  SKIP {name}: not a Webflow export (no index.html)")
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED {name}: {e}")
print(f"ingested {n} templates into {EXPORTS}")
