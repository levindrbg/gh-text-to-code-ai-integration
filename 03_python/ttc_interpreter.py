"""
TTC Interpreter — Parses natural language user prompt into structured JSON.

- Run timer: creates run IDs, fetches newest run ID.
- Fetches JSON structure (schema) and asks LLM to fill it.
- LLM fills structure, infers where logical, asks for clarification when needed.
- Output in two parts: (1) Structure = JSON, (2) Answer = communication (questions or summary).

Saves to 03_python/prompt/[run_id]/: structured_prompt.json, communication.txt.
"""

import os
import re
import json
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

def _load_env_file(env_path: Path) -> None:
    """Load KEY=value lines from .env into os.environ (no dotenv package needed)."""
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


# Load API keys from .env at repo root (repo = parent of 03_python)
try:
    _repo = Path(__file__).resolve().parents[1]  # 03_python
    _env_path = _repo.parent / ".env"
    if _env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_env_path)
        except ImportError:
            _load_env_file(_env_path)
        # If key still missing, try manual load (e.g. dotenv didn't run in Rhino)
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")):
            _load_env_file(_env_path)
except Exception as e:
    print(f"Warning: Could not load .env: {e}")


def _prompt_dir() -> Path:
    """Base directory for run folders: 03_python/prompt/."""
    return Path(__file__).resolve().parents[1] / "prompt"


def get_latest_run_id() -> Optional[str]:
    """
    Returns the most recent run_id (newest folder in prompt/ by mtime).
    Returns None if no runs exist.
    """
    base = _prompt_dir()
    if not base.exists():
        return None
    dirs = [d for d in base.iterdir() if d.is_dir() and not d.name.startswith("_")]
    if not dirs:
        return None
    return max(dirs, key=lambda d: d.stat().st_mtime).name


def create_run_id() -> str:
    """
    Creates a new run_id (timestamp-based), creates the folder, returns the id.
    Use this when the user runs the script (e.g. button trigger).
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = _prompt_dir() / run_id
    folder.mkdir(parents=True, exist_ok=True)
    return run_id


def parse_prompt_to_structured(
    user_prompt: str,
    run_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], str, str]:
    """
    Fetches JSON structure (schema), calls Claude to fill it from the user prompt.
    LLM infers where logical; asks for clarification and lists what is missing when needed.

    Args:
        user_prompt: Natural language description of the structure to design.
        run_id: Optional. If None, a new run_id is created (create_run_id).

    Returns:
        (structured_prompt, communication, run_id)
        - structured_prompt: dict conforming to schemas/structured_prompt.json
        - communication: string — either questions for the user (what's missing) or a brief summary
        - run_id: str used for this run
    """
    API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not API_KEY:
        # Try loading .env again from repo root (e.g. when called from GH, dotenv may not have run)
        _env_path = Path(__file__).resolve().parents[1].parent / ".env"
        if _env_path.exists():
            _load_env_file(_env_path)
        API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not API_KEY:
        raise ValueError(
            "No API key found. Add ANTHROPIC_API_KEY or CLAUDE_API_KEY to the .env file in your repo root:\n"
            "  REPO_ROOT\\.env   with a line:  CLAUDE_API_KEY=your-key-here"
        )

    if run_id is None:
        run_id = create_run_id()

    # Fetch JSON structure to parse (schema)
    repo = Path(__file__).resolve().parents[1]
    schema_path = repo / "schemas" / "structured_prompt.json"
    with open(schema_path) as f:
        schema = json.load(f)

    system_prompt = f"""You are a structural engineering assistant. The user describes a structure they want to design (e.g. roof, truss). Your job is to fill a structured JSON from their description.

JSON STRUCTURE TO FILL (conform exactly to this schema):
{json.dumps(schema, indent=2)}

RULES:
1. Fill every field you can infer from the user's message. Use sensible defaults where the schema allows (e.g. loads: snow 1.0, wind 0.5, dead 0.5 kN/m² if not specified).
2. For required fields (typology, span_m, height_m, material): if the user did not specify, infer from context if there is a logical choice; otherwise leave a placeholder and ask in COMMUNICATION.
3. If important fields are missing or ambiguous, list them clearly in COMMUNICATION and ask the user for clarification. Say exactly what is missing (e.g. "Please specify: span in meters, material (steel/timber/cfrp/aluminum).").
4. If you could fill the structure satisfactorily, write a brief summary in COMMUNICATION (e.g. "Filled structure: gable roof, 12 m span, 4 m height, steel; default loads applied.").

OUTPUT FORMAT — you must respond with exactly two blocks in this order:

<STRUCTURE>
{{ ... valid JSON only, no markdown ... }}
</STRUCTURE>

<COMMUNICATION>
Your questions for the user (what is missing), or a brief summary of what you filled. Plain text only.
</COMMUNICATION>

Return only these two blocks. No other text before or after."""

    user_message = f"""User prompt about the structure they want to design:

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

    # Parse <STRUCTURE> and <COMMUNICATION>
    structure_match = re.search(r"<STRUCTURE>\s*([\s\S]*?)\s*</STRUCTURE>", response_text, re.IGNORECASE)
    comm_match = re.search(r"<COMMUNICATION>\s*([\s\S]*?)\s*</COMMUNICATION>", response_text, re.IGNORECASE)

    if not structure_match:
        raise ValueError("No <STRUCTURE> block in Claude response")
    if not comm_match:
        raise ValueError("No <COMMUNICATION> block in Claude response")

    structure_raw = structure_match.group(1).strip()
    communication = comm_match.group(1).strip()

    # Remove markdown code fences if present
    if structure_raw.startswith("```"):
        structure_raw = re.sub(r"^```\w*\n?", "", structure_raw)
        structure_raw = re.sub(r"\n?```\s*$", "", structure_raw)

    try:
        structured_prompt = json.loads(structure_raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in STRUCTURE block: {e}\nContent:\n{structure_raw}")

    # Validate required fields
    required = schema.get("required", [])
    missing = [f for f in required if f not in structured_prompt]
    if missing:
        communication = f"Missing required fields in structure: {missing}. " + communication

    # Save to prompt/[run_id]/
    prompt_dir = _prompt_dir() / run_id
    prompt_dir.mkdir(parents=True, exist_ok=True)
    with open(prompt_dir / "structured_prompt.json", "w") as f:
        json.dump(structured_prompt, f, indent=2)
    with open(prompt_dir / "communication.txt", "w") as f:
        f.write(communication)

    return structured_prompt, communication, run_id


# Entry point when called from GH (04_gh_python loader)
# ctx: user_prompt; after exec: structured_prompt, communication, run_id
if __name__ == "__main__" or True:
    pass
