# Truss computation process — summary

This summary is based on the **04_knowledge base** reference code (extracted from `database_topology/` and `database_material/`). It describes the computation flow used in the first version of the tool.

---

## 1. Node position

**Source:** `setup_truss_ground_structure` (database_topology)

**Purpose:** Create the initial dense mesh of nodes and potential elements (ground structure).

**What is done:**
- **Nodes:** For `i in range(NUM_BAYS + 1)`, place two nodes at each x: `x = i * (SPAN / NUM_BAYS)` with `y = 0` (bottom chord) and `y = HEIGHT` (top chord). Units in **mm** in the reference (SPAN e.g. 35000 mm, HEIGHT 3000 mm).
- **Elements:** Connect every pair of nodes `(i, j)` where `abs(node1_x - node2_x) <= 3 * (SPAN / NUM_BAYS)` (3-bay proximity). Each element is classified as **chord** (same y, horizontal, `abs(dx) <= bay*1.01`) or **web** (diagonal/vertical); store `chord_indices` and `web_indices`.
- **Boundary conditions:** `fixed_dofs = [0, 1, 2 * bottom_right_node_idx + 1]` — left node fully fixed (Ux, Uz), right bottom node roller (Uz only). So three constrained DOFs for 2D stability.
- **Loads (prepared here):** Top chord nodes (odd indices) get point loads from distributed load: `load = -FACTORED_LINE_LOAD_PER_MM * bay_width`; end nodes get half (tributary).

**Returns:** `(nodes, elements, fixed_dofs, load_nodes, load_values, chord_indices, web_indices)`.

**Global constants (from Global Constants Reference):** `SPAN`, `HEIGHT`, `NUM_BAYS`, `FACTORED_LINE_LOAD_PER_MM`.

---

## 2. Typology / member optimization

**Source:** `update_areas_beso_with_chords` (database_topology)

**Purpose:** Update member areas using BESO (Bi-directional Evolutionary Structural Optimization) with **chord protection** — only web members can be removed; chords are resized by stress but not eliminated.

**What is done:**
- **Allowable stress:** For each member, compressive allowable stress comes from `calculate_buckling_stress(areas, element_lengths)`; tensile allowable is `STEEL_STRENGTH_TENSION`. So `allowable_stresses = tension strength or buckling stress` depending on sign of stress.
- **Stress-based area update:** `stress_ratio = |stresses| / allowable_stresses`. New areas: `new_areas = (1 - MAX_STRESS_ADJUSTMENT_RATE) * areas + MAX_STRESS_ADJUSTMENT_RATE * (areas * stress_ratio)` — smooth adjustment toward target utilization.
- **Web volume reduction (BESO):** Target web volume is `current_web_volume * (1 - EVOLUTIONARY_RATE)`. Sort web members by **sensitivity** (here: `|stress|`). Remove web members (set area to `MIN_AREA`) starting from the **lowest** sensitivity until total web volume reaches the target. Chord members are **not** removed (only their areas are updated above).
- **Floor:** Apply `np.maximum(MIN_AREA, new_areas)`.

**Returns:** Updated member areas (same length as input).

**Dependencies:** `calculate_buckling_stress`; globals: `STEEL_STRENGTH_TENSION`, `MIN_AREA`, `EVOLUTIONARY_RATE`, `MAX_STRESS_ADJUSTMENT_RATE`.

---

## 3. Load calculation / cross section

### 3a. Load assembly

**Source:** `setup_truss_ground_structure` (load part), `main` (external_loads)

Nodal loads are built from the factored line load: for each top-chord node, `load_values = [0, -FACTORED_LINE_LOAD_PER_MM * bay_width]` (vertical, downward); end nodes get half. In `main`, these are scattered into a global vector: `external_loads[node_idx, :] += load_values[i, :]`, then flattened to `F` for FEA.

### 3b. FEA — analyze_truss

**Source:** `analyze_truss` (database_topology), `Analyze_truss_Function` (database_material)

**Steps:**
1. **Global stiffness K:** Loop over elements; for each, compute length `L`, direction cosines `c, s`. Local 4×4 stiffness `k_e = (A * E / L) * [[c², cs, -c², -cs], ...]`. Scatter-add into `K` at DOFs `[2*n1, 2*n1+1, 2*n2, 2*n2+1]`.
2. **Self-weight (topology version):** For each member, `member_weight = area * L * STEEL_DENSITY * 9.81 / 1000`; add half to each node in `self_weight_forces`. Then `F = external_loads.flatten() + self_weight_forces.flatten()`.
3. **Boundary conditions and solve:** `free_dofs = setdiff(all DOFs, fixed_dofs)`. Solve `K_ff @ U_f = F_f` (only free DOFs). On `np.linalg.LinAlgError` (singular matrix), return `(None, None, None, None)` so the optimizer can halt.
4. **Post-processing:** Axial strain in each element: `ε = (c*(U_x2-U_x1) + s*(U_y2-U_y1)) / L`. Stress: `σ = E * ε` (with material E in the material variant).

**Returns:** `(displacements, strains, stresses, element_lengths)` or `(None, None, None, None)` on failure.

### 3c. Cross section and buckling — calculate_buckling_stress

**Source:** `calculate_buckling_stress` (database_topology)

**Purpose:** Allowable compressive stress for Euler buckling.

