# GH component: TTC Fetch Interpreter Returns
# Input run_id → output run_id (pass-through). Reads communication.txt and run_commentary.txt from run_output.
# Outputs one string each (newlines collapsed to space) so Panel shows a single item.
#
# Input  run_id: str
# Output run_id: str (same as input)
# Output communication: str
# Output run_commentary: str

REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"
RUN_OUTPUT_DIR = REPO_ROOT + r"\03_python\run_output"

run_id = str(run_id).strip() if run_id else ""

communication = ""
run_commentary = ""
if run_id:
    base = RUN_OUTPUT_DIR + "\\" + run_id
    try:
        with open(base + "\\communication.txt", encoding="utf-8") as f:
            communication = f.read()
        # Collapse newlines to space so GH Panel shows one string, not a list of lines
        communication = " ".join(communication.split())
    except Exception:
        pass
    try:
        with open(base + "\\run_commentary.txt", encoding="utf-8") as f:
            run_commentary = f.read()
        run_commentary = " ".join(run_commentary.split())
    except Exception:
        pass
