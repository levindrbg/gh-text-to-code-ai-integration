# GH component 1: Send user prompt to interpreter and start the pipeline.
#
# GHPython (CPython 3, Rhino 8):
#   Input  prompt: str — user prompt (e.g. "gable truss 12 m span, steel")
#   Input  run:    wire Button — click to run
#   Output a: communication (str)
#   Output b: run_id (str) — use this in the fetch-output component to get Karamba data
#   Output c: structure (dict, semantic outline)
#   Output d: error (str or None)

import os
import sys

REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

_env_path = os.path.join(REPO_ROOT, ".env")
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
    a = "No prompt provided."
    b = ""
    c = {}
    d = None
else:
    out = run_pipeline(prompt_text, run_id=None)
    a = out.get("communication", "")
    b = out.get("run_id", "")
    c = out.get("structure", {})
    d = out.get("error")
