#!/usr/bin/env python3
"""
audit.py <folder> — production-readiness audit (beyond qa.py's invariants).
Flags things that would embarrass you in front of a paying customer.
Prints JSON {template, issues:{check: [examples]}, counts}.
"""
import glob, json, os, re, sys

ROOT = os.path.abspath(sys.argv[1])
NAME = os.path.basename(ROOT.rstrip("/"))
pages = [p for p in glob.glob(f"{ROOT}/**/*.html", recursive=True)]
issues = {}


def add(check, item):
    issues.setdefault(check, [])
    if item not in issues[check]:
        issues[check].append(item)


def rel(p):
    return os.path.relpath(p, ROOT)


page_files = {rel(p) for p in pages}

for p in pages:
    t = open(p, encoding="utf-8", errors="ignore").read()
    r = rel(p)
    low = t.lower()

    # 1. leftover lorem ipsum / obvious placeholder text (style-guide pages excluded — dev ref)
    if "style-guide" not in r and re.search(r"lorem ipsum|dolor sit amet|consectetur adipi", low):
        add("lorem_ipsum", r)
    # 2. placeholder names / dummy text a customer would notice
    if re.search(r"name surname|john doe|jane doe|your name here|add your|lorem|ipsum company|joesph", low):
        add("placeholder_text", r)
    if re.search(r"\bsample (headline|body copy|description)\b", low):
        add("sample_text_leftover", r)
    # 3. forms with no real action (won't submit)
    for m in re.finditer(r"<form\b[^>]*>", t, re.I):
        tag = m.group(0)
        act = re.search(r'action="([^"]*)"', tag, re.I)
        if not act or act.group(1).strip() in ("", "#"):
            add("form_no_action", r)
    # 4. external script dependencies (should all be local)
    for m in re.findall(r'<script[^>]+src="(https?://[^"]+)"', t, re.I):
        add("external_script", m)
    # 5. external images (incl. og:image) — should be local
    for m in re.findall(r'(?:src|content)="(https?://[^"]+\.(?:png|jpe?g|webp|avif|svg|gif))"', t, re.I):
        add("external_image", m)
    # 6. empty / placeholder titles & missing description
    tt = re.search(r"<title>(.*?)</title>", t, re.S)
    if not tt or not tt.group(1).strip():
        add("empty_title", r)
    if not re.search(r'name="description"\s+content="[^"]{10,}"|content="[^"]{10,}"\s+name="description"', t, re.I):
        add("missing_meta_description", r)
    # 7. broken internal page links (relative .html that doesn't exist)
    for href in re.findall(r'href="([^"#?:]+\.html)"', t):
        target = os.path.normpath(os.path.join(os.path.dirname(r), href))
        if target not in page_files and not os.path.exists(os.path.join(ROOT, target)):
            add("broken_page_link", f"{href} (in {r})")
    # 8. duplicate data-w-id on the SAME page (breaks IX2 interactions)
    ids = re.findall(r'data-w-id="([^"]+)"', t)
    dups = {i for i in ids if ids.count(i) > 1}
    if dups:
        add("duplicate_data_w_id", f"{r} ({len(dups)} dup ids)")
    # 9. dead/placeholder links
    if re.search(r'href="(mailto:|tel:)?(your@email|name@example|example\.com|#TODO)', low):
        add("placeholder_link", r)

counts = {k: len(v) for k, v in issues.items()}
# trim examples for readability
trimmed = {k: v[:5] for k, v in issues.items()}
print(json.dumps({"template": NAME, "counts": counts, "examples": trimmed}))
