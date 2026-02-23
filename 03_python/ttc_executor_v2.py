"""
TTC Executor v2 — Standalone script to run gen_script.py (latest run_id).

- Independent of ttc_main; run directly in IDE.
- Essential API: exec_run() → runs gen_script for latest run_id, returns that run_id.
"""

import ast
import os
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent
RUN_OUTPUT = _DIR / "run_output"


def get_latest_run_id() -> str | None:
    """Return the run_id of the most recent run_output subdir that has gen_script.py."""
    if not RUN_OUTPUT.exists():
        return None
    subdirs = [
        d for d in RUN_OUTPUT.iterdir()
        if d.is_dir() and (d / "gen_script.py").exists()
    ]
    if not subdirs:
        return None
    return max(subdirs, key=lambda d: d.stat().st_mtime).name


def load_script(run_id: str) -> str:
    """Load gen_script.py for run_id. UTF-8."""
    path = RUN_OUTPUT / run_id / "gen_script.py"
    if not path.exists():
        raise FileNotFoundError(f"gen_script.py not found: {path}")
    return path.read_text(encoding="utf-8")


def validate_script(script_str: str) -> None:
    """Raises SyntaxError if invalid."""
    ast.parse(script_str)


def execute_script(script_str: str, run_dir: Path) -> None:
    """Execute script in run_dir as cwd so geometric_output.json is written there.
    Injects __name__ = '__main__' so the script's if __name__ == '__main__' block runs and writes files."""
    run_dir = run_dir.resolve()
    script_file = run_dir / "gen_script.py"
    exec_globals = {"__file__": str(script_file), "__name__": "__main__"}
    old_cwd = os.getcwd()
    try:
        os.chdir(run_dir)
        exec(compile(script_str, "<gen_script>", "exec"), exec_globals)
    finally:
        os.chdir(old_cwd)


def exec_run(run_id: str | None = None) -> str:
    """
    Run gen_script for the given run_id, or latest if run_id is None.
    Returns the run_id that was executed.
    """
    rid = run_id or get_latest_run_id()
    if not rid:
        raise FileNotFoundError("No run_output subdir with gen_script.py found.")
    script_str = load_script(rid)
    validate_script(script_str)
    run_dir = RUN_OUTPUT / rid
    execute_script(script_str, run_dir)
    return rid


if __name__ == "__main__":
    try:
        run_id = exec_run()
        print(f"OK: {run_id}")
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
