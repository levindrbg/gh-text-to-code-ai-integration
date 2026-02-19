# GH component 2: Fetch gen_script output (Karamba data) for a run_id.
# This file is in the repo (02_grasshopper) only for editing. Copy-paste its contents
# into a GHPython component in TTC_Workflow_V1.gh. Path logic must work when run
# inside the component (__file__ may be absent).
#
# GHPython (CPython 3, Rhino 8):
#   Input  run_id: str — from the send-prompt component (output run_id)
#   Input  run:    wire Button — click to fetch
#   Output a: communication / status (str)
#   Output b: Line_Elements (list of Rhino.Geometry.Line)
#   Output c: Support (list of {point, type})
#   Output d: Loads (list of {point, Fx_kN, Fy_kN, Fz_kN})
#   Output e: Load_Points (list of Rhino.Geometry.Point3d)
#   Output f: error (str or None)

import os
import sys
from pathlib import Path

# Repo root for component runtime: cwd-based (__file__ unreliable when pasted)
def _repo_root():
    try:
        p = Path(__file__).resolve()
        if "02_grasshopper" in p.parts:
            return p.parent.parent
    except Exception:
        pass
    cwd = Path(os.getcwd()).resolve()
    if cwd.name == "02_grasshopper":
        return cwd.parent
    if (cwd / "03_python").is_dir() and (cwd / "00_setup").is_dir():
        return cwd
    return cwd

REPO_ROOT = str(_repo_root())
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
os.environ["TTC_03_PYTHON"] = os.path.abspath(SCRIPTS_DIR)

from ttc_main import load_karamba_output

try:
    import Rhino.Geometry as rg
except ImportError:
    rg = None


def _parse_karamba_to_gh(karamba):
    """Parse gen script output into Karamba workflow inputs."""
    line_elements = []
    support = []
    loads = []
    load_points = []

    if not karamba or not rg:
        return line_elements, support, loads, load_points

    for seg in karamba.get("line_elements") or []:
        s, e = seg.get("start"), seg.get("end")
        if s and e and len(s) >= 3 and len(e) >= 3:
            line_elements.append(rg.Line(rg.Point3d(s[0], s[1], s[2]), rg.Point3d(e[0], e[1], e[2])))

    for sup in karamba.get("support") or []:
        pt = sup.get("point")
        if pt and len(pt) >= 3:
            support.append({"point": rg.Point3d(pt[0], pt[1], pt[2]), "type": sup.get("type", "pinned")})

    for ld in karamba.get("loads") or []:
        pt = ld.get("point")
        if pt and len(pt) >= 3:
            loads.append({
                "point": rg.Point3d(pt[0], pt[1], pt[2]),
                "Fx_kN": ld.get("Fx_kN", 0),
                "Fy_kN": ld.get("Fy_kN", 0),
                "Fz_kN": ld.get("Fz_kN", 0),
            })

    for pt in karamba.get("load_points") or []:
        if pt and len(pt) >= 3:
            load_points.append(rg.Point3d(pt[0], pt[1], pt[2]))

    return line_elements, support, loads, load_points


run_id_str = str(run_id).strip() if run_id else ""
if not run_id_str:
    a = "No run_id provided. Run the send-prompt component first and wire its run_id output here."
    b = []
    c = []
    d = []
    e = []
    f = None
else:
    try:
        karamba = load_karamba_output(run_id_str)
        a = "OK"
        b, c, d, e = _parse_karamba_to_gh(karamba)
        f = None
    except Exception as err:
        a = ""
        b, c, d, e = [], [], [], []
        f = str(err)
