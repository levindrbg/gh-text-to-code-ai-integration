"""
TTC (Text-to-Code) pipeline: Interpreter → Generator → Executor.

Orchestrates the full workflow: natural-language prompt → semantic outline → generated
Python script → geometric output. run_id is created here and passed through; all outputs
are saved under run_output/[run_id]/.

- Interpreter: prompt → semantic_outline.json, communication.txt
- Generator: semantic outline → gen_script.py
- Executor: runs gen_script.py → geometric_output.json, truss_plot.png
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from ttc_interpreter import create_run_id, get_latest_run_id, parse_prompt_to_structured
from ttc_generator import generate_geometry_script
from ttc_executor import run as run_executor, plot_geometric_output

_dir = Path(__file__).resolve().parent


def _run_output_dir() -> Path:
    """Run output base dir. Prefer TTC_03_PYTHON when set (e.g. by GH) so read path matches interpreter write path."""
    env = os.environ.get("TTC_03_PYTHON")
    if env:
        return Path(env).resolve() / "run_output"
    return _dir / "run_output"


def _read_run_file(run_dir: Path, filename: str) -> str:
    """Read a text file from run_dir; return empty string if missing or on error."""
    path = run_dir / filename
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _load_iteration_context(run_id: str) -> str:
    """
    Load run_output files for run_id into a single context string for the LLM.
    Used in ITERATION mode to give the agent the previous run's outputs.
    """
    rid = (run_id or "").strip()
    if not rid:
        return ""
    run_dir = _run_output_dir() / rid
    if not run_dir.exists():
        return ""
    parts = [f"# Context from previous run: {rid}\n"]
    for name, label in [
        ("semantic_outline.json", "Semantic outline"),
        ("communication.txt", "Communication"),
        ("run_commentary.txt", "Run commentary"),
        ("geometric_output.json", "Geometric output"),
        ("analysis_output.json", "Analysis output"),
        ("gen_script.py", "Generated script"),
    ]:
        path = run_dir / name
        if not path.exists():
            continue
        try:
            if path.suffix == ".json":
                with open(path, encoding="utf-8") as f:
                    content = json.dumps(json.load(f), indent=2)
            else:
                content = path.read_text(encoding="utf-8")
        except Exception:
            content = "(read error)"
        parts.append(f"\n## {label}\n```\n{content.strip()}\n```\n")
    return "\n".join(parts).strip()


def load_run_outputs(run_id: str) -> tuple:
    """
    Load communication and run_commentary for run_id from run_output/[run_id]/.
    Returns (communication, run_commentary). Empty strings if run_id empty or files missing.
    """
    rid = (run_id or "").strip()
    if not rid:
        return ("", "")
    run_dir = _run_output_dir() / rid
    comm = _read_run_file(run_dir, "communication.txt")
    commentary = _read_run_file(run_dir, "run_commentary.txt")
    if not commentary.strip() and rid:
        commentary = f"Run {rid} (commentary not saved for this run)."
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
    mode: int = 0,
    api_key: Optional[str] = None,
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
        mode: 0 = NEW TRUSS (default), 1 = ITERATION. In ITERATION mode, files from the latest
            run_output folder are loaded and added as context for both interpreter and generator.
        api_key: Optional Claude/Anthropic API key. Used only if .env does not already set
            ANTHROPIC_API_KEY or CLAUDE_API_KEY (e.g. when running from Grasshopper without .env).

    Returns:
        Dict with: communication, run_id, structure, script_str, geometric_output, error, run_commentary.
    """
    # Use .env key if present; otherwise use api_key from caller (e.g. Grasshopper input)
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")):
        key = (api_key or "").strip()
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key

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
        # In ITERATION mode, load context from the latest run (before we create the new run_id)
        iteration_context = ""
        if mode == 1:
            previous_rid = get_latest_run_id()
            if previous_rid:
                iteration_context = _load_iteration_context(previous_rid)
                log.append(f"[mode] ITERATION — context from {previous_rid}")
            else:
                log.append("[mode] ITERATION — no previous run found, proceeding without context")

        # Create run_id once and use it for the whole pipeline
        rid = run_id if run_id is not None else create_run_id()
        result["run_id"] = rid
        log.append(f"[run_id] {rid}")

        # 1. Interpreter: semantic outline → run_output/[run_id]/
        log.append("Interpreting prompt → semantic outline...")
        semantic_outline, communication, _ = parse_prompt_to_structured(
            prompt.strip(), run_id=rid, iteration_context=iteration_context or None
        )
        result["communication"] = communication
        result["structure"] = semantic_outline
        log.append("Saved run_output/{}/semantic_outline.json, communication.txt".format(rid))

        # 2. Generator: gen_script.py → run_output/[run_id]/
        log.append("Generating gen_script.py...")
        catalog = cross_section_catalog if cross_section_catalog is not None else []
        script_str = generate_geometry_script(
            semantic_outline, run_id=rid, cross_section_catalog=catalog, iteration_context=iteration_context or None
        )
        result["script_str"] = script_str
        log.append("Saved run_output/{}/gen_script.py".format(rid))

        # 3. Executor: run gen_script.py (it writes geometric_output.json in run_dir)
        log.append("Executing gen_script...")
        run_dir = _run_output_dir() / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        run_executor(rid)
        geometric_path = run_dir / "geometric_output.json"
        geometric = {}
        if geometric_path.exists():
            with open(geometric_path, encoding="utf-8") as f:
                geometric = json.load(f)
            log.append("Saved run_output/{}/geometric_output.json".format(rid))
        else:
            log.append("Warning: gen_script did not write geometric_output.json")
        result["geometric_output"] = geometric
        # 4. Plot truss layout and save to run_output/[run_id]/truss_plot.png
        plot_geometric_output(geometric, run_dir)
        log.append("Saved run_output/{}/truss_plot.png".format(rid))
        log.append("Done.")

    except Exception as e:
        result["error"] = str(e)
        result["communication"] = "Pipeline error: " + str(e)
        log.append("Error: {}".format(e))

    result["run_commentary"] = "\n".join(log) if log else "[run_id] {}".format(result.get("run_id", ""))
    # Persist run_commentary and (on error) communication so GH Panels show something
    run_dir = _run_output_dir() / result["run_id"]
    if result["run_id"]:
        run_dir.mkdir(parents=True, exist_ok=True)
        with open(run_dir / "run_commentary.txt", "w", encoding="utf-8") as f:
            f.write(result["run_commentary"])
        if result["error"]:
            with open(run_dir / "communication.txt", "w", encoding="utf-8") as f:
                f.write(result["communication"])
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
