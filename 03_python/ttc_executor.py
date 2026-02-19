"""
TTC Executor — Fetch gen script from run_output, validate, execute, return geometric output JSON.

- Loads gen_script.py from 03_python/run_output/[run_id]/.
- Validates script (syntax check).
- Executes and captures output; parses JSON (from get_geometric_output() printed by script).
- Returns dict with line_elements, support, loads for GH (2D [x,z], y=0).
"""

import ast
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict

_dir = Path(__file__).resolve().parent


def load_script(run_id: str) -> str:
    """Load generated script from run_output/[run_id]/gen_script.py."""
    path = _dir / "run_output" / run_id / "gen_script.py"
    if not path.exists():
        raise FileNotFoundError(f"Generated script not found: {path}")
    with open(path) as f:
        return f.read()


def validate_script(script_str: str) -> None:
    """Check script syntax. Raises SyntaxError if invalid."""
    ast.parse(script_str)


def execute_script(script_str: str) -> Dict[str, Any]:
    """
    Execute the generated script and capture stdout.
    Expects script to print a single JSON object (from get_geometric_output()).
    Returns the parsed geometric output dict.
    """
    stdout_capture = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    try:
        exec(compile(script_str, "<gen_script>", "exec"), {})
    finally:
        sys.stdout = old_stdout

    output = stdout_capture.getvalue().strip()
    # Find last line that looks like JSON object
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)

    raise ValueError(f"No valid JSON found in script output. Got:\n{output}")


def run(run_id: str) -> Dict[str, Any]:
    """
    Fetch gen script for run_id, validate, execute, return geometric output.

    Returns:
        Dict with keys: line_elements, support, loads (and any extra from script).
    """
    script_str = load_script(run_id)
    validate_script(script_str)
    return execute_script(script_str)
