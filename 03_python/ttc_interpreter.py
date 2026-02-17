"""
TTC Interpreter — Parses natural language user prompt into structured JSON.

Called from GH component: receives user_prompt, returns structured_prompt dict.
Saves structured_prompt.json to 03_python/prompt/[run_id]/structured_prompt.json.
"""

import os
import json
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Load config (sets env vars from .env)
try:
    _repo = Path(__file__).resolve().parents[1]
    config_path = _repo / "03_python" / "config" / "settings.py"
    exec(open(config_path).read())
except Exception as e:
    print(f"Warning: Could not load config: {e}")


def parse_prompt_to_structured(user_prompt: str, run_id: str = None) -> Dict[str, Any]:
    """
    Calls Claude to parse natural language prompt into structured JSON.
    
    Args:
        user_prompt: Natural language input from user (e.g., "Gable roof, 12 m span, 4 m height, steel")
        run_id: Optional run identifier. If None, generates timestamp-based ID.
    
    Returns:
        structured_prompt dict conforming to schemas/structured_prompt.json
    
    Raises:
        ValueError: If Claude response is invalid or missing JSON
    """
    API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not API_KEY:
        raise ValueError("Set ANTHROPIC_API_KEY or CLAUDE_API_KEY in .env")
    
    # Generate run_id if not provided
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Load schema for system prompt
    _repo = Path(__file__).resolve().parents[1]
    schema_path = _repo / "03_python" / "schemas" / "structured_prompt.json"
    with open(schema_path) as f:
        schema = json.load(f)
    
    system_prompt = f"""You are a structural engineering prompt parser. Your task: extract structured parameters from a user's natural language description of a roof structure.

SCHEMA (output must conform to this JSON structure):
{json.dumps(schema, indent=2)}

EXTRACTION RULES:
- typology: must be one of {schema['properties']['typology']['enum']}
- span_m: extract span dimension in meters (main direction)
- height_m: extract height/rise in meters
- material: must be one of {schema['properties']['material']['enum']}
- loads: extract snow/wind/dead load if mentioned, otherwise use defaults (snow: 1.0, wind: 0.5, dead: 0.5 kN/m²)
- supports: infer from context (default: pinned at wall plates, no ridge support)
- geometry: extract num_bays, longitudinal_length, rafter_spacing if mentioned
- notes: preserve any additional constraints or requirements

OUTPUT: Return ONLY valid JSON conforming to the schema. No markdown fences, no explanation, just the JSON object.
"""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.1  # Low temperature for consistent parsing
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
    
    # Parse JSON from response (may have markdown fences)
    response_text = response_text.strip()
    if response_text.startswith("```"):
        # Extract JSON from markdown code block
        lines = response_text.splitlines()
        json_lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(json_lines)
    
    try:
        structured_prompt = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from Claude response: {e}\nResponse was:\n{response_text}")
    
    # Validate required fields
    required = schema.get("required", [])
    missing = [f for f in required if f not in structured_prompt]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    
    # Save to 03_python/prompt/[run_id]/structured_prompt.json
    prompt_dir = _repo / "03_python" / "prompt" / run_id
    prompt_dir.mkdir(parents=True, exist_ok=True)
    output_path = prompt_dir / "structured_prompt.json"
    with open(output_path, "w") as f:
        json.dump(structured_prompt, f, indent=2)
    
    return structured_prompt, run_id


# Entry point when called from GH (04_gh_python loader sets ctx and exec's this file)
# ctx must have: user_prompt, optional run_id
# After exec: ctx["structured_prompt"], ctx["run_id"] are set
if __name__ == "__main__" or True:
    pass
