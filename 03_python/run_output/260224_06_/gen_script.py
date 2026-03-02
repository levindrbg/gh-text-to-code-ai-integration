import numpy as np
import json
import os

def get_geometric_output():
    # Input parameters from semantic outline
    span_m = 15
    truss_spacing_m = 6.0
    typology = "warren"
    snow_kN_per_m2 = 4.5
    roof_cladding_kN_per_m2 = 10.0
    self_weight_kN_per_m2 = 0.3
    
    # System parameters
    num_bays = 6
    ULS_gamma_G = 1.35
    ULS_gamma_Q = 1.5
    max_iterations = 40
    max_slenderness_ratio = 200
    f_y = 235000  # kN/m2
    E = 210000000  # kN/m2
    min_area_mm2 = 1
    
    # Height calculation for warren typology
    height_ratio = 6.5
    height_m = span_m / height_ratio
    
    # HEA profile properties (A in cm2, I_y in cm4, i_y in cm)
    hea_profiles = {
        "HEA100": {"A": 21.2, "I_y": 349, "i_y": 4.06},
        "HEA120": {"A": 25.3, "I_y": 606, "i_y": 4.89},
        "HEA140": {"A": 31.4, "I_y": 1033, "i_y": 5.73},
        "HEA160": {"A": 38.8, "I_y": 1673, "i_y": 6.57},
        "HEA180": {"A": 45.3, "I_y": 2510, "i_y": 7.45},
        "HEA200": {"A": 53.8, "I_y": 3692, "i_y": 8.28},
        "HEA220": {"A": 64.3, "I_y": 5410, "i_y": 9.17},
        "HEA240": {"A": 76.8, "I_y": 7763, "i_y": 10.1},
        "HEA260": {"A": 86.8, "I_y": 10450, "i_y": 10.9},
        "HEA280": {"A": 97.3, "I_y": 13670, "i_y": 11.8},
        "HEA300": {"A": 113, "I_y": 18260, "i_y": 12.7},
        "HEA320": {"A": 124, "I_y": 22930, "i_y": 13.6},
        "HEA340": {"A": 133, "I_y": 27690, "i_y": 14.4},
        "HEA360": {"A": 143, "I_y": 33090, "i_y": 15.2},
        "HEA400": {"A": 159, "I_y": 45070, "i_y": 16.8},
        "HEA450": {"A": 178, "I_y": 63720, "i_y": 18.9},
        "HEA500": {"A": 198, "I_y": 86970, "i_y": 21.0},
        "HEA550": {"A": 212, "I_y": 111900, "i_y": 23.0},
        "HEA600": {"A": 226, "I_y": 141200, "i_y": 25.0},
        "HEA650": {"A": 242, "I_y": 175100, "i_y": 26.9},
        "HEA700": {"A": 260, "I_y": 215100, "i_y": 28.8},
        "HEA800": {"A": 286, "I_y": 303400, "i_y": 32.6},
        "HEA900": {"A": 320, "I_y": 422100, "i_y": 36.3},
        "HEA1000": {"A": 347, "I_y": 553500, "i_y": 39.9}
    }
    
    # Node generation
    node_spacing = span_m / num_bays
    
    # Bottom chord nodes
    bottom_nodes = []
    for i in range(num_bays + 1):
        x = i * node_spacing
        bottom_nodes.append([x, 0.0])
    
    # Top chord nodes (warren has nodes at each bay)
    top_nodes = []
    for i in range(num_bays + 1):
        x = i * node_spacing
        top_nodes.append([x, height_m])
    
    # All nodes
    nodes = bottom_nodes + top_nodes
    num_bottom = len(bottom_nodes)
    num_top = len(top_nodes)
    
    # Member connectivity for warren truss
    members = []
    
    # Bottom chord
    for i in range(num_bays):
        members.append([i, i + 1])
    
    # Top chord
    for i in range(num_bays):
        members.append([num_bottom + i, num_bottom + i + 1])
    
    # Diagonals (warren pattern - alternating)
    for i in range(num_bays):
        if i % 2 == 0:
            # Connect bottom left to top right
            members.append([i, num_bottom + i + 1])
        else:
            # Connect bottom right to top left
            members.append([i + 1, num_bottom + i])
    
    # Support nodes (first and last bottom chord nodes)
    support_nodes = [0, num_bays]
    
    # Load calculation
    G = self_weight_kN_per_m2 + roof_cladding_kN_per_m2
    Q = snow_kN_per_m2
    q_uls = ULS_gamma_G * G + ULS_gamma_Q * Q
    tributary_width = truss_spacing_m
    
    # Load positions and values (top chord nodes)
    loads = []
    for i in range(num_top):
        x = top_nodes[i][0]
        z = top_nodes[i][1]
        if i == 0 or i == num_top - 1:
            # End nodes get half load
            Fz = -q_uls * tributary_width * (node_spacing / 2)
        else:
            # Interior nodes get full load
            Fz = -q_uls * tributary_width * node_spacing
        loads.append([x, z, Fz])
    
    # Initialize member areas with smallest profile
    member_areas = [hea_profiles["HEA100"]["A"] * 1e-4 for _ in members]  # Convert cm2 to m2
    member_profiles = ["HEA100" for _ in members]
    
    # FEA function
    def solve_fea(areas):
        num_nodes = len(nodes)
        num_members = len(members)
        
        # Global stiffness matrix
        K = np.zeros((2 * num_nodes, 2 * num_nodes))
        
        for m, (i, j) in enumerate(members):
            xi, zi = nodes[i]
            xj, zj = nodes[j]
            
            L = np.sqrt((xj - xi)**2 + (zj - zi)**2)
            if L == 0:
                continue
                
            c = (xj - xi) / L
            s = (zj - zi) / L
            
            A = areas[m]
            k = E * A / L
            
            # Local to global transformation
            T = np.array([
                [c, s, 0, 0],
                [-s, c, 0, 0],
                [0, 0, c, s],
                [0, 0, -s, c]
            ])
            
            k_local = np.array([
                [1, 0, -1, 0],
                [0, 0, 0, 0],
                [-1, 0, 1, 0],
                [0, 0, 0, 0]
            ]) * k
            
            k_global = T.T @ k_local @ T
            
            # Assembly
            dofs = [2*i, 2*i+1, 2*j, 2*j+1]
            for p in range(4):
                for q in range(4):
                    K[dofs[p], dofs[q]] += k_global[p, q]
        
        # Apply boundary conditions
        fixed_dofs = []
        for support_node in support_nodes:
            fixed_dofs.extend([2*support_node, 2*support_node+1])
        
        free_dofs = [i for i in range(2 * num_nodes) if i not in fixed_dofs]
        
        # Load vector
        F = np.zeros(2 * num_nodes)
        for i, (x, z, Fz) in enumerate(loads):
            node_idx = num_bottom + i  # Top chord nodes
            F[2*node_idx + 1] = Fz
        
        # Solve
        try:
            K_ff = K[np.ix_(free_dofs, free_dofs)]
            F_f = F[free_dofs]
            u_f = np.linalg.solve(K_ff, F_f)
            
            u = np.zeros(2 * num_nodes)
            u[free_dofs] = u_f
            
            # Calculate member forces
            forces = []
            for m, (i, j) in enumerate(members):
                xi, zi = nodes[i]
                xj, zj = nodes[j]
                
                L = np.sqrt((xj - xi)**2 + (zj - zi)**2)
                if L == 0:
                    forces.append(0)
                    continue
                    
                c = (xj - xi) / L
                s = (zj - zi) / L
                
                u_i = [u[2*i], u[2*i+1]]
                u_j = [u[2*j], u[2*j+1]]
                
                delta = c * (u_j[0] - u_i[0]) + s * (u_j[1] - u_i[1])
                N = E * areas[m] * delta / L
                forces.append(N)
            
            return forces, True
            
        except np.linalg.LinAlgError:
            return [0] * len(members), False
    
    # Optimization loop
    for iteration in range(max_iterations):
        forces, success = solve_fea(member_areas)
        if not success:
            break
        
        # Update profiles based on forces
        for m, force in enumerate(forces):
            i, j = members[m]
            xi, zi = nodes[i]
            xj, zj = nodes[j]
            L = np.sqrt((xj - xi)**2 + (zj - zi)**2)
            
            # Find suitable profile
            selected_profile = "HEA100"
            for profile_name in hea_profiles:
                profile = hea_profiles[profile_name]
                A = profile["A"] * 1e-4  # cm2 to m2
                i_y = profile["i_y"] * 1e-2  # cm to m
                
                # Stress check
                if A > 0:
                    stress = abs(force) / A
                    if stress > f_y:
                        continue
                
                # Slenderness check
                if L / i_y > max_slenderness_ratio:
                    continue
                
                # Euler buckling check for compression
                if force < 0:  # Compression
                    sigma_cr = np.pi**2 * E * i_y**2 / L**2
                    if abs(force) / A > sigma_cr:
                        continue
                
                selected_profile = profile_name
                break
            
            member_profiles[m] = selected_profile
            member_areas[m] = hea_profiles[selected_profile]["A"] * 1e-4
    
    # Final FEA
    final_forces, _ = solve_fea(member_areas)
    
    # Build output
    line_elements = []
    for m, (i, j) in enumerate(members):
        if member_areas[m] * 1e6 >= min_area_mm2:  # Convert m2 to mm2 for comparison
            start = nodes[i]
            end = nodes[j]
            profile = member_profiles[m]
            line_elements.append({
                "start": start,
                "end": end,
                "cross_section": profile
            })
    
    support_positions = [nodes[i] for i in support_nodes]
    load_list = [[x, z, Fz] for x, z, Fz in loads]
    
    result = {
        "description": f"Warren truss, span {span_m}m, height {height_m:.2f}m, {num_bays} bays",
        "line_elements": line_elements,
        "support": support_positions,
        "loads": load_list
    }
    
    return result

if __name__ == "__main__":
    result = get_geometric_output()
    print(json.dumps(result))
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "geometric_output.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)