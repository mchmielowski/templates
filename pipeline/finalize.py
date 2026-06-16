#!/usr/bin/env python3
"""
finalize.py <folder> — last step, AFTER the adaptive content/image pass:
prune now-unused images, then run QA. Safe to run only once content images are
referenced.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."

subprocess.run(["python3", f"{HERE}/prune.py", ROOT], check=False)
sys.exit(subprocess.run(["python3", f"{HERE}/qa.py", ROOT]).returncode)
