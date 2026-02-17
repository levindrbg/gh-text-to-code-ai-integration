# Copy this script into a GHPython component (CPython 3, Rhino 8).
# Input  x: user_prompt (str) — from Panel
# Input  y: top_k (int, optional) — default 5
# Output a: context_chunks (list of dicts with "text", "score")

import os
import sys

REPO_ROOT = r"C:\path\to\repo"  # set to your repo path, or wire from Panel
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

config_path = os.path.join(REPO_ROOT, "03_python", "config", "settings.py")
exec(open(config_path).read())

ctx = {"ghenv": ghenv, "user_prompt": x, "top_k": y if y is not None else 5}
script_path = os.path.join(SCRIPTS_DIR, "rag_query.py")
exec(open(script_path).read(), ctx)
a = ctx.get("context_chunks") or ctx.get("result") or []
