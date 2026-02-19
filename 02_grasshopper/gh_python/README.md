# gh_python

Scripts to **copy-paste into Grasshopper GHPython components** in **TTC_Workflow_V1.gh**.  
These files live in the repo only for editing; they do not run from disk. Path logic inside them is written for the **component runtime** (when pasted into the component), not for running the .py files themselves.

Pipeline code lives in **03_python/**; these components add the repo path, load `.env` from **00_setup**, and call the pipeline.

---

| File | Role | GH inputs | GH outputs |
|------|------|-----------|------------|
| **ttc_gh_send_prompt.py** | Send prompt and run full pipeline | `prompt` (str), run (e.g. Button) | `communication`, `run_id`, `run_commentary` |
| **ttc_gh_fetch_output.py** | Fetch Karamba output for a run | `run_id` (str), run (e.g. Button) | `a`=status, `b`=Line_Elements, `c`=Support, `d`=Loads, `e`=Load_Points, `f`=error |

---

**Usage**

1. Open **TTC_Workflow_V1.gh** (in `02_grasshopper/`).
2. Add two GHPython components.
3. Copy the contents of **ttc_gh_send_prompt.py** into the first component; copy **ttc_gh_fetch_output.py** into the second.
4. Wire the **run_id** output of the send-prompt component to the **run_id** input of the fetch-output component when you need Karamba geometry for a run.

Repo root and **03_python** are resolved from the component’s runtime (e.g. `os.getcwd()`); if Rhino’s cwd is the repo root or `02_grasshopper`, paths should work. Set `REPO_ROOT` in the scripts if you need a fixed path.
