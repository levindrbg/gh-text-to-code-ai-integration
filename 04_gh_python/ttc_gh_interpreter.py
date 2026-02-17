# Copy this script into a GHPython component (CPython 3, Rhino 8).
# Input 1: prompt (str) — original user prompt: what kind of structure they want to design
# Input 2: run — wire Button here; click to run (each run creates a new run_id)
# Output 1: out — same as answer (communication from LLM)
# Output 2: run_id — id for this run (for Generator step)
# Output 3: structure — filled JSON (dict)
# Output 4: answer — communication: questions for clarification or brief summary

import os
import sys

REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"  # change if repo is elsewhere
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# Load API keys from .env at repo root (works without python-dotenv, e.g. in Rhino)
_env_path = os.path.join(REPO_ROOT, ".env")
if os.path.isfile(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass
    # Fallback: read .env manually so it works in Rhino when dotenv isn't installed
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _, _v = _line.partition("=")
                    _k, _v = _k.strip(), _v.strip()
                    if _v.startswith('"') and _v.endswith('"'): _v = _v[1:-1]
                    elif _v.startswith("'") and _v.endswith("'"): _v = _v[1:-1]
                    if _k: os.environ.setdefault(_k, _v)

from ttc_interpreter import parse_prompt_to_structured, get_latest_run_id

# Inputs from GH are named: prompt, run (use those names in the component)
prompt_text = str(prompt).strip() if prompt else ""
if not prompt_text:
    out = "No prompt provided."
    run_id = get_latest_run_id() or ""
    structure = {}
    answer = out
else:
    structured_prompt, communication, run_id = parse_prompt_to_structured(prompt_text, run_id=None)
    out = communication
    run_id = run_id
    structure = structured_prompt
    answer = communication

# GHPython outputs (order: out, run_id, structure, answer)
a = out
b = run_id
c = structure
d = answer
