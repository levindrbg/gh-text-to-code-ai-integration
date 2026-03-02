import numpy as np
import json
import os

def get_geometric_output():
    # Input parameters from semantic outline
    span_m = 15
    length_y_m = 30
    num_bays = 10
    typology = "bowstring"
    height_m = 2.5  # Explicitly provided in semantic outline
    snow_kN_per_m2 = 4.5
    roof_cladding_kN_per_m2 = 0.3
    additional_dead_kN_per_m2 = 10.0
    self_weight_kN_per_m2 = 0.3
    
    # System parameters
    ULS_gamma_G = 1.35
    ULS_gamma_Q = 1.5
    max_iterations = 40
    max_slenderness_ratio = 200
    f_y = 235000  # kN/m2
    E = 210000000  # kN/m2
    min_member_area_mm2 = 1
    
    # Tributary width calculation
    tributary_width_m = length_y_m / 2  # Assume 2 trusses
    
    # HEA profile properties [A_cm2, I_y_cm4, i_y_cm]
    hea_profiles = {
        "HEA100": [21.2, 349, 4.06],
        "HEA120": [25.3, 606, 4.89],
        "HEA140": [31.4, 1033, 5.73],
        "HEA160": [38.8, 1673, 6.57],
        "HEA180": [45.3, 2510, 7.45],
        "HEA200": [53.8, 3692, 8.28],
        "HEA220": [64.3, 5410, 9.17],
        "HEA240": [76.8, 7763, 10.1],
        "HEA260": [90.7, 10450, 10.7],
        "HEA280": [103.1, 13670, 11.5],
        "HEA300": [112.5, 18260, 12.7],
        "HEA320": [124.4, 22930, 13.6],
        "HEA340": [133.5, 27690, 14.4],
        "HEA360": [142.8, 33090, 15.2],
        "HEA400": [159.0, 45070, 16.8],
        "HEA450": [178.0, 63720, 18.9],
        "HEA500": [198.0, 86970, 21.0],
        "HEA550": [212.0, 111900, 23.0],
        "HEA600": [226.0, 141200, 25.0],
        "HEA650": [242.0, 175100, 26.9],
        "HEA700": [260.0, 215100, 28.8],
        "HEA800": [286.0, 303400, 32.6],
        "HEA900": [320.0, 422100, 36.3],
        "HEA1000": [347.0, 553500, 39.9]
    }
    
    profile_names = list(hea_profiles.keys())
    
    # Node generation
    node_spacing = span_m / num_bays
    
    # Bottom chord nodes (straight line)
    bottom_nodes = []
    for i in range(num_bays + 1):
        x = i * node_spacing
        z = 0.0
        bottom_nodes.append([x, z])
    
    # Top chord nodes - parabolic arch
    top_nodes = []
    for i in range(num_bays + 1):
        x = i * node_spacing
        if i == 0 or i == num_bays:
            z = 0.0  # Ends at support level
        else:
            z = 4 * height_m * (x / span_m) * (1 - x / span_m)
        top_nodes.append([x, z])
    
    # All nodes
    nodes = bottom_nodes + top_nodes
    num_bottom_nodes = len(bottom_nodes)
    
    # Member generation
    members = []
    
    # Bottom chord members
    for i in range(num_bays):
        members.append([i, i + 1])
    
    # Top chord members
    for i in range(num_bays):
        top_idx1 = num_bottom_nodes + i
        top_idx2 = num_bottom_nodes + i + 1
        members.append([top_idx1, top_idx2])
    
    # Vertical members
    for i in range(num_bays + 1):
        bottom_idx = i
        top_idx = num_bottom_nodes + i
        members.append([bottom_idx, top_idx])
    
    # Diagonal bracing members
    for i in range(num_bays):
        bottom_left = i
        bottom_right = i + 1
        top_left = num_bottom_nodes + i
        top_right = num_bottom_nodes + i + 1
        
        members.append([bottom_left, top_right])
        members.append([bottom_right, top_left])
    
    # Support nodes
    support_nodes = [0, num_bays]
    
    # Load calculation
    G = self_weight_kN_per_m2 + roof_cladding_kN_per_m2 + additional_dead_kN_per_m2
    Q = snow_kN_per_m2
    q_uls = ULS_gamma_G * G + ULS_gamma_Q * Q
    
    # Load positions (top chord nodes)
    load_positions = []
    load_values = []
    
    # Interior top chord nodes
    for i in range(1, num_bays):
        node_idx = num_bottom_nodes + i
        load_value = -q_uls * tributary_width_m * node_spacing
        load_positions.append(node_idx)
        load_values.append(load_value)
    
    # End top chord nodes (half tributary)
    end_load = -q_uls * tributary_width_m * (node_spacing / 2)
    load_positions.extend([num_bottom_nodes, num_bottom_nodes + num_bays])
    load_values.extend([end_load, end_load])
    
    # Initialize member areas and profiles
    member_areas = [hea_profiles["HEA100"][0] * 1e-4 for _ in members]  # Convert cm2 to m2
    member_profiles = ["HEA100" for _ in members]
    
    # Identify chord and web members for uniform chord sizing
    chord_indices = []
    web_indices = []
    
    # Bottom chord
    for i in range(num_bays):
        chord_indices.append(i)
    
    # Top chord
    for i in range(num_bays, 2 * num_bays):
        chord_indices.append(i)
    
    # All other members are webs
    for i in range(2 * num_bays, len(members)):
        web_indices.append(i)
    
    # FEA function
    def solve_fea(nodes, members, member_areas, support_nodes, load_positions, load_values):
        num_nodes = len(nodes)
        num_dofs = 2 * num_nodes
        
        # Global stiffness matrix
        K = np.zeros((num_dofs, num_dofs))
        
        for m_idx, (i, j) in enumerate(members):
            xi, zi = nodes[i]
            xj, zj = nodes[j]
            
            L = np.sqrt((xj - xi)**2 + (zj - zi)**2)
            if L < 1e-12:
                continue
                
            c = (xj - xi) / L
            s = (zj - zi) / L
            
            A = member_areas[m_idx]
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
            
            dofs = [2*i, 2*i+1, 2*j, 2*j+1]
            for p in range(4):
                for q in range(4):
                    K[dofs[p], dofs[q]] += k_global[p, q]
        
        # Load vector
        F = np.zeros(num_dofs)
        for load_idx, load_val in zip(load_positions, load_values):
            F[2*load_idx + 1] = load_val  # Z-direction
        
        # Boundary conditions
        fixed_dofs = []
        for support_node in support_nodes:
            fixed_dofs.extend([2*support_node, 2*support_node + 1])
        
        free_dofs = [i for i in range(num_dofs) if i not in fixed_dofs]
        
        try:
            K_ff = K[np.ix_(free_dofs, free_dofs)]
            F_f = F[free_dofs]
            u_f = np.linalg.solve(K_ff, F_f)
            
            u = np.zeros(num_dofs)
            u[free_dofs] = u_f
            
            # Member forces
            member_forces = []
            for m_idx, (i, j) in enumerate(members):
                xi, zi = nodes[i]
                xj, zj = nodes[j]
                
                L = np.sqrt((xj - xi)**2 + (zj - zi)**2)
                if L < 1e-12:
                    member_forces.append(0.0)
                    continue
                    
                c = (xj - xi) / L
                s = (zj - zi) / L
                
                ui, vi = u[2*i], u[2*i+1]
                uj, vj = u[2*j], u[2*j+1]
                
                delta = c * (uj - ui) + s * (vj - vi)
                A = member_areas[m_idx]
                force = E * A * delta / L
                member_forces.append(force)
            
            return member_forces, u
            
        except np.linalg.LinAlgError:
            return None, None
    
    # Optimization loop
    for iteration in range(max_iterations):
        member_forces, displacements = solve_fea(nodes, members, member_areas, support_nodes, load_positions, load_values)
        
        if member_forces is None:
            break
        
        # Find maximum force in chord members for uniform sizing
        max_chord_force = 0
        max_chord_length = 0
        
        for m_idx in chord_indices:
            force = abs(member_forces[m_idx])
            if force > max_chord_force:
                max_chord_force = force
                
            i, j = members[m_idx]
            xi, zi = nodes[i]
            xj, zj = nodes[j]
            L = np.sqrt((xj - xi)**2 + (zj - zi)**2)
            if L > max_chord_length:
                max_chord_length = L
        
        # Find suitable uniform chord profile
        chord_profile = None
        for profile_name in profile_names:
            A_cm2, I_y_cm4, i_y_cm = hea_profiles[profile_name]
            A_m2 = A_cm2 * 1e-4
            i_y_m = i_y_cm * 1e-2
            
            # Stress check
            stress = max_chord_force / A_m2
            if stress > f_y:
                continue
            
            # Slenderness check
            if max_chord_length / i_y_m > max_slenderness_ratio:
                continue
            
            # Euler buckling check for compression
            if max_chord_force > 0:  # Assuming compression
                sigma_cr = np.pi**2 * E * (i_y_m / max_chord_length)**2
                if stress > sigma_cr:
                    continue
            
            chord_profile = profile_name
            break
        
        # Update chord members with uniform profile
        chord_updated = False
        if chord_profile:
            for m_idx in chord_indices:
                if member_profiles[m_idx] != chord_profile:
                    member_profiles[m_idx] = chord_profile
                    member_areas[m_idx] = hea_profiles[chord_profile][0] * 1e-4
                    chord_updated = True
        
        # Update web members individually
        web_updated = False
        for m_idx in web_indices:
            force = abs(member_forces[m_idx])
            i, j = members[m_idx]
            xi, zi = nodes[i]
            xj, zj = nodes[j]
            L = np.sqrt((xj - xi)**2 + (zj - zi)**2)
            
            if L < 1e-12:
                continue
            
            current_profile = member_profiles[m_idx]
            suitable_profile = None
            
            for profile_name in profile_names:
                A_cm2, I_y_cm4, i_y_cm = hea_profiles[profile_name]
                A_m2 = A_cm2 * 1e-4
                i_y_m = i_y_cm * 1e-2
                
                # Stress check
                stress = force / A_m2
                if stress > f_y:
                    continue
                
                # Slenderness check
                if L / i_y_m > max_slenderness_ratio:
                    continue
                
                # Euler buckling check for compression
                if member_forces[m_idx] < 0:  # Compression
                    sigma_cr = np.pi**2 * E * (i_y_m / L)**2
                    if stress > sigma_cr:
                        continue
                
                suitable_profile = profile_name
                break
            
            if suitable_profile and suitable_profile != current_profile:
                member_profiles[m_idx] = suitable_profile
                member_areas[m_idx] = hea_profiles[suitable_profile][0] * 1e-4
                web_updated = True
        
        if not chord_updated and not web_updated:
            break
    
    # Final FEA
    member_forces, displacements = solve_fea(nodes, members, member_areas, support_nodes, load_positions, load_values)
    
    # Build output
    line_elements = []
    for m_idx, (i, j) in enumerate(members):
        start = nodes[i]
        end = nodes[j]
        profile = member_profiles[m_idx]
        
        # Filter by minimum area
        if member_areas[m_idx] * 1e4 >= min_member_area_mm2 * 1e-2:  # Convert to cm2
            line_elements.append({
                "start": start,
                "end": end,
                "cross_section": profile
            })
    
    support_positions = [nodes[i] for i in support_nodes]
    
    loads = []
    for load_idx, load_val in zip(load_positions, load_values):
        x, z = nodes[load_idx]
        loads.append([x, z, load_val])
    
    result = {
        "description": f"Bowstring truss, span {span_m}m, {num_bays} bays, height {height_m}m",
        "line_elements": line_elements,
        "support": support_positions,
        "loads": loads
    }
    
    return result

if __name__ == "__main__":
    result = get_geometric_output()
    print(json.dumps(result))
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "geometric_output.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)