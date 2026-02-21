"""
TTC Interpreter — Create full semantic outline of Truss from user prompt.

- Fetches semantic outline schema from config/semantic_outline.json and system prompt from config/interpreter_system_prompt.md.
- Calls LLM to fill the form from the user prompt.
- Saves semantic outline and communication in 03_python/run_output/[run_id]/.
"""

import os
import re
import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

_CONFIG_DIR = "config"
_SEMANTIC_OUTLINE_BASENAME = "semantic_outline.json"

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


# Repo root for .env (00_setup/.env)
def _repo_root() -> Path:
    try:
        p = Path(__file__).resolve()
        if p.name.endswith(".py") and p.parent.name == "03_python":
            return p.parents[1]
    except Exception:
        pass
    return Path(os.getcwd()) if os.getcwd() else Path(sys.path[0]).parents[1] if len(sys.path) > 0 else Path(".").resolve()

_env_path = _repo_root() / "00_setup" / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_env_path))
    except ImportError:
        pass
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")):
        _load_env_file(_env_path)


def _python_dir() -> Path:
    """03_python directory. Resolve via config/semantic_outline.json."""
    config_file = _config_semantic_outline_path()
    if config_file and config_file.exists():
        return config_file.parent.parent  # config -> 03_python
    env_base = os.environ.get("TTC_03_PYTHON")
    if env_base:
        return Path(env_base).resolve()
    return Path(__file__).resolve().parent


def _config_semantic_outline_path() -> Optional[Path]:
    """Path to config/semantic_outline.json; None if not found."""
    candidates = []
    try:
        candidates.append(Path(__file__).resolve().parent / _CONFIG_DIR / _SEMANTIC_OUTLINE_BASENAME)
    except Exception:
        pass
    if sys.path:
        candidates.append(Path(sys.path[0]).resolve() / _CONFIG_DIR / _SEMANTIC_OUTLINE_BASENAME)
    cwd = Path(os.getcwd()).resolve()
    candidates.extend([
        cwd / "03_python" / _CONFIG_DIR / _SEMANTIC_OUTLINE_BASENAME,
        cwd / _CONFIG_DIR / _SEMANTIC_OUTLINE_BASENAME,
    ])
    try:
        for parent in Path(__file__).resolve().parents:
            candidates.append(parent / "03_python" / _CONFIG_DIR / _SEMANTIC_OUTLINE_BASENAME)
    except Exception:
        pass
    for p in candidates:
        if p.exists():
            return p
    return None


def _run_output_dir() -> Path:
    """Base directory for run output: 03_python/run_output/."""
    d = _python_dir() / "run_output"
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
    """Create new run_id: short date + index (e.g. 260219_01_, 260219_02_)."""
    date_prefix = datetime.now().strftime("%y%m%d")  # 260219
    base = _run_output_dir()
    base.mkdir(parents=True, exist_ok=True)
    existing = [d.name for d in base.iterdir() if d.is_dir() and d.name.startswith(date_prefix + "_")]
    indices = []
    for name in existing:
        try:
            # name like 260219_01_ or 260219_02_
            parts = name.split("_")
            if len(parts) >= 2 and parts[1].isdigit():
                indices.append(int(parts[1]))
        except (ValueError, IndexError):
            pass
    next_idx = (max(indices) + 1) if indices else 1
    run_id = f"{date_prefix}_{next_idx:02d}_"
    folder = base / run_id
    folder.mkdir(parents=True, exist_ok=True)
    return run_id


def _load_semantic_outline() -> Dict[str, Any]:
    """Load semantic outline (form schema) from config/semantic_outline.json."""
    path = _config_semantic_outline_path()
    if not path or not path.exists():
        base = _python_dir()
        path = base / _CONFIG_DIR / _SEMANTIC_OUTLINE_BASENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Semantic outline not found. Expected config/semantic_outline.json under 03_python. Tried: {path}"
        )
    with open(path) as f:
        return json.load(f)


def parse_prompt_to_structured(
    user_prompt: str,
    run_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], str, str]:
    """
    Create full semantic outline of Truss from user prompt.

    - Fetches semantic outline schema from config/semantic_outline.json and system prompt from config/interpreter_system_prompt.md.
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
            "No API key. Add ANTHROPIC_API_KEY or CLAUDE_API_KEY to .env in 00_setup."
        )

    if run_id is None:
        run_id = create_run_id()

    schema = _load_semantic_outline()
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    schema_str = json.dumps({"required": required, "properties": properties}, indent=2)

    system_prompt_path = _python_dir() / _CONFIG_DIR / "interpreter_system_prompt.md"
    if system_prompt_path.exists():
        with open(system_prompt_path, encoding="utf-8") as f:
            system_prompt = f.read().strip()
        system_prompt += "\n\n---\n\nJSON structure to fill (required and properties):\n"
        system_prompt += schema_str
    else:
        raise FileNotFoundError(f"Interpreter system prompt not found: {system_prompt_path}")

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

    if structure_match:
        structure_raw = structure_match.group(1).strip()
        communication = comm_match.group(1).strip() if comm_match else ""
    else:
        # Fallback: prompt says "return only the filled JSON" — try to find a JSON object in the response
        structure_raw = response_text.strip()
        if structure_raw.startswith("```"):
            structure_raw = re.sub(r"^```\w*\n?", "", structure_raw)
            structure_raw = re.sub(r"\n?```\s*$", "", structure_raw)
        # Find first {...} that looks like JSON (greedy match from first { to last })
        obj_match = re.search(r"\{[\s\S]*\}", structure_raw)
        if obj_match:
            structure_raw = obj_match.group(0)
        communication = ""

    if structure_raw.startswith("```"):
        structure_raw = re.sub(r"^```\w*\n?", "", structure_raw)
        structure_raw = re.sub(r"\n?```\s*$", "", structure_raw)

    try:
        semantic_outline = json.loads(structure_raw)
    except json.JSONDecodeError as e:
        snippet = (response_text[:500] + "...") if len(response_text) > 500 else response_text
        raise ValueError(
            f"Invalid JSON from Interpreter: {e}\nContent used:\n{structure_raw[:800]}...\n\nFull response snippet:\n{snippet}"
        )

    missing = [f for f in required if f not in semantic_outline]
    if missing:
        communication = f"Missing required fields: {missing}. " + communication

    # One continuous line in file so GH and other readers get a single string
    communication_one_line = " ".join(communication.split())

    out_dir = _run_output_dir() / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "semantic_outline.json", "w", encoding="utf-8") as f:
        json.dump(semantic_outline, f, indent=2)
    with open(out_dir / "communication.txt", "w", encoding="utf-8") as f:
        f.write(communication_one_line)

    return semantic_outline, communication, run_id
