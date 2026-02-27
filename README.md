**AI-assisted structural design of trusses in Grasshopper.** Describe the structure in natural language; the pipeline turns your text into a Python script, runs it, and outputs geometry plus analysis-ready data for Karamba3D.

---

## What it does

A **text-to-code** workflow runs inside Grasshopper (Rhino 8):

1. **Interpreter** — Your prompt (e.g. “Warren truss, 12 m span, 4 bays”) is sent to an LLM and converted into a structured semantic outline (JSON).
2. **Generator** — A second LLM call produces a Python script that defines the truss (members, supports, loads, cross-sections).
3. **Executor** — The script runs in the project; it writes `geometric_output.json` and optionally a truss plot image.

Outputs are written under `03_python/run_output/[run_id]/`. Grasshopper components read them and expose geometry (lines, supports, loads) and text (communication, commentary). You can plug the geometry into Karamba3D and, in iteration mode, feed analysis results back into the next run.

Optional: a **knowledge base** (e.g. RAG over Pinecone) can provide context to the LLM; the repo includes an `04_knowledge base/` folder and extraction scripts.

---

## Prerequisites

- **Rhino 8** with Grasshopper and **CPython 3** in GHPython components  
- **Python 3** on your machine (for venv and CLI)  
- **Anthropic API key** (Claude) — set in `00_setup/.env` or via the Grasshopper component input  

---

## Installation

1. **Clone the repo** and go to its root.

2. **Create venv and install dependencies** (bash, from repo root):

   ```bash
   bash 00_setup/setup.sh
   ```

   This creates `venv/` and installs from `00_setup/requirements.txt`.  
   Full details (folder layout, activation commands): [00_setup/SETUP.md](00_setup/SETUP.md).

3. **API key**  
   Create `00_setup/.env` with:

   ```text
   ANTHROPIC_API_KEY=your-key-here
   ```

   or use `CLAUDE_API_KEY`. You can also pass the key via the Run Pipeline component input in Grasshopper.

---

## How to run the workflow in Grasshopper

1. **Open** `02_grasshopper/TTC_Workflow_V4.gh` in Rhino 8 (open from the repo so the working directory is the repo root or `02_grasshopper`).

2. **Paste scripts** from `02_grasshopper/gh_python/` into the GHPython components:
   - **Run pipeline** → `ttc_gh_run_pipeline.py` (input: prompt, optional CroSec, mode, Run button)
   - **Fetch interpreter** → `ttc_gh_fetch_interpreter.py` (input: `run_id`)
   - **Fetch executor** → `ttc_gh_fetch_executor.py` (input: `run_id`) → geometry out
   - Optionally: `ttc_gh_save_analysis.py`, `ttc_gh_display_truss_plot.py`

3. **Wire the chain**: connect **run_id** from each component’s output to the next component’s **run_id** input. Use the Run button on the first component to trigger the pipeline.

Component roles, inputs, and outputs are described in [02_grasshopper/gh_python/README.md](02_grasshopper/gh_python/README.md).

---

## Project structure

| Folder | Contents |
|--------|----------|
| `00_setup/` | `setup.sh`, `requirements.txt`, SETUP.md; create `00_setup/.env` here |
| `02_grasshopper/` | Grasshopper definition (e.g. `TTC_Workflow_V4.gh`) and `gh_python/` scripts to paste into GHPython components |
| `03_python/` | Pipeline logic: interpreter, generator, executor; config and schemas; outputs under `run_output/[run_id]/` |
| `04_knowledge base/` | Reference docs and optional scripts to extract text for RAG |

All pipeline logic is in **Python** (no C#). Grasshopper only hosts the UI and calls into `03_python/` via the pasted scripts.

---

## License and use

This repository is intended for teaching and research (e.g. structural design, human–AI workflows in Grasshopper). Use and adapt as needed for your course or project.
