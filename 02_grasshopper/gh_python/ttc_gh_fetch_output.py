# GH component 2: Fetch run output (geometric_output.json) for a run_id.
# Copy-paste into a GHPython component in TTC_Workflow_V1.gh.
# Loads run_output/[run_id]/geometric_output.json (2D [x,z], y=0).
#
# GHPython (CPython 3, Rhino 8):
#   Input  run_id: str — wire from send-prompt component (output run_id)
#   Output status: str (OK or message)
#   Output Line_Elements: list of Rhino.Geometry.Line
#   Output Support: list of Rhino.Geometry.Point3d (support points)
#   Output Loads: list of Rhino.Geometry.Vector3d (force vectors, kN)
#   Output Load_Points: list of Rhino.Geometry.Point3d (application points)

import os
import sys
from pathlib import Path

# Hardcode repo root so 03_python is always found when pasted into GH (Rhino cwd/__file__ are unreliable)
REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"
if not os.path.isdir(os.path.join(REPO_ROOT, "03_python")):
    _cwd = Path(os.getcwd()).resolve()
    if (_cwd / "03_python").is_dir():
        REPO_ROOT = str(_cwd)
    elif _cwd.name == "02_grasshopper" and (_cwd.parent / "03_python").is_dir():
        REPO_ROOT = str(_cwd.parent)

SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
os.environ["TTC_03_PYTHON"] = os.path.abspath(SCRIPTS_DIR)

from ttc_main import load_geometric_output

try:
    import Rhino.Geometry as rg
except ImportError:
    rg = None

# 2D [x, z] → Rhino Point3d with y=0
def _pt(xz):
    if xz is None or len(xz) < 2:
        return None
    return rg.Point3d(float(xz[0]), 0.0, float(xz[1]))


def _parse_geometric_to_gh(geo):
    """Parse geometric_output.json into GH elements. Plane [x,z], y=0. Uses Rhino.Geometry."""
    line_elements = []
    support = []
    loads = []
    load_points = []

    if not geo or not rg:
        return line_elements, support, loads, load_points

    for seg in geo.get("line_elements") or []:
        s, e = seg.get("start"), seg.get("end")
        ps, pe = _pt(s), _pt(e)
        if ps and pe:
            line_elements.append(rg.Line(ps, pe))

    for xz in geo.get("support") or []:
        p = _pt(xz)
        if p:
            support.append(p)

    for ld in geo.get("loads") or []:
        if not ld or len(ld) < 3:
            continue
        x, z, F = float(ld[0]), float(ld[1]), float(ld[2])
        load_points.append(rg.Point3d(x, 0.0, z))
        loads.append(rg.Vector3d(0.0, 0.0, F))

    return line_elements, support, loads, load_points


run_id_str = str(run_id).strip() if run_id else ""
if not run_id_str:
    status = "No run_id provided. Run the send-prompt component first and wire its run_id output here."
    Line_Elements = []
    Support = []
    Loads = []
    Load_Points = []
else:
    try:
        geo = load_geometric_output(run_id_str)
        status = "OK"
        Line_Elements, Support, Loads, Load_Points = _parse_geometric_to_gh(geo)
    except Exception as err:
        status = str(err)
        Line_Elements, Support, Loads, Load_Points = [], [], [], []
