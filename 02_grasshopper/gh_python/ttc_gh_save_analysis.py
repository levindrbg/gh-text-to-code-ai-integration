# GH component: TTC Save Analysis
# Saves per-member analysis to run_output/[run_id]/analysis_output.json for the feedback loop.
# Input run_id + line_elements (base) + attribute lists → writes JSON, outputs run_id (pass-through).
#
# Input  run_id: str (or list with one str from GH wire)
# Input  Line_Elements: list of Rhino.Geometry.Line (or list of dicts {start, end, cross_section})
# Input  CroSec: list of str, cross_section name per member (same order as Line_Elements)
# Input  Utilization: list of float, one per member
# Input  Displacement_Start: list of [dx, dz] or Point3d/Vector3d, displacement at start of member
# Input  Displacement_End: list of [dx, dz] or Point3d/Vector3d, displacement at end of member
# Input  Axial_Stress: list of float, axial stress per member (e.g. MPa)
# Output run_id: str (same as input)
# Output status: str

import json
import os

REPO_ROOT = r"C:\Users\levin\Documents\GitHub\gh-text-to-code-ai-integration"
RUN_OUTPUT_DIR = os.path.join(REPO_ROOT, "03_python", "run_output")

try:
    import Rhino.Geometry as rg
except ImportError:
    rg = None


def _point_to_xz(pt):
    """Extract [x, z] from Point3d/Vector3d or [x, y, z] / [x, z] list."""
    if pt is None:
        return [0.0, 0.0]
    if rg and hasattr(pt, "X") and hasattr(pt, "Z"):
        return [float(pt.X), float(pt.Z)]
    if hasattr(pt, "__getitem__") and len(pt) >= 2:
        return [float(pt[0]), float(pt[1])]
    return [0.0, 0.0]


def _line_to_segment(line):
    """Convert Rhino Line to {start: [x,z], end: [x,z]}."""
    if rg and hasattr(line, "From") and hasattr(line, "To"):
        return {"start": _point_to_xz(line.From), "end": _point_to_xz(line.To)}
    if isinstance(line, dict):
        s, e = line.get("start"), line.get("end")
        return {"start": s if isinstance(s, list) else [0, 0], "end": e if isinstance(e, list) else [0, 0]}
    return {"start": [0.0, 0.0], "end": [0.0, 0.0]}


# Normalize run_id
if run_id is not None and hasattr(run_id, "__getitem__") and not isinstance(run_id, str):
    try:
        run_id = run_id[0]
    except (IndexError, TypeError, KeyError):
        run_id = ""
run_id = str(run_id).strip() if run_id else ""

# Coerce inputs to lists and ensure same length
line_elems = list(Line_Elements) if Line_Elements is not None else []
crosec = list(CroSec) if CroSec is not None else []
utilization = list(Utilization) if Utilization is not None else []
displacement_start = list(Displacement_Start) if Displacement_Start is not None else []
displacement_end = list(Displacement_End) if Displacement_End is not None else []
axial_stress = list(Axial_Stress) if Axial_Stress is not None else []

n = len(line_elems)
if n == 0:
    status = "No line elements provided; nothing to save."
else:
    # Align lengths to n (pad with defaults where needed)
    def pad(lst, default):
        return lst + [default] * (n - len(lst)) if len(lst) < n else lst[:n]

    crosec = pad(crosec, "")
    utilization = pad(utilization, 0.0)
    displacement_start = pad(displacement_start, [0.0, 0.0])
    displacement_end = pad(displacement_end, [0.0, 0.0])
    axial_stress = pad(axial_stress, 0.0)

    members = []
    for i in range(n):
        seg = _line_to_segment(line_elems[i])
        seg["cross_section"] = str(crosec[i]) if i < len(crosec) else ""
        seg["utilization"] = float(utilization[i])
        seg["displacement_start"] = _point_to_xz(displacement_start[i])
        seg["displacement_end"] = _point_to_xz(displacement_end[i])
        seg["axial_stress"] = float(axial_stress[i])
        members.append(seg)

    if not run_id:
        status = "No run_id provided; analysis not saved."
    else:
        run_dir = os.path.join(RUN_OUTPUT_DIR, run_id)
        try:
            os.makedirs(run_dir, exist_ok=True)
            path = os.path.join(run_dir, "analysis_output.json")
            compact = lambda obj: json.dumps(obj, separators=(", ", ": "))
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"description":"Member analysis for feedback loop (per-member attributes)",\n"line_elements":[\n')
                f.write(",\n".join(compact(m) for m in members))
                f.write("\n]}\n")
            status = "OK: saved " + path
        except Exception as err:
            status = "Error: " + str(err)
