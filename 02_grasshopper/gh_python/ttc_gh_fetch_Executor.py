# GH component: TTC Fetch Executor (geometric_output.json).
# Input run_id → output run_id (pass-through). Reads geometric_output.json from run_output, parses to GH geometry.
# Schema: line_elements [{start, end, cross_section}], support [[x,z]], loads [[x,z,Fz]].
#
# Input  run_id: str (or list with one str from GH wire)
# Output run_id: str (same as input)
# Output status: str
# Output Line_Elements, Support, Loads, Load_Points, CroSec
#   CroSec: list of cross_section name strings, one per line element (same order as Line_Elements)

import json
import os

REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"
RUN_OUTPUT_DIR = os.path.join(REPO_ROOT, "03_python", "run_output")

try:
    import Rhino.Geometry as rg
except ImportError:
    rg = None

# GH may pass a list; take first element so path is a plain string
if run_id is not None and hasattr(run_id, "__getitem__") and not isinstance(run_id, str):
    try:
        run_id = run_id[0]
    except (IndexError, TypeError, KeyError):
        run_id = ""
run_id = str(run_id).strip() if run_id else ""

if not run_id:
    status = "No run_id provided."
    Line_Elements = []
    Support = []
    Loads = []
    Load_Points = []
    CroSec = []
else:
    path = os.path.join(RUN_OUTPUT_DIR, run_id, "geometric_output.json")
    status = "OK"
    Line_Elements = []
    Support = []
    Loads = []
    Load_Points = []
    CroSec = []
    try:
        with open(path, encoding="utf-8") as f:
            geo = json.load(f)
        line_elems = geo.get("line_elements") or []
        if rg:
            for seg in line_elems:
                s, e = seg.get("start"), seg.get("end")
                if s and e and len(s) >= 2 and len(e) >= 2:
                    Line_Elements.append(rg.Line(rg.Point3d(s[0], 0.0, s[1]), rg.Point3d(e[0], 0.0, e[1])))
                CroSec.append(str(seg.get("cross_section") or ""))
            for xz in geo.get("support") or []:
                if xz and len(xz) >= 2:
                    Support.append(rg.Point3d(xz[0], 0.0, xz[1]))
            for ld in geo.get("loads") or []:
                if ld and len(ld) >= 3:
                    Load_Points.append(rg.Point3d(ld[0], 0.0, ld[1]))
                    Loads.append(rg.Vector3d(0.0, 0.0, ld[2]))
        else:
            for seg in line_elems:
                CroSec.append(str(seg.get("cross_section") or ""))
    except Exception as err:
        status = str(err)
