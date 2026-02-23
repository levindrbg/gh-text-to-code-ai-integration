"""
TTC Executor — Load, validate, and execute gen_script.py for a run.

- Loads gen_script.py from 03_python/run_output/[run_id]/.
- Validates script (syntax check).
- Executes the script in that run directory so it can write geometric_output.json there.
- Grasshopper (or other clients) read geometric_output.json separately.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Any, Dict

_dir = Path(__file__).resolve().parent


def plot_geometric_output(geometric: Dict[str, Any], run_dir: Path) -> None:
    """
    Plot truss from geometric output (line_elements, support, loads) and save as run_dir/truss_plot.png.
    Uses matplotlib Agg backend (no display). On failure (e.g. matplotlib missing), skips without raising.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    line_elements = geometric.get("line_elements") or []
    support = geometric.get("support") or []
    loads = geometric.get("loads") or []

    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        # Members
        for seg in line_elements:
            start = seg.get("start") or [0, 0]
            end = seg.get("end") or [0, 0]
            label = seg.get("cross_section") or ""
            ax.plot([start[0], end[0]], [start[1], end[1]], color="steelblue", linewidth=1.5)
            mid_x = (start[0] + end[0]) / 2
            mid_z = (start[1] + end[1]) / 2
            if label:
                ax.text(mid_x, mid_z, label, fontsize=7, ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
        # Supports [[x, z], ...]
        for i, pt in enumerate(support):
            if not pt:
                continue
            x = pt[0] if len(pt) > 0 else 0
            z = pt[1] if len(pt) > 1 else 0
            ax.plot(x, z, "s", markersize=10, color="green", label="Support" if i == 0 else "")
        # Loads [x, z, Fz]
        for item in loads:
            if len(item) < 3:
                continue
            x, z, Fz = item[0], item[1], item[2]
            ax.plot(x, z, "o", markersize=6, color="orange")
            scale = 0.3
            if abs(Fz) > 1e-6:
                ax.arrow(x, z, 0, scale * (1 if Fz < 0 else -1), head_width=0.15, head_length=0.08, fc="orange", ec="orange")
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")
        ax.set_xlabel("X [m]")
        ax.set_ylabel("Z [m]")
        ax.set_title("Truss layout (pipeline plot)")
        ax.legend(loc="upper right")
        fig.tight_layout()
        out_path = run_dir / "truss_plot.png"
        fig.savefig(out_path, dpi=120)
        plt.close(fig)
    except Exception:
        pass


def load_script(run_id: str) -> str:
    """Load generated script from run_output/[run_id]/gen_script.py. Uses UTF-8 to avoid Windows charmap decode errors."""
    path = _dir / "run_output" / run_id / "gen_script.py"
    if not path.exists():
        raise FileNotFoundError(f"Generated script not found: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def validate_script(script_str: str) -> None:
    """Check script syntax. Raises SyntaxError if invalid."""
    ast.parse(script_str)


def execute_script(script_str: str, run_dir: Path) -> None:
    """
    Execute the generated script in run_dir as cwd.
    Injects __file__ and __name__='__main__' so the script's if __name__ == '__main__' block runs
    and geometric_output.json is written to the run folder, not 03_python/.
    """
    run_dir = run_dir.resolve()
    script_file = run_dir / "gen_script.py"
    exec_globals = {"__file__": str(script_file), "__name__": "__main__"}
    old_cwd = os.getcwd()
    try:
        os.chdir(run_dir)
        exec(compile(script_str, "<gen_script>", "exec"), exec_globals)
    finally:
        os.chdir(old_cwd)


def run(run_id: str) -> None:
    """
    Load gen_script for run_id, validate syntax, execute it.
    The script writes geometric_output.json in run_output/[run_id]/; the executor returns nothing.
    """
    script_str = load_script(run_id)
    validate_script(script_str)
    run_dir = _dir / "run_output" / run_id
    execute_script(script_str, run_dir)


if __name__ == "__main__":
    run_output_dir = _dir / "run_output"
    if not run_output_dir.exists():
        print("No run_output directory found.", file=sys.stderr)
        sys.exit(1)

    # run_id from argv, or latest run_output folder by mtime
    if len(sys.argv) >= 2:
        run_id = sys.argv[1]
    else:
        subdirs = [d for d in run_output_dir.iterdir() if d.is_dir() and (d / "gen_script.py").exists()]
        if not subdirs:
            print("No run_output subdirs with gen_script.py. Usage: python ttc_executor.py <run_id>", file=sys.stderr)
            sys.exit(1)
        run_id = max(subdirs, key=lambda d: d.stat().st_mtime).name
        print(f"No run_id given, using latest: {run_id}")

    try:
        run(run_id)
        print(f"OK: gen_script.py executed for {run_id}")
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Execution error: {e}", file=sys.stderr)
        sys.exit(1)
