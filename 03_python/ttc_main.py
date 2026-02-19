"""
Single pipeline: Interpreter → Generator → Executor.

run_id is created in this script and passed through the whole process.
All filled-out data is saved under run_output/[run_id]/.

- Interpreter: semantic outline, communication → run_output/[run_id]/
- Generator: gen_script.py → run_output/[run_id]/
- Executor: runs gen_script, result saved as karamba_output.json → run_output/[run_id]/
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from ttc_interpreter import create_run_id, parse_prompt_to_structured
from ttc_generator import generate_geometry_script
from ttc_executor import run as run_executor

_dir = Path(__file__).resolve().parent


def _run_output_dir() -> Path:
    return _dir / "run_output"


def run(
    prompt: str,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the full pipeline: interpret → generate → execute.
    Creates run_id at start (if not provided) and carries it through.
    All outputs are stored under run_output/[run_id]/.

    Args:
        prompt: User natural-language prompt (e.g. "gable truss 12 m span, steel").
        run_id: Optional. If None, a new run_id is created here and used for the whole process.

    Returns:
        Dict with: communication, run_id, structure, script_str, karamba, error.
    """
    result: Dict[str, Any] = {
        "communication": "",
        "run_id": "",
        "structure": {},
        "script_str": "",
        "karamba": {},
        "error": None,
    }

    try:
        # Create run_id once and use it for the whole pipeline
        rid = run_id if run_id is not None else create_run_id()
        result["run_id"] = rid

        # 1. Interpreter: semantic outline → run_output/[run_id]/
        semantic_outline, communication, _ = parse_prompt_to_structured(prompt.strip(), run_id=rid)
        result["communication"] = communication
        result["structure"] = semantic_outline

        # 2. Generator: gen_script.py → run_output/[run_id]/
        script_str = generate_geometry_script(semantic_outline, run_id=rid)
        result["script_str"] = script_str

        # 3. Executor: run script, get Karamba JSON; save to run_output/[run_id]/karamba_output.json
        karamba = run_executor(rid)
        result["karamba"] = karamba
        run_dir = _run_output_dir() / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        with open(run_dir / "karamba_output.json", "w") as f:
            json.dump(karamba, f, indent=2)

    except Exception as e:
        result["error"] = str(e)
        if not result["communication"]:
            result["communication"] = f"Error: {e}"

    return result


def load_karamba_output(run_id: str) -> Dict[str, Any]:
    """
    Load saved Karamba output for a run (from run_output/[run_id]/karamba_output.json).
    Use this from the GH fetch-output component.
    """
    path = _run_output_dir() / run_id / "karamba_output.json"
    if not path.exists():
        raise FileNotFoundError(f"No karamba output for run_id: {run_id}. Path: {path}")
    with open(path) as f:
        return json.load(f)
