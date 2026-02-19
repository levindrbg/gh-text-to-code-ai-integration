"""
TTC Interpreter — Create full semantic outline of Truss from user prompt.

- Fetches structure outline (form) from empty_schemas/structure_outline.json.
- Calls LLM to fill the form from the user prompt.
- Saves semantic outline and communication in 03_python/run_output/[run_id]/.
"""

import os
import re
import json
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

def _load_env_file(env_path: Path) -> None:
    """Load KEY=value lines from .env into os.environ."""
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1].replace('\\"', '"')
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1].replace("\\'", "'")
                    if key:
                        os.environ.setdefault(key, value)
    except Exception as e:
        print(f"Warning: Could not read .env: {e}")


_repo = Path(__file__).resolve().parents[1]
_env_path = _repo.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")):
        _load_env_file(_env_path)


def _run_output_dir() -> Path:
    """Base directory for run output: 03_python/run_output/."""
    d = Path(__file__).resolve().parent / "run_output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_latest_run_id() -> Optional[str]:
    """Most recent run_id (newest folder in run_output by mtime)."""
    base = _run_output_dir()
    dirs = [d for d in base.iterdir() if d.is_dir() and not d.name.startswith("_")]
    if not dirs:
        return None
    return max(dirs, key=lambda d: d.stat().st_mtime).name


def create_run_id() -> str:
    """Create new run_id (timestamp), create folder in run_output, return id."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = _run_output_dir() / run_id
    folder.mkdir(parents=True, exist_ok=True)
    return run_id


def _load_structure_outline() -> Dict[str, Any]:
    """Fetch structure outline (form) from empty_schemas/structure_outline.json."""
    path = Path(__file__).resolve().parent / "empty_schemas" / "structure_outline.json"
    if not path.exists():
        raise FileNotFoundError(f"Structure outline not found: {path}")
    with open(path) as f:
        return json.load(f)


def parse_prompt_to_structured(
    user_prompt: str,
    run_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], str, str]:
    """
    Create full semantic outline of Truss from user prompt.

    - Fetches structure outline from empty_schemas/structure_outline.json.
    - Asks LLM to fill the form; infers where logical, asks for clarification otherwise.
    - Saves in 03_python/run_output/[run_id]/: semantic_outline.json, communication.txt.

    Returns:
        (semantic_outline, communication, run_id)
    """
    API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not API_KEY:
        _load_env_file(_env_path)
        API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not API_KEY:
        raise ValueError(
            "No API key. Add ANTHROPIC_API_KEY or CLAUDE_API_KEY to .env at repo root."
        )

    if run_id is None:
        run_id = create_run_id()

    schema = _load_structure_outline()
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    system_prompt = f"""You are a structural engineering assistant. The user describes a truss/structure. Fill a structured JSON from their description.

JSON STRUCTURE TO FILL (conform to this schema):
{json.dumps({"required": required, "properties": properties}, indent=2)}

RULES:
1. Fill every field you can infer. Use sensible defaults where appropriate (e.g. loads: snow 1.0, wind 0.5, dead 0.5 kN/m² if not specified).
2. If required fields are missing or ambiguous, list them in COMMUNICATION and ask for clarification.
3. If you filled the structure satisfactorily, write a brief summary in COMMUNICATION.

OUTPUT FORMAT — respond with exactly two blocks in this order:

<STRUCTURE>
{{ ... valid JSON only, no markdown ... }}
</STRUCTURE>

<COMMUNICATION>
Questions for the user or brief summary. Plain text only.
</COMMUNICATION>

Return only these two blocks. No other text before or after."""

    user_message = f"""User prompt about the structure they want:

{user_prompt}

Fill the JSON structure. If something is missing or unclear, say so in COMMUNICATION."""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
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

    structure_match = re.search(r"<STRUCTURE>\s*([\s\S]*?)\s*</STRUCTURE>", response_text, re.IGNORECASE)
    comm_match = re.search(r"<COMMUNICATION>\s*([\s\S]*?)\s*</COMMUNICATION>", response_text, re.IGNORECASE)

    if not structure_match:
        raise ValueError("No <STRUCTURE> block in Claude response")
    if not comm_match:
        raise ValueError("No <COMMUNICATION> block in Claude response")

    structure_raw = structure_match.group(1).strip()
    communication = comm_match.group(1).strip()

    if structure_raw.startswith("```"):
        structure_raw = re.sub(r"^```\w*\n?", "", structure_raw)
        structure_raw = re.sub(r"\n?```\s*$", "", structure_raw)

    try:
        semantic_outline = json.loads(structure_raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in STRUCTURE block: {e}\nContent:\n{structure_raw}")

    missing = [f for f in required if f not in semantic_outline]
    if missing:
        communication = f"Missing required fields: {missing}. " + communication

    out_dir = _run_output_dir() / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "semantic_outline.json", "w") as f:
        json.dump(semantic_outline, f, indent=2)
    with open(out_dir / "communication.txt", "w") as f:
        f.write(communication)

    return semantic_outline, communication, run_id
