# Copy this script into a GHPython component (CPython 3, Rhino 8).
# Input  x: script_str (str) — from Generator step
# Output a: structural_result (dict) — nodes, members, loads, results

import os
import sys

REPO_ROOT = r"C:\path\to\repo"  # set to your repo path, or wire from Panel
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from script_executor import execute_generated_script

script_str = str(x) if x else ""
structural_result = execute_generated_script(script_str)
a = structural_result
