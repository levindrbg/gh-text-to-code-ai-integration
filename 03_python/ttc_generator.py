"""
TTC Generator — Create gen_script.py (generated script for truss geometry).

- Loads generator_system_prompt.md and system_outline.json from config. Semantic outline + catalogue at runtime.
- LLM returns script; scrape and save as gen_script.py in 03_python/run_output/[run_id]/.
"""

import os
import json
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional

from ttc_http import urlopen_with_retry

_dir = Path(__file__).resolve().parent


def _load_text(path: Path, encoding: str = "utf-8") -> str:
    with open(path, encoding=encoding) as f:
        return f.read().strip()


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _build_system_prompt(
    semantic_outline: Dict[str, Any],
    cross_section_catalog: List[str],
) -> str:
    """Build system prompt: generator_system_prompt.md + system_outline.json (includes output schema) + catalogue + semantic outline."""
    system_md = _dir / "config" / "generator_system_prompt.md"
    system_outline_path = _dir / "config" / "system_outline.json"
    if not system_md.exists():
        raise FileNotFoundError(f"Generator system prompt not found: {system_md}")

    parts = [_load_text(system_md)]
    if system_outline_path.exists():
        parts.append("\n\n---\n\nSYSTEM CONFIG (system_outline.json):")
        parts.append(json.dumps(_load_json(system_outline_path), indent=2))
    if cross_section_catalog:
        parts.append("\n\n---\n\nCROSS-SECTION CATALOGUE (assign one of these profile names per member):")
        parts.append(json.dumps(cross_section_catalog, indent=2))
    parts.append("\n\n---\n\nSEMANTIC OUTLINE (input for this run):")
    parts.append(json.dumps(semantic_outline, indent=2))
    return "\n".join(parts)


def _scrape_script_from_llm_response(response_text: str) -> str:
    """Extract Python script from LLM response (strip markdown fences)."""
    text = response_text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    start = 1
    end = len(lines)
    for i in range(len(lines) - 1, 0, -1):
        if lines[i].strip().startswith("```"):
            end = i
            break
    return "\n".join(lines[start:end])


def generate_geometry_script(
    semantic_outline: Dict[str, Any],
    run_id: str,
    cross_section_catalog: Optional[List[str]] = None,
    iteration_context: Optional[str] = None,
) -> str:
    """
    Generate gen_script via LLM. System = generator_system_prompt + system_outline + catalogue; user = semantic outline.
    Saves gen_script.py in 03_python/run_output/[run_id]/.
    If iteration_context is provided (ITERATION mode), it is included so the LLM can refine from the previous run.
    Returns the script string.
    """
    API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not API_KEY:
        raise ValueError("Set ANTHROPIC_API_KEY or CLAUDE_API_KEY in .env")

    catalog = cross_section_catalog if cross_section_catalog is not None else []
    system_prompt = _build_system_prompt(semantic_outline, catalog)
    if iteration_context:
        user_prompt = f"""CONTEXT FROM PREVIOUS RUN (use this to refine or iterate; preserve or improve on this):

{iteration_context}

---

Generate a Python script that computes the truss geometry and returns geometric output.

Use the semantic outline below as input parameters. Your script must:
1. Compute node positions and member connectivity (top chord, bottom chord, diagonals).
2. Define support points and load points.
3. Call get_geometric_output() and at the end (if __name__ == "__main__"): (a) print the JSON, and (b) save the same JSON to geometric_output.json in the same directory as the script (use os.path.dirname(os.path.abspath(__file__)) and open(..., "w") with json.dump). Both print and save are required.

SEMANTIC OUTLINE:
{json.dumps(semantic_outline, indent=2)}

Output ONLY executable Python 3 code. No markdown fences, no explanation."""
    else:
        user_prompt = f"""Generate a Python script that computes the truss geometry and returns geometric output.

Use the semantic outline below as input parameters. Your script must:
1. Compute node positions and member connectivity (top chord, bottom chord, diagonals).
2. Define support points and load points.
3. Call get_geometric_output() and at the end (if __name__ == "__main__"): (a) print the JSON, and (b) save the same JSON to geometric_output.json in the same directory as the script (use os.path.dirname(os.path.abspath(__file__)) and open(..., "w") with json.dump). Both print and save are required.

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

    raw = urlopen_with_retry(req)
    data = json.loads(raw)

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
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_str)

    return script_str
