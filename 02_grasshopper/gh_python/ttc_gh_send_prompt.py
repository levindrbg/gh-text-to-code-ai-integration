# GH component 1: Send user prompt to interpreter and start the pipeline.
# This file is in the repo (02_grasshopper) only for editing. Copy-paste its contents
# into a GHPython component in TTC_Workflow_V1.gh. Path logic below must work when
# run inside the component (not when run as this .py file); __file__ may be absent.
#
# GHPython (CPython 3, Rhino 8):
#   Input  prompt: str — user prompt (e.g. "gable truss 12 m span, steel")
#   Input  run:    wire Button — click to run
#   Output communication: str — ONLY the chat completion from the interpreter (LLM message; no errors)
#   Output run_id: str — use this in the fetch-output component to get Karamba data
#   Output run_commentary: str — from main.py: step log + all error messages

import os
import sys
from pathlib import Path

# Hardcode repo root so 03_python is always found when pasted into GH (Rhino cwd/__file__ are unreliable)
REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"
# Fallback if you moved the project: try cwd
if not os.path.isdir(os.path.join(REPO_ROOT, "03_python")):
    _cwd = Path(os.getcwd()).resolve()
    if (_cwd / "03_python").is_dir():
        REPO_ROOT = str(_cwd)
    elif _cwd.name == "02_grasshopper" and (_cwd.parent / "03_python").is_dir():
        REPO_ROOT = str(_cwd.parent)

SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
os.environ["TTC_03_PYTHON"] = os.path.abspath(SCRIPTS_DIR)

_env_path = os.path.join(REPO_ROOT, "00_setup", ".env")
if os.path.isfile(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _, _v = _line.partition("=")
                    _k, _v = _k.strip(), _v.strip()
                    if _v.startswith('"') and _v.endswith('"'): _v = _v[1:-1]
                    elif _v.startswith("'") and _v.endswith("'"): _v = _v[1:-1]
                    if _k:
                        os.environ.setdefault(_k, _v)

from ttc_main import run as run_pipeline

prompt_text = str(prompt).strip() if prompt else ""
if not prompt_text:
    communication = "No prompt provided."
    run_id = ""
    run_commentary = ""
else:
    try:
        out = run_pipeline(prompt_text, run_id=None)
        communication = out.get("communication", "")
        run_id = out.get("run_id", "")
        run_commentary = out.get("run_commentary", "")
    except Exception as e:
        communication = ""
        run_id = ""
        run_commentary = "Error: {}".format(e)
