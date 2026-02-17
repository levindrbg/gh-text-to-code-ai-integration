# Repo setup

## 1. Folder structure

- `00_setup/` — `.env.example`, `requirements.txt`, `SETUP.md`
- `01_docs/` — PDF and goals (gitignored)
- `02_grasshopper/` — Grasshopper workflows; GH Python components call `03_python` scripts
- `03_python/` — all Python scripts called from GH: config, schemas, tests, optimization
- `04_gh_python/` — scripts to copy into GHPython components
- `05_knowledge_base/` — data for Pinecone vector space (gitignored)

## 2. Virtual environment (venv)

From repo root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r 00_setup\requirements.txt
```

(On Windows CMD: `venv\Scripts\activate.bat`.)

## 3. API keys (.env) and config

1. Copy the example env file to the repo root as `.env`:

   ```powershell
   copy 00_setup\.env.example .env
   ```

2. Edit `.env` and set:
   - `ANTHROPIC_API_KEY` (or `CLAUDE_API_KEY`) — this project uses Claude only, no OpenAI
   - `PINECONE_API_KEY` and `PINECONE_INDEX_HOST` (when you use RAG)

3. Copy the config template so GH and tests can load `.env`:

   ```powershell
   copy 03_python\config\settings.example.py 03_python\config\settings.py
   ```

`.env` and `03_python/config/settings.py` are gitignored. Do not commit them.

## 4. Cursor rules

Project rules for Cursor live in **`.cursorrules`** at the repo root. Cursor picks that file automatically. The full spec (architecture, patterns, schema) is there.

## 5. Running scripts in Grasshopper

- Use **Rhino 8** with **CPython 3** in the GHPython component.
- In each component, use the loader pattern from `.cursorrules`: set `REPO_ROOT` to this repo, then `exec(open(script_path).read(), ctx)`.
- Scripts live in `03_python/`; edit in your IDE, save, then Recompute in GH — no restart needed.

## Is `exec()` slow or unstable?

- **Stable:** Yes. `exec(open(...).read(), ctx)` is the standard way to run script files from GH; many teams use it.
- **Slow:** Only the first read from disk (a few ms). Execution is the same as imported code. For repeated recomputes, the cost is negligible.
