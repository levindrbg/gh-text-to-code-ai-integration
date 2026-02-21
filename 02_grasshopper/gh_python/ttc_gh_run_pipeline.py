# GH component: TTC Run Pipeline
# Copy-paste into a GHPython component. Runs only when Run is clicked (armed + button + prompt).
# Output run_id connects to the next component in the chain (e.g. TTC Fetch Interpreter Returns).
#
# GHPython (CPython 3, Rhino 8):
#   Input  prompt: str — user prompt (e.g. "gable truss 12 m span, steel")
#   Input  CroSec: str or list — cross-section catalogue. Either a single string with lines like
#           family:'HEA' name:'HEA100' country:'EU' material:'Steel' applies to elements:''; 
#           or a list of profile name strings (e.g. ["HEA100","HEA120",...]). Used by Generator to assign one profile per member.
#   Input  run:    wire Button — click to run pipeline (only when armed)
#   Input  arm:    bool — True = armed, False = disarmed
#   Output run_id: str — pass to next component in chain

import os
import re
import sys
from pathlib import Path


def _parse_crosec_catalog(crosec_input):
    """Parse CroSec input to a list of profile name strings. Handles GH catalogue string format or list of names."""
    if crosec_input is None:
        return []
    if hasattr(crosec_input, "__iter__") and not isinstance(crosec_input, str):
        # List of items from GH (e.g. list of strings)
        try:
            items = list(crosec_input)
            if not items:
                return []
            # If first item looks like "family:'HEA' name:'HEA100' ...", parse each
            first = str(items[0])
            if "name:'" in first or 'name:"' in first:
                names = []
                for item in items:
                    s = str(item).strip()
                    m = re.search(r"name:\s*['\"]([^'\"]+)['\"]", s)
                    if m:
                        names.append(m.group(1))
                return names
            # Otherwise treat as list of profile names
            return [str(x).strip() for x in items if str(x).strip()]
        except (TypeError, IndexError):
            return []
    s = str(crosec_input).strip()
    if not s:
        return []
    names = []
    for line in s.replace(";", "\n").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.search(r"name:\s*['\"]([^'\"]+)['\"]", line)
        if m:
            names.append(m.group(1))
    return names

REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"
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

from ttc_main import run as run_pipeline, get_latest_run_id

armed = bool(arm) if arm is not None else False
run_triggered = bool(run) if run is not None else False
prompt_text = str(prompt).strip() if prompt else ""
try:
    crosec_catalog = _parse_crosec_catalog(CroSec) if CroSec is not None else []
except NameError:
    crosec_catalog = []  # CroSec input not yet added to component

do_run = armed and run_triggered and bool(prompt_text)

if do_run:
    try:
        out = run_pipeline(prompt_text, run_id=None, cross_section_catalog=crosec_catalog)
        run_id = out.get("run_id", "")
    except Exception as e:
        run_id = ""
else:
    # When not running, pass through latest run_id so the chain still has a value
    run_id = get_latest_run_id() or ""
