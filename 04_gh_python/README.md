# 04_gh_python

Scripts to **copy into Grasshopper GHPython components** (one script per node).  
They set `REPO_ROOT`, load config, and call the corresponding logic in `03_python/`.

| File | Step | GH inputs | GH outputs |
|------|------|-----------|------------|
| ttc_gh_interpreter.py | Interpreter | x=prompt (run via button/recompute) | a=Answer, b=Structure, c=run_id |
| ttc_gh_generator.py | Generator | x=run_id, y=context_chunks | a=script_str |
| ttc_gh_rag.py | RAG query | x=user_prompt, y=top_k | a=context_chunks |
| ttc_gh_executor.py | Script executor | x=script_str | a=structural_result |
| ttc_gh_optimization.py | Optimization | x=structural_result | a=structural_result |
| ttc_gh_geometry.py | Geometry | x=structural_result | a=lines, b=points |

Set `REPO_ROOT` in each script to your repo path (or wire from a Panel).
