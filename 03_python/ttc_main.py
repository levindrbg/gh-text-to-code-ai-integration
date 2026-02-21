"""
Single pipeline: Interpreter → Generator → Executor.

run_id is created in this script and passed through the whole process.
All filled-out data is saved under run_output/[run_id]/.

- Interpreter: semantic outline, communication → run_output/[run_id]/
- Generator: gen_script.py → run_output/[run_id]/
- Executor: runs gen_script, result saved as geometric_output.json → run_output/[run_id]/
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from ttc_interpreter import create_run_id, get_latest_run_id, parse_prompt_to_structured
from ttc_generator import generate_geometry_script
from ttc_executor import run as run_executor

_dir = Path(__file__).resolve().parent


def _run_output_dir() -> Path:
    """Run output base dir. Prefer TTC_03_PYTHON when set (e.g. by GH) so read path matches interpreter write path."""
    env = os.environ.get("TTC_03_PYTHON")
    if env:
        return Path(env).resolve() / "run_output"
    return _dir / "run_output"


def load_run_outputs(run_id: str) -> tuple:
    """
    Load communication and run_commentary for a given run_id from run_output/[run_id]/.
    Returns (communication, run_commentary). Empty strings if run_id is empty or files missing.
    """
    rid = (run_id or "").strip()
    if not rid:
        return ("", "")
    run_dir = _run_output_dir() / rid
    comm = ""
    if (run_dir / "communication.txt").exists():
        try:
            with open(run_dir / "communication.txt", encoding="utf-8") as f:
                comm = f.read()
        except Exception:
            pass
    commentary = ""
    if (run_dir / "run_commentary.txt").exists():
        try:
            with open(run_dir / "run_commentary.txt", encoding="utf-8") as f:
                commentary = f.read()
        except Exception:
            pass
    if not commentary.strip() and rid:
        commentary = "Run {} (commentary not saved for this run).".format(rid)
    return (comm, commentary)


def load_latest_outputs() -> tuple:
    """
    Load communication, run_id, run_commentary from the latest run in run_output.
    Returns (run_id, communication, run_commentary). Empty strings if no runs exist.
    """
    rid = get_latest_run_id()
    if not rid:
        return ("", "", "")
    comm, commentary = load_run_outputs(rid)
    return (rid, comm, commentary)


def run(
    prompt: str,
    run_id: Optional[str] = None,
    cross_section_catalog: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Run the full pipeline: interpret → generate → execute.
    Creates run_id at start (if not provided) and carries it through.
    All outputs are stored under run_output/[run_id]/.

    Args:
        prompt: User natural-language prompt (e.g. "gable truss 12 m span, steel").
        run_id: Optional. If None, a new run_id is created here and used for the whole process.
        cross_section_catalog: Optional list of profile name strings (e.g. ["HEA100", "HEA120", ...])
            for the generator to assign to members. Passed from GH "CroSec" input when provided.

    Returns:
        Dict with: communication, run_id, structure, script_str, geometric_output, error, run_commentary.
    """
    result: Dict[str, Any] = {
        "communication": "",
        "run_id": "",
        "structure": {},
        "script_str": "",
        "geometric_output": {},
        "error": None,
        "run_commentary": "",
    }
    log: list = []

    try:
        # Create run_id once and use it for the whole pipeline
        rid = run_id if run_id is not None else create_run_id()
        result["run_id"] = rid
        log.append(f"[run_id] {rid}")

        # 1. Interpreter: semantic outline → run_output/[run_id]/
        log.append("Interpreting prompt → semantic outline...")
        semantic_outline, communication, _ = parse_prompt_to_structured(prompt.strip(), run_id=rid)
        result["communication"] = communication
        result["structure"] = semantic_outline
        log.append("Saved run_output/{}/semantic_outline.json, communication.txt".format(rid))

        # 2. Generator: gen_script.py → run_output/[run_id]/
        log.append("Generating gen_script.py...")
        catalog = cross_section_catalog if cross_section_catalog is not None else []
        script_str = generate_geometry_script(semantic_outline, run_id=rid, cross_section_catalog=catalog)
        result["script_str"] = script_str
        log.append("Saved run_output/{}/gen_script.py".format(rid))

        # 3. Executor: run script, get geometric JSON; save to run_output/[run_id]/geometric_output.json
        log.append("Executing gen_script...")
        geometric = run_executor(rid)
        result["geometric_output"] = geometric
        run_dir = _run_output_dir() / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        with open(run_dir / "geometric_output.json", "w") as f:
            json.dump(geometric, f, indent=2)
        log.append("Saved run_output/{}/geometric_output.json".format(rid))
        log.append("Done.")

    except Exception as e:
        result["error"] = str(e)
        result["communication"] = ""  # never put errors in communication; only in run_commentary
        log.append("Error: {}".format(e))

    result["run_commentary"] = "\n".join(log) if log else "[run_id] {}".format(result.get("run_id", ""))
    # Persist run_commentary so GH can show "latest run" after button pulse
    run_dir = _run_output_dir() / result["run_id"]
    if result["run_id"]:
        run_dir.mkdir(parents=True, exist_ok=True)
        with open(run_dir / "run_commentary.txt", "w", encoding="utf-8") as f:
            f.write(result["run_commentary"])
    return result


def load_geometric_output(run_id: str) -> Dict[str, Any]:
    """
    Load geometric output for a run (from run_output/[run_id]/geometric_output.json).
    2D truss in [x, z] plane; use y=0 when building Rhino geometry.
    """
    path = _run_output_dir() / run_id / "geometric_output.json"
    if not path.exists():
        raise FileNotFoundError(f"No geometric output for run_id: {run_id}. Path: {path}")
    with open(path) as f:
        return json.load(f)
