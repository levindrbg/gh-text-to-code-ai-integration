# Copy this script into a GHPython component (CPython 3, Rhino 8).
# Input  x: run_id (str, optional) — from Interpreter step; leave empty to use latest
# Input  y: context_chunks (list, optional) — from RAG query; leave empty if no RAG
# Output a: script_str (str) — generated Python script

import os
import sys

REPO_ROOT = r"C:\path\to\repo"  # set to your repo path, or wire from Panel
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

config_path = os.path.join(REPO_ROOT, "03_python", "config", "settings.py")
exec(open(config_path).read())

from ttc_generator import find_latest_structured_prompt, generate_geometry_script

run_id = str(x).strip() if x else None
context_chunks = y if y else []

if run_id:
    import json
    prompt_path = os.path.join(REPO_ROOT, "03_python", "prompt", run_id, "structured_prompt.json")
    with open(prompt_path) as f:
        structured_prompt = json.load(f)
else:
    _, structured_prompt = find_latest_structured_prompt()

script_str = generate_geometry_script(structured_prompt, context_chunks=context_chunks, run_id=run_id)
a = script_str
