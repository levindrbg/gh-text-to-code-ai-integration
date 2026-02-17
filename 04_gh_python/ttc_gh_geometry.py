# Copy this script into a GHPython component (CPython 3, Rhino 8).
# Input  x: structural_result (dict) — from Optimization or Script Executor
# Output a: lines (list of Rhino.Geometry.Line)
# Output b: points (list of Rhino.Geometry.Point3d)

import os
import sys

REPO_ROOT = r"C:\path\to\repo"  # set to your repo path, or wire from Panel
SCRIPTS_DIR = os.path.join(REPO_ROOT, "03_python")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from geometry_builder import build_geometry

structural_result = x if x else {}
lines, points = build_geometry(structural_result)
a = lines
b = points
