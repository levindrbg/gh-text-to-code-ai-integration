# gh-text-to-code-ai-integration

AI-assisted structural optimization of roof systems (Dachkonstruktion) in Grasshopper. Text-to-code workflow: RAG + LLM → generated Python script → JSON → geometry + Karamba3D.

**Setup:** See [00_setup/SETUP.md](00_setup/SETUP.md) for venv, `.env`, and folder structure.

**Structure:** `02_grasshopper/` = GH workflows (interface); `03_python/` = scripts called from GH; `04_knowledge_base/` = Pinecone data (gitignored). Option A: all logic in Python, loaded via `exec()`. No C#.
