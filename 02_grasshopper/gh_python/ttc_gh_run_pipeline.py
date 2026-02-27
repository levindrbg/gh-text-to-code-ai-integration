"""
GHPython component: TTC Run Pipeline

Runs the full TTC pipeline (Interpreter → Generator → Executor) when Run is clicked (armed + button + prompt).
Creates run_id and writes all outputs to run_output/[run_id]/.

Inputs:  prompt (str), CroSec (optional), mode (0=NEW TRUSS, 1=ITERATION), api_key (optional), run (Button), arm (bool)
Outputs: run_id (str) — pass to next component in chain
"""

import os
import re
import sys
from pathlib import Path

# State file for rising-edge detection: run pipeline only when run goes False → True (one API run per click).
_TTC_RUN_STATE_FILE = None  # set after REPO_ROOT is defined


def _run_trigger_rising_edge(run_val):
    """Return True only when run_val is True this time and was False last time (single run per button click)."""
    global _TTC_RUN_STATE_FILE
    if _TTC_RUN_STATE_FILE is None:
        return bool(run_val)  # fallback if state file not set
    try:
        prev = _TTC_RUN_STATE_FILE.read_text().strip().lower() == "true"
    except Exception:
        prev = False
    is_run = bool(run_val)
    try:
        _TTC_RUN_STATE_FILE.write_text("True" if is_run else "False", encoding="utf-8")
    except Exception:
        pass
    return is_run and not prev


def _parse_crosec_catalog(crosec_input):
    """Parse CroSec input to a list of profile name strings. Handles GH catalogue string format or list of names."""
    if crosec_input is None:
        return []
    if hasattr(crosec_input, "__iter__") and not isinstance(crosec_input, str):
        try:
            items = list(crosec_input)
            if not items:
                return []
            first = str(items[0])
            if "name:'" in first or 'name:"' in first:
                names = []
                for item in items:
                    s = str(item).strip()
                    m = re.search(r"name:\s*['\"]([^'\"]+)['\"]", s)
                    if m:
                        names.append(m.group(1))
                return names
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

# Resolve repo root from cwd (repo root or 02_grasshopper when GH runs)
_cwd = Path(os.getcwd()).resolve()
if (_cwd / "03_python").is_dir():
    REPO_ROOT = str(_cwd)
elif _cwd.name == "02_grasshopper" and (_cwd.parent / "03_python").is_dir():
    REPO_ROOT = str(_cwd.parent)
else:
    REPO_ROOT = str(_cwd)

# Rising-edge state file (run only once per button click)
_TTC_RUN_STATE_FILE = Path(REPO_ROOT) / ".ttc_gh_run_prev"

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
run_val = bool(run) if run is not None else False
run_triggered = _run_trigger_rising_edge(run_val)  # True only on rising edge (one run per click)
prompt_text = str(prompt).strip() if prompt else ""
try:
    crosec_catalog = _parse_crosec_catalog(CroSec) if CroSec is not None else []
except NameError:
    crosec_catalog = []  # CroSec input not yet added to component
try:
    mode_val = int(mode) if mode is not None else 0
except (TypeError, ValueError):
    mode_val = 0
if mode_val not in (0, 1):
    mode_val = 0
api_key_str = str(api_key).strip() if api_key is not None else ""

do_run = armed and run_triggered and bool(prompt_text)

if do_run:
    try:
        out = run_pipeline(prompt_text, run_id=None, cross_section_catalog=crosec_catalog, mode=mode_val, api_key=api_key_str or None)
        run_id = out.get("run_id", "")
    except Exception as e:
        run_id = ""
else:
    # When not running, pass through latest run_id so the chain still has a value
    run_id = get_latest_run_id() or ""
