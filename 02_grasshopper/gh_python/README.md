# gh_python

Scripts to **copy-paste into Grasshopper GHPython components** in **TTC_Workflow_V1.gh**.  
These files live in the repo only for editing; they do not run from disk. Path logic inside them is written for the **component runtime** (when pasted into the component), not for running the .py files themselves.

Pipeline code lives in **03_python/**; these components add the repo path, load `.env` from **00_setup**, and call the pipeline.

**Components form a linear chain.** Connect them in series by wiring **run_id** from each component’s output to the next component’s **run_id** input.

---

| File | Role | GH inputs | GH outputs |
|------|------|-----------|------------|
| **ttc_gh_run_pipeline.py** | Run pipeline (creates run_id) | `prompt`, `CroSec` (optional), `mode` (0=NEW TRUSS, 1=ITERATION), `api_key` (optional; used if .env has no key), `run` (Button), `arm` | `run_id` |
| **ttc_gh_fetch_interpreter_returns.py** | Fetch interpreter outputs for run_id | `run_id` | `run_id` (pass-through), `communication`, `run_commentary` |
| **ttc_gh_fetch_Executor.py** | Fetch geometric output for run_id | `run_id` | `run_id` (pass-through), `status`, `Line_Elements`, `Support`, `Loads`, `Load_Points`, `CroSec` |
| **ttc_gh_save_analysis.py** | Save per-member analysis for feedback loop | `run_id`, `Line_Elements`, `CroSec`, `Utilization`, `Displacement_Start`, `Displacement_End`, `Axial_Stress` | `run_id` (pass-through), `status` |
| **ttc_gh_display_truss_plot.py** | Display truss plot image overlay in viewport | `run_id`, `show` (bool) | `status`, `resolved_path` |

---

**Usage**

1. Open **TTC_Workflow_V1.gh** (in `02_grasshopper/`).
2. Add three GHPython components (or two if you skip interpreter returns).
3. Paste **ttc_gh_run_pipeline.py** into the first, **ttc_gh_fetch_interpreter_returns.py** into the second, **ttc_gh_fetch_output.py** into the third.
4. Wire in series: **run_id** out → **run_id** in for each step. Connect **communication** and **run_commentary** to Panels as needed; use **Line_Elements**, **Support**, **Loads**, **Load_Points** for geometry. For the feedback loop: after analysis, wire **run_id**, **Line_Elements**, **CroSec**, and the analysis attribute lists into **ttc_gh_save_analysis**; it writes `analysis_output.json` to `run_output/[run_id]/`.

Repo root and **03_python** are resolved from the component’s runtime (e.g. `os.getcwd()`); if Rhino’s cwd is the repo root or `02_grasshopper`, paths should work. Set `REPO_ROOT` in the scripts if you need a fixed path.
