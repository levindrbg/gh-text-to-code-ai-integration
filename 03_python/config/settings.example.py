# Copy to settings.py (gitignored). Claude only — ANTHROPIC_API_KEY or CLAUDE_API_KEY.
# Repo root = two levels up from this file (03_python/config/).

import os
from pathlib import Path

_repo = Path(__file__).resolve().parents[2]  # repo root
try:
    from dotenv import load_dotenv
    load_dotenv(_repo / ".env")
except ImportError:
    pass

os.environ.setdefault("ANTHROPIC_API_KEY", os.environ.get("CLAUDE_API_KEY", ""))
os.environ.setdefault("PINECONE_API_KEY", "")
os.environ.setdefault("PINECONE_INDEX_HOST", "https://your-index.svc.pinecone.io")
