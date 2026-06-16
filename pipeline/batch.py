#!/usr/bin/env python3
"""
batch.py <exports-dir> [<built-dir>] — run the deterministic pipeline + QA over
every template in <exports-dir>, in parallel. Copies each to <built-dir> first
(default: ../built), so source exports are never modified. Writes a report.

    python3 batch.py ../exports ../built
"""
import concurrent.futures as cf
import os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(os.path.dirname(SRC), "built")
REPORTS = os.path.join(os.path.dirname(SRC), "reports")


def templates(d):
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "index.html")):
            yield name


def process(name):
    src, dst = os.path.join(SRC, name), os.path.join(OUT, name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    b = subprocess.run(["python3", f"{HERE}/build.py", dst], capture_output=True, text=True)
    q = subprocess.run(["python3", f"{HERE}/qa.py", dst], capture_output=True, text=True)
    status = {0: "CLEAN", 3: "ADAPTIVE", 1: "HARD"}.get(q.returncode, "ERROR")
    return name, status, (q.stdout + q.stderr).strip(), b.returncode


def main():
    names = list(templates(SRC))
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)
    print(f"building {len(names)} templates  {SRC} -> {OUT}\n")
    rows, t0 = [], time.time()
    with cf.ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) - 1)) as ex:
        for name, status, msg, brc in ex.map(process, names):
            mark = {"CLEAN": "✓", "ADAPTIVE": "~", "HARD": "✗", "ERROR": "‼"}[status]
            print(f"{mark} {status:9} {name}")
            if status in ("HARD", "ERROR"):
                for line in msg.splitlines()[1:]:
                    print("      " + line)
            rows.append((name, status, msg, brc))

    by = lambda s: [r for r in rows if r[1] == s]
    report = os.path.join(REPORTS, "batch-report.txt")
    with open(report, "w") as fh:
        for status in ("CLEAN", "ADAPTIVE", "HARD", "ERROR"):
            grp = by(status)
            fh.write(f"\n== {status} ({len(grp)}) ==\n")
            for name, _, msg, _ in grp:
                fh.write(f"  {name}\n")
                if status in ("HARD", "ERROR"):
                    for line in msg.splitlines()[1:]:
                        fh.write("      " + line + "\n")
    print(f"\n{'='*48}")
    print(f"CLEAN: {len(by('CLEAN'))}   ADAPTIVE(needs content): {len(by('ADAPTIVE'))}   "
          f"HARD-FAIL: {len(by('HARD'))}   ERROR: {len(by('ERROR'))}")
    print(f"elapsed {int(time.time()-t0)}s · report: {report}")
    print("Next: adaptive content/image agent pass on ADAPTIVE templates, then finalize.py each.")


if __name__ == "__main__":
    main()
