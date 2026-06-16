"""
clean_leftovers.py <built-dir-or-template> [--apply] — remove the last NON-FUNCTIONAL
Webflow leftovers that make a template look un-finished in view-source, WITHOUT
touching the load-bearing runtime (data-w-id / w-* / data-wf-page are read by the
vendored IX2 engine in js/main.js — see each template's CLAUDE.md — so they stay).

Two surgical jobs, both pure deletions of dead markup:

  1) DEAD FONT HINTS — every page ships a
        <link href="https://fonts.googleapis.com" rel="preconnect">
     (and sometimes a fonts.gstatic.com one). All fonts are already vendored
     locally (@font-face -> ../fonts/* or base64), so these load NOTHING — they
     only open an external connection to Google on page load (a privacy ping /
     the one remaining "external CDN" the README claims is gone). Removed.

  2) 401 PASSWORD PAGE — Webflow's utility password page posts to its hosted
     auth endpoint and injects server-rendered tokens that never resolve off
     Webflow:
        action="/.wf_auth"                      -> action="#"   (dead endpoint)
        <input ... value="<%WF_FORM_VALUE_PATH%>">  removed       (literal token
        <input ... value="<%WF_FORM_VALUE_PAGE%>">  removed        leaks in source)
     The page stays a working static "enter password" demo; the inline
     onload-fail JS handler is left intact.

Accepts either the whole built/ dir or a single template folder (recurses *.html).
Without --apply it reports per-file counts only. Run pipeline/qa.py afterwards.
"""
import os, re, sys, glob

ROOT = os.path.abspath(sys.argv[1])
APPLY = "--apply" in sys.argv

# 1) dead external font preconnect / dns-prefetch hints (fonts are local)
FONT_HINT = re.compile(
    r'[ \t]*<link\b[^>]*\bhref="https://fonts\.g(?:oogle|static)[^"]*"[^>]*>\n?',
    re.I,
)
# 2a) the dead Webflow password-page auth endpoint
WF_AUTH = '/.wf_auth'
# 2b) hidden inputs carrying unrendered server tokens (multi-line attrs)
WF_TOKEN_INPUT = re.compile(
    r'[ \t]*<input\b[^>]*<%WF_FORM_VALUE_[A-Z]+%>[^>]*>\n?',
    re.I | re.S,
)


def transform(html):
    n_hint = len(FONT_HINT.findall(html))
    html = FONT_HINT.sub("", html)

    n_auth = html.count(f'action="{WF_AUTH}"')
    html = html.replace(f'action="{WF_AUTH}"', 'action="#"')

    n_tok = len(WF_TOKEN_INPUT.findall(html))
    html = WF_TOKEN_INPUT.sub("", html)

    return html, n_hint, n_auth, n_tok


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True))
    tot = {"hint": 0, "auth": 0, "tok": 0}
    changed = 0
    for fp in files:
        with open(fp, encoding="utf-8") as fh:
            html = fh.read()
        new, n_hint, n_auth, n_tok = transform(html)
        if new == html:
            continue
        changed += 1
        tot["hint"] += n_hint
        tot["auth"] += n_auth
        tot["tok"] += n_tok
        rel = os.path.relpath(fp, ROOT)
        bits = []
        if n_hint:
            bits.append(f"{n_hint} font-hint")
        if n_auth:
            bits.append(f"{n_auth} wf_auth")
        if n_tok:
            bits.append(f"{n_tok} wf-token")
        print(f"  {rel}: {', '.join(bits)}")
        if APPLY:
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(new)
    mode = "APPLIED" if APPLY else "DRY-RUN (no files written; pass --apply)"
    print(f"\n{mode}: {changed} file(s) — "
          f"{tot['hint']} dead font hint(s), {tot['auth']} wf_auth action(s), "
          f"{tot['tok']} unrendered token input(s) removed.")


if __name__ == "__main__":
    main()
