# 02_grasshopper

Grasshopper workflows — the interface of the tool. GH Python components here call Python scripts from `03_python/` via `exec(open(...).read(), ctx)`.

Set `REPO_ROOT` in each component to this repo root so paths resolve to `03_python/` and `03_python/config/settings.py`.
