import numpy as np
import json
import os

def get_geometric_output():
    # Input parameters from semantic outline
    span_m = 15
    length_y_m = 30
    truss_count = 6
    typology = "warren"
    support_positions = [[0, 0], [15, 0]]
    
    # Load parameters
    snow_kN_per_m2 = 4.5
    roof_cladding_kN_per_m2 = 10.0
    self_weight_kN_per_m2 = 0.3
    
    # System parameters
    ULS_gamma_G = 1.35
    ULS_gamma_Q = 1.5
    max_iterations = 40
    max_slenderness_ratio = 200
    max_deflection_ratio = 300
    min_member_area_mm2 = 1
    volume_fraction = 0.4
    
    # Material properties (steel)
    E = 210000000  # kN/m2
    f_y = 355000   # kN/m2
    
    # HEA profile catalogue (A in cm2, I_y in cm4, i_y in cm)
    hea_profiles = {
        "HEA100": {"A": 21.2, "I_y": 349, "i_y": 4.06},
        "HEA120": {"A": 25.3, "I_y": 606, "i_y": 4.89},
        "HEA140": {"A": 31.4, "I_y": 1033, "i_y": 5.73},
        "HEA160": {"A": 38.8, "I_y": 1673, "i_y": 6.57},
        "HEA180": {"A": 45.3, "I_y": 2510, "i_y": 7.45},
        "HEA200": {"A": 53.8, "I_y": 3692, "i_y": 8.28},
        "HEA220": {"A": 64.3, "I_y": 5410, "i_y": 9.17},
        "HEA240": {"A": 76.8, "I_y": 7763, "i_y": 10.1},
        "HEA260": {"A": 90.7, "I_y": 10450, "i_y": 10.7},
        "HEA280": {"A": 103.1, "I_y": 13670, "i_y": 11.5},
        "HEA300": {"A": 112.5, "I_y": 18260, "i_y": 12.7},
        "HEA320": {"A": 124.4, "I_y": 22930, "i_y": 13.6},
        "HEA340": {"A": 133.5, "I_y": 27690, "i_y": 14.4},
        "HEA360": {"A": 142.8, "I_y": 33090, "i_y": 15.2},
        "HEA400": {"A": 159.0, "I_y": 45070, "i_y": 16.8},
        "HEA450": {"A": 178.0, "I_y": 63720, "i_y": 18.9},
        "HEA500": {"A": 197.8, "I_y": 86970, "i_y": 21.0},
        "HEA550": {"A": 212.2, "I_y": 111900, "i_y": 22.9},
        "HEA600": {"A": 226.5, "I_y": 141200, "i_y": 24.9},
        "HEA650": {"A": 240.6, "I_y": 175100, "i_y": 27.0},
        "HEA700": {"A": 260.1, "I_y": 215300, "i_y": 28.8},
        "HEA800": {"A": 286.4, "I_y": 303400, "i_y": 32.6},
        "HEA900": {"A": 320.5, "I_y": 422100, "i_y": 36.2},
        "HEA1000": {"A": 347.4, "I_y": 553500, "i_y": 39.9}
    }
    
    # Calculate height from span and typology
    height_ratios = {
        "bowstring": 4,
        "warren": 6.5,
        "warren_with_verticals": 6,
        "pratt": 5.5,
        "howe": 5.5,
        "fink": 4.5,
        "parker": 4.5,
        "flat": 9
    }
    height_ratio = height_ratios.get(typology, 6)
    height_m = span_m / height_ratio
    
    # Calculate tributary width
    tributary_width = length_y_m / truss_count
    
    # Calculate number of bays (scale with span, min 4)
    num_bays = max(4, int(span_m / 2.5))
    
    # Step 1: Node position
    # Generate nodes for Warren truss
    node_spacing = span_m / num_bays
    
    # Bottom chord nodes
    bottom_nodes = []
    for i in range(num_bays + 1):
        x = i * node_spacing
        bottom_nodes.append([x, 0])
    
    # Top chord nodes (Warren has alternating pattern)
    top_nodes = []
    for i in range(1, num_bays):
        x = i * node_spacing
        top_nodes.append([x, height_m])
    
    # Combine all nodes
    nodes = bottom_nodes + top_nodes
    num_bottom_nodes = len(bottom_nodes)
    num_top_nodes = len(top_nodes)
    
    # Generate members for Warren truss
    members = []
    
    # Bottom chord members
    for i in range(num_bays):
        members.append([i, i + 1])
    
    # Top chord members
    for i in range(num_top_nodes - 1):
        members.append([num_bottom_nodes + i, num_bottom_nodes + i + 1])
    
    # Diagonal members (Warren pattern)
    for i in range(num_bays):
        if i < num_top_nodes:
            # Left diagonal
            members.append([i, num_bottom_nodes + i])
        if i + 1 < num_top_nodes:
            # Right diagonal
            members.append([i + 1, num_bottom_nodes + i])
    
    # Support nodes (first and last bottom chord nodes)
    support_nodes = [0, num_bays]
    
    # Load positions (top chord nodes)
    load_nodes = list(range(num_bottom_nodes, num_bottom_nodes + num_top_nodes))
    
    # Calculate loads
    G = self_weight_kN_per_m2 + roof_cladding_kN_per_m2
    Q = snow_kN_per_m2
    q_uls = ULS_gamma_G * G + ULS_gamma_Q * Q
    
    # Step 2: Initialize member areas with smallest profile
    smallest_profile = "HEA100"
    member_profiles = [smallest_profile] * len(members)
    
    # Step 3: Load calculation and FEA
    def calculate_member_length(member_idx):
        i, j = members[member_idx]
        node_i = nodes[i]
        node_j = nodes[j]
        return np.sqrt((node_j[0] - node_i[0])**2 + (node_j[1] - node_i[1])**2)
    
    def get_direction_cosines(member_idx):
        i, j = members[member_idx]
        node_i = nodes[i]
        node_j = nodes[j]
        L = calculate_member_length(member_idx)
        cx = (node_j[0] - node_i[0]) / L
        cz = (node_j[1] - node_i[1]) / L
        return cx, cz
    
    def assemble_stiffness_matrix():
        num_nodes = len(nodes)
        K = np.zeros((2 * num_nodes, 2 * num_nodes))
        
        for m_idx, (i, j) in enumerate(members):
            profile = member_profiles[m_idx]
            A = hea_profiles[profile]["A"] * 1e-4  # Convert cm2 to m2
            L = calculate_member_length(m_idx)
            cx, cz = get_direction_cosines(m_idx)
            
            k_local = (E * A / L) * np.array([
                [1, -1],
                [-1, 1]
            ])
            
            T = np.array([
                [cx, cz, 0, 0],
                [0, 0, cx, cz]
            ])
            
            k_global = T.T @ k_local @ T
            
            dofs = [2*i, 2*i+1, 2*j, 2*j+1]
            for ii, dof_i in enumerate(dofs):
                for jj, dof_j in enumerate(dofs):
                    K[dof_i, dof_j] += k_global[ii, jj]
        
        return K
    
    def apply_loads():
        num_nodes = len(nodes)
        F = np.zeros(2 * num_nodes)
        
        # Apply point loads at top chord nodes
        for node_idx in load_nodes:
            if node_idx == load_nodes[0] or node_idx == load_nodes[-1]:
                # End nodes get half load
                load_magnitude = -q_uls * tributary_width * (node_spacing / 2)
            else:
                # Interior nodes get full load
                load_magnitude = -q_uls * tributary_width * node_spacing
            
            F[2 * node_idx + 1] = load_magnitude  # Z direction
        
        return F
    
    def solve_fea():
        try:
            K = assemble_stiffness_matrix()
            F = apply_loads()
            
            # Apply boundary conditions
            num_nodes = len(nodes)
            all_dofs = list(range(2 * num_nodes))
            constrained_dofs = []
            
            for support_node in support_nodes:
                constrained_dofs.extend([2 * support_node, 2 * support_node + 1])
            
            free_dofs = [dof for dof in all_dofs if dof not in constrained_dofs]
            
            K_ff = K[np.ix_(free_dofs, free_dofs)]
            F_f = F[free_dofs]
            
            u_f = np.linalg.solve(K_ff, F_f)
            
            # Full displacement vector
            u = np.zeros(2 * num_nodes)
            u[free_dofs] = u_f
            
            # Calculate member forces
            member_forces = []
            for m_idx, (i, j) in enumerate(members):
                profile = member_profiles[m_idx]
                A = hea_profiles[profile]["A"] * 1e-4
                L = calculate_member_length(m_idx)
                cx, cz = get_direction_cosines(m_idx)
                
                u_i = [u[2*i], u[2*i+1]]
                u_j = [u[2*j], u[2*j+1]]
                
                delta_u = [(u_j[0] - u_i[0]), (u_j[1] - u_i[1])]
                axial_strain = (cx * delta_u[0] + cz * delta_u[1]) / L
                axial_force = E * A * axial_strain
                member_forces.append(axial_force)
            
            return member_forces, u
            
        except np.linalg.LinAlgError:
            print("Singular matrix encountered in FEA")
            return None, None
    
    def select_profile(force, length):
        stress = abs(force)
        
        for profile_name in hea_profiles:
            profile = hea_profiles[profile_name]
            A = profile["A"] * 1e-4  # Convert to m2
            i_y = profile["i_y"] * 1e-2  # Convert to m
            
            # Check stress
            if stress / A <= f_y:
                # Check slenderness
                if length / i_y <= max_slenderness_ratio:
                    # Check Euler buckling for compression
                    if force < 0:  # Compression
                        sigma_cr = (np.pi**2 * E * (i_y**2)) / (length**2)
                        if stress / A <= sigma_cr:
                            return profile_name
                    else:  # Tension
                        return profile_name
        
        return "HEA1000"  # Fallback to largest profile
    
    # Step 4: Iteration
    for iteration in range(max_iterations):
        member_forces, displacements = solve_fea()
        
        if member_forces is None:
            break
        
        # Update member profiles
        updated = False
        for m_idx in range(len(members)):
            force = member_forces[m_idx]
            length = calculate_member_length(m_idx)
            new_profile = select_profile(force, length)
            
            if new_profile != member_profiles[m_idx]:
                member_profiles[m_idx] = new_profile
                updated = True
        
        if not updated:
            break
    
    # Final FEA
    member_forces, displacements = solve_fea()
    
    # Step 5: Output
    line_elements = []
    for m_idx, (i, j) in enumerate(members):
        start = nodes[i]
        end = nodes[j]
        profile = member_profiles[m_idx]
        
        line_elements.append({
            "start": start,
            "end": end,
            "cross_section": profile
        })
    
    # Support positions
    support_positions_output = [nodes[i] for i in support_nodes]
    
    # Load positions and values
    loads_output = []
    for node_idx in load_nodes:
        node_pos = nodes[node_idx]
        if node_idx == load_nodes[0] or node_idx == load_nodes[-1]:
            load_magnitude = -q_uls * tributary_width * (node_spacing / 2)
        else:
            load_magnitude = -q_uls * tributary_width * node_spacing
        
        loads_output.append([node_pos[0], node_pos[1], load_magnitude])
    
    result = {
        "description": f"Warren truss, span {span_m}m, height {height_m:.2f}m, {num_bays} bays",
        "line_elements": line_elements,
        "support": support_positions_output,
        "loads": loads_output
    }
    
    return result

if __name__ == "__main__":
    result = get_geometric_output()
    print(json.dumps(result))
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "geometric_output.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)