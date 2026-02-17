# Copy this script into a GHPython component (CPython 3, Rhino 8).
# Input  x: user_prompt (str) — from Panel
# Input  y: run_id (str, optional) — leave empty for auto-generated
# Output a: structured_prompt (dict)
# Output b: run_id (str)

import os
import sys

REPO_ROOT = r"C:\path\to\repo"  # set to your repo path, or wire from Panel
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

config_path = os.path.join(REPO_ROOT, "03_python", "config", "settings.py")
exec(open(config_path).read())

user_prompt = str(x) if x else ""
run_id_in = str(y).strip() if (y and str(y).strip()) else None
ctx = {"ghenv": ghenv, "user_prompt": user_prompt, "run_id": run_id_in}
script_path = os.path.join(SCRIPTS_DIR, "ttc_interpreter.py")
exec(open(script_path).read(), ctx)
parse_prompt_to_structured = ctx["parse_prompt_to_structured"]
structured_prompt, run_id_out = parse_prompt_to_structured(user_prompt, run_id=run_id_in)
a = structured_prompt
b = run_id_out
