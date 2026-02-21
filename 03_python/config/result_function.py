"""
Reference implementation for geometric output. Use this in gen_script to build
the JSON that the pipeline expects (same structure as geometric_outline.json).

Output structure: description, line_elements, support, loads.
Units: m for coordinates, kN for forces. 2D truss in [x, z] plane; y=0 in Rhino.

Common ways to define truss geometry in Python:
  1. Node-based (indexed): nodes = [[x,z], ...], members = [(i,j), ...]
     - Standard in structural/FEM (Karamba, scipy). Supports/loads by node index.
  2. Explicit coordinates: build line_elements as [{"start":[x,z],"end":[x,z]}, ...]
     - Simple when geometry comes from parametric formulas or direct coordinates.
  3. NumPy: nodes as (N,2) array, members as (M,2) array of node indices — same as 1.
"""

import json
from typing import List, Tuple, Union

# Type aliases: 2D point [x, z]; line element {start, end}; load [x, z, Fz]
Point2D = List[float]
LineElement = dict  # {"start": [x,z], "end": [x,z]}
Load = List[float]  # [x, z, Fz] — application point and vertical force (kN)


def get_geometric_output(
    line_elements: List[LineElement],
    support: List[Point2D],
    loads: List[Load],
    description: str = "2D truss in [x, z] plane. Units: m, kN. Supports pinned.",
) -> dict:
    """
    Build the standard geometric output dict (matches geometric_outline.json).

    Args:
        line_elements: List of {"start": [x, z], "end": [x, z]} for each member.
        support: List of [x, z] for each support point.
        loads: List of [x, z, Fz] — application point (x,z) and vertical force Fz in kN.
        description: Optional short description of the structure.

    Returns:
        Dict with keys: description, line_elements, support, loads (JSON-serializable).
    """
    return {
        "description": description,
        "line_elements": line_elements,
        "support": support,
        "loads": loads,
    }


def from_nodes_and_members(
    nodes: List[Point2D],
    members: List[Tuple[int, int]],
    support_indices: List[int],
    loads_at_nodes: List[Tuple[int, float]],
    description: str = "2D truss in [x, z] plane. Units: m, kN. Supports pinned.",
) -> dict:
    """
    Build geometric output from node-based representation (common in structural code).

    Args:
        nodes: List of [x, z] for each node (index = position in list).
        members: List of (i, j) node index pairs for each member.
        support_indices: Node indices that are supports.
        loads_at_nodes: List of (node_index, Fz) — vertical force in kN at that node.
        description: Optional short description.

    Returns:
        Same dict as get_geometric_output().
    """
    line_elements = [
        {"start": list(nodes[i]), "end": list(nodes[j])}
        for i, j in members
    ]
    support = [list(nodes[i]) for i in support_indices]
    loads = [[nodes[i][0], nodes[i][1], Fz] for i, Fz in loads_at_nodes]
    return get_geometric_output(line_elements, support, loads, description)


# Example: use in gen_script and print JSON when run as main
if __name__ == "__main__":
    # Minimal example: two segments and one diagonal
    line_elements = [
        {"start": [0, 0], "end": [1, 0]},
        {"start": [1, 0], "end": [2, 0]},
        {"start": [0, 0], "end": [1, 0.5]},
        {"start": [1, 0.5], "end": [2, 0]},
    ]
    support = [[0, 0], [2, 0]]
    loads = [[1, 0.5, -1]]
    out = get_geometric_output(line_elements, support, loads)
    print(json.dumps(out))
