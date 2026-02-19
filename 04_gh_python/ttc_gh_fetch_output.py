# GH component 2: Fetch gen_script output (Karamba data) for a run_id.
#
# GHPython (CPython 3, Rhino 8):
#   Input  run_id: str — from the send-prompt component (output b)
#   Input  run:    wire Button — click to fetch
#   Output a: communication / status (str)
#   Output b: Line_Elements (list of Rhino.Geometry.Line)
#   Output c: Support (list of {point, type})
#   Output d: Loads (list of {point, Fx_kN, Fy_kN, Fz_kN})
#   Output e: Load_Points (list of Rhino.Geometry.Point3d)
#   Output f: error (str or None)

import os
import sys

REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

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
