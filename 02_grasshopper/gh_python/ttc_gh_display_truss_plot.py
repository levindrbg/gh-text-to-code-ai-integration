"""
GHPython component: Display Truss Plot Image

Shows the pipeline-generated truss plot (run_output/[run_id]/truss_plot.png) as an overlay in the Rhino viewport.
Toggle show to display or hide the image.

Inputs:  run_id (str), show (bool)
Outputs: status (str), resolved_path (str)
"""

import os
import clr
clr.AddReference("System.Drawing")
import System.Drawing as SD
import Rhino
import Rhino.Display as RD
import Rhino.Geometry as RG
import scriptcontext as sc
from pathlib import Path

IMG_WIDTH = 600
MARGIN_LEFT = 10
MARGIN_TOP = 10
CONDUIT_KEY = "ttc_truss_plot_conduit"

# Resolve repo root from cwd (repo root or 02_grasshopper when GH runs)
_cwd = Path(os.getcwd()).resolve()
if (_cwd / "03_python").is_dir():
    REPO_ROOT = str(_cwd)
elif _cwd.name == "02_grasshopper" and (_cwd.parent / "03_python").is_dir():
    REPO_ROOT = str(_cwd.parent)
else:
    REPO_ROOT = str(_cwd)

# ---- Normalize run_id (can be list from GH wire) ----
if run_id is not None and hasattr(run_id, "__getitem__") and not isinstance(run_id, str):
    try:
        run_id = run_id[0]
    except (IndexError, TypeError, KeyError):
        run_id = ""
run_id = str(run_id).strip() if run_id else ""

img_path = os.path.join(REPO_ROOT, "03_python", "run_output", run_id, "truss_plot.png")
resolved_path = os.path.abspath(img_path)

if not run_id:
    status = "ERROR: No run_id provided."
elif not os.path.isfile(img_path):
    status = "ERROR: File not found:\n{}".format(resolved_path)
else:
    try:
        bmp = SD.Bitmap(img_path)
        w, h = float(bmp.Width), float(bmp.Height)
        draw_w = float(IMG_WIDTH)
        draw_h = draw_w * (h / w) if w else draw_w

        # DisplayBitmap for the display pipeline (keep bitmap ref so it isn't GC'd)
        display_bmp = RD.DisplayBitmap(bmp)

        if CONDUIT_KEY not in sc.sticky:
            class TrussPlotConduit(RD.DisplayConduit):
                def __init__(self):
                    self.visible = False
                    self.display_bmp = None
                    self.bitmap_ref = None
                    self.center_x = 0.0
                    self.center_y = 0.0
                    self.draw_w = 0.0
                    self.draw_h = 0.0

                def DrawForeground(self, e):
                    if not self.visible or self.display_bmp is None:
                        return
                    center = RG.Point2d(self.center_x, self.center_y)
                    e.Display.DrawSprite(self.display_bmp, center, self.draw_w, self.draw_h)

            c = TrussPlotConduit()
            sc.sticky[CONDUIT_KEY] = c
            c.Enabled = True

        c = sc.sticky[CONDUIT_KEY]
        old_bmp = getattr(c, "bitmap_ref", None)
        if old_bmp is not None:
            try:
                old_bmp.Dispose()
            except Exception:
                pass

        # DrawSprite uses center; we want top-left at (MARGIN_LEFT, MARGIN_TOP)
        c.center_x = MARGIN_LEFT + draw_w * 0.5
        c.center_y = MARGIN_TOP + draw_h * 0.5
        c.draw_w = draw_w
        c.draw_h = draw_h
        c.display_bmp = display_bmp
        c.bitmap_ref = bmp
        c.visible = bool(show)

        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is not None:
            doc.Views.Redraw()

        status = "{} | {}x{}px | {}".format(
            "VISIBLE" if show else "HIDDEN", int(draw_w), int(draw_h), resolved_path
        )
    except Exception as ex:
        status = "ERROR: {}".format(str(ex))
