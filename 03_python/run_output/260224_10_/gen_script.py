import numpy as np
import json
import os
import math

def get_geometric_output():
    # Input parameters from semantic outline
    span_m = 30
    length_y_m = 15
    num_bays = 10
    typology = "bowstring"
    
    # Load parameters
    snow_kN_per_m2 = 4.5
    roof_cladding_kN_per_m2 = 10.0
    self_weight_kN_per_m2 = 0.3
    
    # System parameters
    ULS_gamma_G = 1.35
    ULS_gamma_Q = 1.5
    max_iterations = 40
    max_slenderness_ratio = 200
    f_y = 235000  # kN/m2 (S235 steel)
    E = 210000000  # kN/m2
    min_area_mm2 = 1
    
    # Height calculation for bowstring (ratio = 4)
    height_m = span_m / 4.0
    
    # Tributary width calculation
    tributary_width_m = length_y_m  # Single truss spans full width
    
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
        "HEA260": {"A": 86.8, "I_y": 10450, "i_y": 10.9},
        "HEA280": {"A": 97.3, "I_y": 13670, "i_y": 11.8},
        "HEA300": {"A": 112.5, "I_y": 18260, "i_y": 12.7},
        "HEA320": {"A": 124.4, "I_y": 22930, "i_y": 13.6},
        "HEA340": {"A": 133.5, "I_y": 27690, "i_y": 14.4},
        "HEA360": {"A": 142.6, "I_y": 33090, "i_y": 15.2},
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
    
    # Node positioning
    node_spacing = span_m / num_bays
    
    # Bottom chord nodes (straight line)
    bottom_nodes = []
    for i in range(num_bays + 1):
        x = i * node_spacing
        z = 0.0
        bottom_nodes.append([x, z])
    
    # Top chord nodes (bowstring - parabolic arch)
    top_nodes = []
    for i in range(1, num_bays):  # Interior nodes only
        x = i * node_spacing
        # Parabolic equation: z = 4*h*x*(L-x)/L^2
        z = 4 * height_m * x * (span_m - x) / (span_m * span_m)
        top_nodes.append([x, z])
    
    # All nodes
    nodes = bottom_nodes + top_nodes
    num_bottom_nodes = len(bottom_nodes)
    num_top_nodes = len(top_nodes)
    
    # Member connectivity
    members = []
    
    # Bottom chord members
    for i in range(num_bays):
        members.append([i, i + 1])
    
    # Top chord members (connecting interior top nodes)
    for i in range(num_top_nodes - 1):
        top_i = num_bottom_nodes + i
        top_j = num_bottom_nodes + i + 1
        members.append([top_i, top_j])
    
    # Web members (diagonals and verticals for bowstring)
    # Connect each bottom node to nearest top nodes
    for i in range(num_bays + 1):
        if i == 0:  # First bottom node
            if num_top_nodes > 0:
                members.append([0, num_bottom_nodes])  # To first top node
        elif i == num_bays:  # Last bottom node
            if num_top_nodes > 0:
                members.append([num_bays, num_bottom_nodes + num_top_nodes - 1])  # To last top node
        else:  # Interior bottom nodes
            if i - 1 < num_top_nodes:
                members.append([i, num_bottom_nodes + i - 1])  # Vertical to corresponding top node
    
    # Additional diagonal members for bowstring
    for i in range(1, num_bays):
        if i - 1 < num_top_nodes and i < num_top_nodes:
            # Left diagonal
            if i - 1 >= 0:
                members.append([i - 1, num_bottom_nodes + i - 1])
            # Right diagonal
            if i + 1 <= num_bays:
                members.append([i + 1, num_bottom_nodes + i - 1])
    
    # Support nodes
    support_nodes = [0, num_bays]
    
    # Load calculation
    G = self_weight_kN_per_m2 + roof_cladding_kN_per_m2
    Q = snow_kN_per_m2
    q_uls = ULS_gamma_G * G + ULS_gamma_Q * Q
    
    # Point loads at top chord nodes
    loads = []
    for i in range(num_top_nodes):
        node_idx = num_bottom_nodes + i
        x, z = nodes[node_idx]
        
        # Tributary length
        if i == 0 or i == num_top_nodes - 1:
            trib_length = node_spacing / 2
        else:
            trib_length = node_spacing
        
        Fz = -q_uls * tributary_width_m * trib_length
        loads.append([x, z, Fz])
    
    # Initialize member areas with smallest profile
    member_profiles = ["HEA100"] * len(members)
    
    # FEA and optimization loop
    for iteration in range(max_iterations):
        try:
            # Assemble stiffness matrix
            num_nodes = len(nodes)
            num_dofs = 2 * num_nodes
            K = np.zeros((num_dofs, num_dofs))
            
            for m_idx, (i, j) in enumerate(members):
                profile = member_profiles[m_idx]
                A = hea_profiles[profile]["A"] * 1e-4  # cm2 to m2
                
                xi, zi = nodes[i]
                xj, zj = nodes[j]
                L = math.sqrt((xj - xi)**2 + (zj - zi)**2)
                
                if L == 0:
                    continue
                
                c = (xj - xi) / L
                s = (zj - zi) / L
                
                k_local = (E * A / L) * np.array([
                    [1, 0, -1, 0],
                    [0, 0, 0, 0],
                    [-1, 0, 1, 0],
                    [0, 0, 0, 0]
                ])
                
                T = np.array([
                    [c, s, 0, 0],
                    [-s, c, 0, 0],
                    [0, 0, c, s],
                    [0, 0, -s, c]
                ])
                
                k_global = T.T @ k_local @ T
                
                dofs = [2*i, 2*i+1, 2*j, 2*j+1]
                for p in range(4):
                    for q in range(4):
                        K[dofs[p], dofs[q]] += k_global[p, q]
            
            # Apply boundary conditions
            fixed_dofs = []
            for support_node in support_nodes:
                fixed_dofs.extend([2*support_node, 2*support_node+1])
            
            free_dofs = [dof for dof in range(num_dofs) if dof not in fixed_dofs]
            
            # Load vector
            F = np.zeros(num_dofs)
            for x, z, Fz in loads:
                # Find node closest to load position
                min_dist = float('inf')
                load_node = 0
                for n_idx, (nx, nz) in enumerate(nodes):
                    dist = math.sqrt((nx - x)**2 + (nz - z)**2)
                    if dist < min_dist:
                        min_dist = dist
                        load_node = n_idx
                F[2*load_node + 1] += Fz
            
            # Solve
            K_ff = K[np.ix_(free_dofs, free_dofs)]
            F_f = F[free_dofs]
            
            u_f = np.linalg.solve(K_ff, F_f)
            
            # Calculate member stresses
            u = np.zeros(num_dofs)
            u[free_dofs] = u_f
            
            member_stresses = []
            for m_idx, (i, j) in enumerate(members):
                profile = member_profiles[m_idx]
                A = hea_profiles[profile]["A"] * 1e-4  # cm2 to m2
                
                xi, zi = nodes[i]
                xj, zj = nodes[j]
                L = math.sqrt((xj - xi)**2 + (zj - zi)**2)
                
                if L == 0:
                    member_stresses.append(0)
                    continue
                
                c = (xj - xi) / L
                s = (zj - zi) / L
                
                u_local = np.array([
                    c * u[2*i] + s * u[2*i+1],
                    -s * u[2*i] + c * u[2*i+1],
                    c * u[2*j] + s * u[2*j+1],
                    -s * u[2*j] + c * u[2*j+1]
                ])
                
                strain = (u_local[2] - u_local[0]) / L
                stress = E * strain
                member_stresses.append(stress)
            
            # Update member profiles
            updated = False
            for m_idx, stress in enumerate(member_stresses):
                i, j = members[m_idx]
                xi, zi = nodes[i]
                xj, zj = nodes[j]
                L = math.sqrt((xj - xi)**2 + (zj - zi)**2)
                
                current_profile = member_profiles[m_idx]
                
                # Find suitable profile
                for profile_name in hea_profiles:
                    A = hea_profiles[profile_name]["A"] * 1e-4  # cm2 to m2
                    i_y = hea_profiles[profile_name]["i_y"] * 1e-2  # cm to m
                    
                    # Check stress
                    if abs(stress) > 1e-6:
                        stress_ratio = abs(stress) / f_y
                        if stress_ratio > 1.0:
                            continue
                    
                    # Check slenderness
                    if L / i_y > max_slenderness_ratio:
                        continue
                    
                    # Check Euler buckling for compression
                    if stress < 0:  # Compression
                        sigma_cr = (math.pi**2 * E * i_y**2) / (L**2)
                        if abs(stress) > sigma_cr:
                            continue
                    
                    # Check minimum area
                    if A * 1e6 < min_area_mm2:  # Convert to mm2
                        continue
                    
                    # Profile is suitable
                    if profile_name != current_profile:
                        member_profiles[m_idx] = profile_name
                        updated = True
                    break
            
            if not updated:
                break
                
        except np.linalg.LinAlgError:
            print(f"Singular matrix at iteration {iteration}")
            break
    
    # Build output
    line_elements = []
    for m_idx, (i, j) in enumerate(members):
        start = nodes[i]
        end = nodes[j]
        profile = member_profiles[m_idx]
        
        # Check minimum area
        A = hea_profiles[profile]["A"]  # cm2
        if A * 100 >= min_area_mm2:  # Convert cm2 to mm2
            line_elements.append({
                "start": start,
                "end": end,
                "cross_section": profile
            })
    
    support_positions = [nodes[i] for i in support_nodes]
    
    result = {
        "description": f"Bowstring truss, span {span_m}m, {num_bays} bays, height {height_m:.1f}m",
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