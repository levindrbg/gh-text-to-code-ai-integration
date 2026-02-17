"""
TTC Generator — Generates Python script for geometry computation from structured prompt.

Called from GH component: reads latest structured_prompt.json from 03_python/prompt/[run_id]/,
uses it + optional RAG context to generate executable Python script.
"""

import os
import json
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional

# Load config (sets env vars from .env)
try:
    _repo = Path(__file__).resolve().parents[1]
    config_path = _repo / "03_python" / "config" / "settings.py"
    exec(open(config_path).read())
except Exception as e:
    print(f"Warning: Could not load config: {e}")


def find_latest_structured_prompt() -> tuple[Path, Dict[str, Any]]:
    """
    Finds the most recent structured_prompt.json in 03_python/prompt/.
    
    Returns:
        (path, structured_prompt_dict)
    
    Raises:
        FileNotFoundError: If no structured_prompt.json exists
    """
    prompt_base = Path(__file__).resolve().parents[1] / "prompt"
    
    if not prompt_base.exists():
        raise FileNotFoundError(f"Prompt directory not found: {prompt_base}")
    
    # Find all structured_prompt.json files
    prompt_files = list(prompt_base.glob("*/structured_prompt.json"))
    
    if not prompt_files:
        raise FileNotFoundError(f"No structured_prompt.json found in {prompt_base}")
    
    # Get the most recent one (by modification time)
    latest = max(prompt_files, key=lambda p: p.stat().st_mtime)
    
    with open(latest) as f:
        structured_prompt = json.load(f)
    
    return latest, structured_prompt


def generate_geometry_script(
    structured_prompt: Dict[str, Any],
    context_chunks: Optional[List[Dict[str, Any]]] = None,
    run_id: Optional[str] = None
) -> str:
    """
    Calls Claude to generate Python script that computes roof geometry from structured prompt.
    
    Args:
        structured_prompt: Parsed prompt dict (from ttc_interpreter)
        context_chunks: Optional RAG context chunks (from rag_query)
        run_id: Optional run identifier for logging
    
    Returns:
        Generated Python script string (executable, outputs JSON)
    """
    API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not API_KEY:
        raise ValueError("Set ANTHROPIC_API_KEY or CLAUDE_API_KEY in .env")
    
    # Load output schema reference
    _repo = Path(__file__).resolve().parents[1]
    schema_path = _repo / "03_python" / "schemas" / "structural_output.json"
    with open(schema_path) as f:
        output_schema = json.load(f)
    
    # Build context text from RAG chunks
    context_text = ""
    if context_chunks:
        context_text = "\n\n---\n\n".join(c.get("text", "") for c in context_chunks)
    
    system_prompt = f"""You are a structural engineering code generator for Grasshopper/Karamba3D.
Your task: write a self-contained Python 3 script that generates a structural roof system from structured parameters.

STRUCTURED PROMPT (input parameters):
{json.dumps(structured_prompt, indent=2)}

KNOWLEDGE BASE CONTEXT (use this to ground your implementation):
{context_text if context_text else "No RAG context provided. Use standard structural engineering principles."}

OUTPUT SCHEMA (your script must print JSON conforming to this):
{json.dumps(output_schema, indent=2)}

SCRIPT REQUIREMENTS:
- Output ONLY executable Python 3 code, no markdown fences, no explanation
- The script must end by printing a single JSON string conforming to the structural_output schema
- Use only: numpy, scipy, json, math, os, sys (no matplotlib, no pandas)
- All units: meters for geometry, kN for forces, MPa for stress, cm² for cross-sections
- Include a main() function; call it at the end with: if __name__ == "__main__" or always
- Compute node positions based on typology, span, height
- Generate initial member connectivity (ridge beams, rafters, purlins, etc.)
- Include loads based on structured_prompt loads (snow, wind, dead load)
- Set is_support=True for wall plate nodes (and ridge if supports.at_ridge is True)
- Output JSON with nodes, members, loads arrays conforming to schema
"""

    user_prompt = f"""Generate a Python script that creates a {structured_prompt.get('typology', 'gable_roof')} roof structure with:
- Span: {structured_prompt.get('span_m')} m
- Height: {structured_prompt.get('height_m')} m
- Material: {structured_prompt.get('material')}
- Loads: {json.dumps(structured_prompt.get('loads', {}), indent=2)}

Additional parameters: {json.dumps(structured_prompt.get('geometry', {}), indent=2)}
"""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.2
    }).encode()
    
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    )
    
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    
    # Extract text from Claude response
    response_text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            response_text = block["text"]
            break
    
    if not response_text:
        raise ValueError("No text content in Claude response")
    
    # Clean markdown fences if present
    response_text = response_text.strip()
    if response_text.startswith("```python"):
        lines = response_text.splitlines()
        json_lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(json_lines)
    elif response_text.startswith("```"):
        lines = response_text.splitlines()
        json_lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(json_lines)
    
    return response_text


# Entry point for GH component
if __name__ == "__main__" or True:
    # When called from GH:
    # Option 1: Pass run_id explicitly
    # ctx = {"run_id": "test_001", "context_chunks": [...]}
    # exec(open("ttc_generator.py").read(), ctx)
    # script_str = ctx.get("script_str")
    
    # Option 2: Auto-find latest structured_prompt.json
    # ctx = {"context_chunks": [...]}
    # exec(open("ttc_generator.py").read(), ctx)
    # script_str = ctx.get("script_str")
    pass
