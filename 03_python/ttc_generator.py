"""
TTC Generator — Create gen_script.py (generated script for truss geometry).

- Fetches boundary conditions and geometric output structure from config.
- System prompt: boundary conditions + system_prompt.txt + gen_script_output_function.txt.
- User prompt: semantic outline from Interpreter.
- LLM returns script; scrape and save as gen_script.py in 03_python/run_output/[run_id]/.
"""

import os
import json
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

_dir = Path(__file__).resolve().parent


def _load_text(path: Path) -> str:
    with open(path) as f:
        return f.read().strip()


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _build_system_prompt(semantic_outline: Dict[str, Any]) -> str:
    """Build system prompt from config files + semantic outline (for context)."""
    system_txt = _dir / "config" / "system_prompt.txt"
    output_fn_txt = _dir / "config" / "gen_script_output_function.txt"
    boundary_path = _dir / "config" / "boundary_conditions.json"
    geometric_path = _dir / "config" / "geometric_output_structure.json"

    parts = []
    parts.append(_load_text(system_txt))
    parts.append("\n\nBOUNDARY CONDITIONS AND REQUIREMENTS:")
    if boundary_path.exists():
        parts.append(json.dumps(_load_json(boundary_path), indent=2))
    parts.append("\n\nGEOMETRIC OUTPUT STRUCTURE (what your script must provide):")
    if geometric_path.exists():
        parts.append(json.dumps(_load_json(geometric_path), indent=2))
    parts.append("\n\nHARDCODED OUTPUT FUNCTION (your script MUST include and use this):")
    parts.append(_load_text(output_fn_txt))
    parts.append("\n\nSEMANTIC OUTLINE (input parameters for this run):")
    parts.append(json.dumps(semantic_outline, indent=2))
    return "\n".join(parts)


def _scrape_script_from_llm_response(response_text: str) -> str:
    """Extract Python script from LLM response (strip markdown fences)."""
    text = response_text.strip()
    if text.startswith("```python"):
        lines = text.splitlines()
        start = 1 if lines[0].strip().startswith("```") else 0
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        return "\n".join(lines[start:end])
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        return "\n".join(lines[start:end])
    return text


def generate_geometry_script(
    semantic_outline: Dict[str, Any],
    run_id: str,
) -> str:
    """
    Generate gen script via LLM. User prompt = semantic outline; system = boundary conditions + system prompt file + output function.
    Saves script as [run_id]_gen_script.py in 03_python/run_output.
    Returns the script string.
    """
    API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not API_KEY:
        raise ValueError("Set ANTHROPIC_API_KEY or CLAUDE_API_KEY in .env")

    system_prompt = _build_system_prompt(semantic_outline)
    user_prompt = f"""Generate a Python script that computes the truss geometry and returns geometric output.

Use the semantic outline below as input parameters. Your script must:
1. Compute node positions and member connectivity (top chord, bottom chord, diagonals).
2. Define support points and load points.
3. Call get_geometric_output() and print its JSON at the end (if __name__ == "__main__": ... print(json.dumps(get_geometric_output()))).

SEMANTIC OUTLINE:
{json.dumps(semantic_outline, indent=2)}

Output ONLY executable Python 3 code. No markdown fences, no explanation."""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())

    response_text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            response_text = block["text"]
            break

    if not response_text:
        raise ValueError("No text content in Claude response")

    script_str = _scrape_script_from_llm_response(response_text)

    run_dir = _dir / "run_output" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    script_path = run_dir / "gen_script.py"
    with open(script_path, "w") as f:
        f.write(script_str)

    return script_str


def load_generated_script(run_id: str) -> str:
    """Load gen_script.py from run_output/[run_id]/."""
    path = _dir / "run_output" / run_id / "gen_script.py"
    if not path.exists():
        raise FileNotFoundError(f"Generated script not found: {path}")
    with open(path) as f:
        return f.read()
