# Repo setup

## 1. Folder structure

- `00_setup/` — `setup.sh`, `requirements.txt`, `SETUP.md`; you create `.env` here (see step 3)
- `01_docs/` — PDF and goals (gitignored)
- `02_grasshopper/` — Grasshopper workflows; GH Python components call `03_python` scripts
- `03_python/` — all Python scripts called from GH: config, schemas, tests, optimization
- GH Python scripts live in `02_grasshopper/gh_python/` — copy-paste into GHPython components

## 2. Virtual environment and dependencies

From repo root, run the setup script (creates `venv/` and installs from `requirements.txt`):

```bash
bash 00_setup/setup.sh
```

Then activate the venv when you need it:

- **Linux / macOS / Git Bash:** `source venv/bin/activate`
- **Windows PowerShell:** `.\venv\Scripts\Activate.ps1`
- **Windows CMD:** `venv\Scripts\activate.bat`

## 3. API keys (.env)

Either load the Anthropic (Cluade) api key through `.env` from **`00_setup/.env`** or directly in the Grasshopper script.

Example for .env:
==============================================
CLAUDE_API_KEY = [Api Key here]
==============================================

## 5. Running scripts in Grasshopper

- Use **Rhino 8** with **CPython 3** in the GHPython component.
- Open **`02_grasshopper/TTC_Workflow_V4.gh`** and paste the scripts from `02_grasshopper/gh_python/` into each GHPython component (see that folder’s README for the component chain and wiring).
- Open the .gh file from the repo so the current working directory is the repo root or `02_grasshopper`.
- Pipeline code lives in `03_python/`; the GH scripts add the repo to `sys.path` and call it. Edit scripts in your IDE, save, then Recompute in GH.

## Is `exec()` slow or unstable?

- **Stable:** Yes. `exec(open(...).read(), ctx)` is the standard way to run script files from GH; many teams use it.
- **Slow:** Only the first read from disk (a few ms). Execution is the same as imported code. For repeated recomputes, the cost is negligible.