**What is done:** Approximate second moment of area from area: `I = safe_areas² / (8 * π * T_D_RATIO)`. Effective length: `L_eff = K_FACTOR_BUCKLING * lengths`. Critical stress: `σ_cr = (π² * STEEL_E * I) / (L_eff² * safe_areas)`. Return `np.minimum(σ_cr, STEEL_STRENGTH_COMPRESSION)` so allowable stress is capped by material strength.

**Globals:** `MIN_AREA`, `T_D_RATIO`, `K_FACTOR_BUCKLING`, `STEEL_E`, `STEEL_STRENGTH_COMPRESSION`.

*(In the current generator pipeline, cross section is often discrete HEA profiles with stress + slenderness + Euler checks; the reference uses continuous areas and this buckling stress in the BESO step.)*

---

## >> Iteration

**Source:** `main` (database_topology), `Core Computation` (database_material — alternate runner)

**Purpose:** Orchestrate the optimization loop: repeatedly run FEA, update areas (and remove low-stress webs), until a fixed number of iterations or convergence.

**What is done:**
1. **Setup:** Call `setup_truss_ground_structure()` → nodes, elements, fixed_dofs, load_nodes, load_values, chord_indices, web_indices. Initialize `areas = np.full(num_elements, INITIAL_AREA)`. Build `external_loads` from load_nodes/load_values.
2. **Loop** for `i in range(NUM_ITERATIONS)` (e.g. 120):
   - `analysis_results = analyze_truss(nodes, elements, areas, fixed_dofs, external_loads)`.
   - If `analysis_results[0] is None` (singular matrix / unstable), append a log entry and **break**.
   - Else unpack `displacements, strains, stresses, element_lengths`.
   - **Update areas:** `areas = update_areas_beso_with_chords(areas, stresses, element_lengths, chord_indices, web_indices)`.
   - Optional logging: active member count, total volume.
3. **Final analysis:** Run `analyze_truss` once more with final `areas`. If successful, call `format_results_as_json(nodes, elements, areas, final_stresses, final_lengths)` and attach `optimization_log` to the result.

**Returns:** Dictionary with formatted results and optimization log, or error dict if final analysis fails.

**Globals:** `INITIAL_AREA`, `NUM_ITERATIONS`, `MIN_AREA`.

---

## Output

**Source:** `format_results_as_json` (database_topology), `Output_function` (database_material)

**Purpose:** Export the truss so downstream tools (e.g. Karamba, n8n) can consume it.

**format_results_as_json:**
- Inputs: `nodes`, `elements`, `areas`, optional `stresses`, `element_lengths`. Units in reference: mm for coordinates, mm² for areas.
- Filter: skip members with `areas <= MIN_AREA * 1.1`.
- For each active member: build an object with `member_id` (1-based, e.g. `member_01`), `start_x/y/z`, `end_x/y/z` (convert mm → m, 3 decimals), `area` (mm² → cm², 2 decimals; or empty string if below threshold). If `stresses` provided, add `stress_MPa`. Wrap each in `{"json": member_data}`.
- Returns a list of such dicts.

**Output_function (database_material):** Same idea: `export_final_design_to_json(nodes, elements, areas)` returns a list of member dicts (coords in m, area in cm²), to be returned to n8n as `[{ "json": data }, ...]`.

*(The current generator produces `geometric_output.json` with `line_elements`, `support`, and `loads` in the Karamba schema; the logic of “filter by MIN_AREA, convert units, one entry per member” is the same.)*

---

## Flow diagram (from knowledge base)

```
[1] setup_truss_ground_structure()
    → nodes, elements, fixed_dofs, load_nodes, load_values, chord_indices, web_indices

[2] BESO + chord protection (inside iteration)
    → update_areas_beso_with_chords(areas, stresses, lengths, chord_indices, web_indices)

[3] Loads: external_loads from load_nodes/load_values; F = external + self_weight (in analyze_truss)
    FEA: analyze_truss(nodes, elements, areas, fixed_dofs, external_loads)
    → displacements, strains, stresses, element_lengths
    Buckling: calculate_buckling_stress(areas, lengths) → used in update_areas_beso_with_chords

>> Iteration (main):
    areas = INITIAL_AREA
    for i in range(NUM_ITERATIONS):
        analyze_truss(...) → if None, break
        areas = update_areas_beso_with_chords(...)
    final analyze_truss → format_results_as_json(...)

[Output] format_results_as_json / export_final_design_to_json → list of {"json": member_data}
```

---

## Global constants (reference values)

From **Global Constants Reference:**

| Symbol | Example / meaning |
|--------|-------------------|
| SPAN | 35000 mm |
| HEIGHT | 3000 mm |
| NUM_BAYS | 12 |
| FACTORED_LINE_LOAD_PER_MM | 33.75 N/mm |
| STEEL_E | 210000 MPa |
| STEEL_STRENGTH_TENSION / COMPRESSION | 355 MPa |
| STEEL_DENSITY | 7.85e-6 kg/mm³ |
| INITIAL_AREA | 20000 mm² |
| MIN_AREA | 1.0 mm² |
| NUM_ITERATIONS | 120 |
| EVOLUTIONARY_RATE | 0.03 (3%) |
| MAX_STRESS_ADJUSTMENT_RATE | 0.5 |
| T_D_RATIO | 0.1 (buckling I approximation) |
| K_FACTOR_BUCKLING | 1.0 |

---

*Summary derived from extracted text in `04_knowledge base/extracted_txt/` (database_topology and database_material).*
