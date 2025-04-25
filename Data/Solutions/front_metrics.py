import os
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist


# === Objectives ===
objectives = [
    "Driver Violation",
    "Commute Distance",
    "Transport Machines",
    "Transport Attachments",
    "Machines",
    "Workers",
    "Attachments"
]


def get_methdod_paths(instance_folder: str):
    # === Automatically find all methods based on subfolders containing ParetoFront.csv ===
    method_paths = {}
    for root, dirs, files in os.walk(instance_folder):
        if "ParetoFront.csv" in files:
            method_name = os.path.basename(root)
            method_paths[method_name] = os.path.join(root, "ParetoFront.csv")

    if not method_paths:
        raise FileNotFoundError(f"No ParetoFront.csv files found in {instance_folder}")

    return method_paths



def calculate_pf_share(method_paths=None, print_interim_results=False):
    """
    Calculate the percentage share of each method's solutions in the global Pareto front.
    All results are returned as percentages (0–100, float).
    Returns a DataFrame with one row per method.
    """

    # Load all method data with objectives
    all_data = []
    method_data = {}
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        df_obj = df[objectives].copy()
        df_obj["Method"] = method
        all_data.append(df_obj)
        method_data[method] = df_obj

    all_data_concat = pd.concat(all_data, ignore_index=True)

    # Determine non-dominated solutions (globally across all methods)
    def is_dominated(row, others):
        return np.any(np.all(others <= row, axis=1) & np.any(others < row, axis=1))

    pareto_rows = []
    data_values = all_data_concat[objectives].values
    for i, row in enumerate(data_values):
        if not is_dominated(row, np.delete(data_values, i, axis=0)):
            pareto_rows.append(i)

    pareto_df = all_data_concat.iloc[pareto_rows].reset_index(drop=True)

    # For each method, count how many solutions in global Pareto front come from that method
    total_pareto = len(pareto_df)
    pf_share_results = {}
    for method in method_paths.keys():
        count = len(pareto_df[pareto_df["Method"] == method])
        pf_share_results[method] = (count / total_pareto) * 100 if total_pareto > 0 else 0.0

    result_df = pd.DataFrame({
        "PF-Share": pf_share_results
    }).T

    if print_interim_results:
        print("\n--- PF-Share values per method ---")
        print(result_df)

    return result_df



def calculate_dci(method_paths=None, print_interim_results=False):

    # === 3. Create global Pareto front including method assignment ===
    all_data = []
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        df = df[objectives].copy()
        df["Method"] = method
        all_data.append(df)

    all_data_concat = pd.concat(all_data, ignore_index=True)

    if print_interim_results:
        print("\n--- All solutions from all methods ---")
        print(all_data_concat)

    # Determine non-dominated solutions (globally across all methods)
    def is_dominated(row, others):
        return np.any(np.all(others <= row, axis=1) & np.any(others < row, axis=1))

    pareto_rows = []
    data_values = all_data_concat[objectives].values
    for i, row in enumerate(data_values):
        if not is_dominated(row, np.delete(data_values, i, axis=0)):
            pareto_rows.append(i)

    pareto_df = all_data_concat.iloc[pareto_rows].reset_index(drop=True)

    if print_interim_results:
        print("\n--- Combined Pareto Front ---")
        print(pareto_df)
    # === 3.1. Group Pareto front by method ===
    pareto_groups = {}
    for method in method_paths.keys():
        pareto_groups[method] = pareto_df[pareto_df["Method"] == method].reset_index(drop=True)
    if print_interim_results:
        print("\n--- Combined Pareto Front grouped by method ---")
        for method, group in pareto_groups.items():
            print(f"\n--- {method} ---")
            print(group)

    # === 4. Ideal, Nadir, and Upper Bound based on global Pareto front ===
    div = 5
    ideal_point = pareto_df[objectives].min()
    nadir_point = pareto_df[objectives].max()
    upper_bound = nadir_point + (nadir_point - ideal_point) / (2 * div)
    lower_bound = ideal_point

    box_size = (upper_bound - lower_bound) / div

    if print_interim_results:
        print("\n--- Ideal Point ---")
        print(ideal_point)
        print("\n--- Nadir Point ---")
        print(nadir_point)
        print("\n--- Upper Bound ---")
        print(upper_bound)
        print("\n--- Box Size ---")
        print(box_size)

    # === 4.2 Detect and remove objectives without variation ===
    valid_dims = box_size != 0
    if not valid_dims.all():
        removed = list(box_size[~valid_dims].index)
        if print_interim_results:
            print(f"\n⚠️  These objectives have no variation and are removed for DCI calculation: {removed}")

    # Adjusted grid assignment based on valid dimensions
    def get_grid_index(row):
        return tuple(((row[valid_dims] - lower_bound[valid_dims]) / box_size[valid_dims]).astype(int))

    # Record occupied boxes
    grid_cells_by_method = {method: set() for method in method_paths}
    cell_contributions = {}

    for method, df in pareto_groups.items():
        for _, row in df[objectives].iterrows():
            cell = get_grid_index(row)
            grid_cells_by_method[method].add(cell)

    # All occupied cells from all methods
    all_cells = set().union(*grid_cells_by_method.values())

    # === 4.3 Distance-based Contribution Degree (CD) calculation ===
    from math import sqrt

    cd_matrix = {method: {} for method in method_paths}
    m = valid_dims.sum()  # effective dimensionality after exclusion

    # Precompute grid cells of all solutions per method
    grid_index_by_method = {
        method: [get_grid_index(row) for _, row in df[objectives].iterrows()]
        for method, df in pareto_groups.items()
    }

    # For each occupied box, compute CD(P, h)
    for cell in all_cells:
        for method, grid_indices in grid_index_by_method.items():
            # Calculate minimum distance D(P, h)
            distances = [np.linalg.norm(np.array(cell) - np.array(p_cell)) for p_cell in grid_indices]
            D = min(distances)
            threshold = sqrt(m + 1)
            if D < threshold:
                CD = 1 - (D**2) / (m + 1)
                cd_matrix[method][cell] = CD
            else:
                cd_matrix[method][cell] = 0.0

    # Output: Example CD values
    if print_interim_results:
        print("\n--- Example Contribution Degrees ---")
        for method, contributions in cd_matrix.items():
            non_zero = {k: v for k, v in contributions.items() if v > 0}
            print(f"{method}: {list(non_zero.items())[:5]}")

    # === 4. Diversity Comparison Indicator (DCI) ===
    # === 4.4 Calculate final DCI value per method ===
    dci_result = {}
    S = len(all_cells)
    for method in method_paths:
        contribution_sum = sum(cd_matrix[method].get(cell, 0.0) for cell in all_cells)
        dci_result[method] = contribution_sum / S if S > 0 else 0.0


    # === 7. Result as table ===
    result_df = pd.DataFrame({
        "DCI": dci_result
    }).T

    if print_interim_results:
        print("\n--- DCI values per method ---")
        print(result_df)

    return result_df


def calculate_pci(method_paths=None, print_interim_results=False):



    # Load all method data with objectives
    all_data = []
    method_data = {}
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        df_obj = df[objectives].copy()
        df_obj["Method"] = method
        all_data.append(df_obj)
        method_data[method] = df_obj

    all_data_concat = pd.concat(all_data, ignore_index=True)

    # === Algorithm 1 Step 1: Non-dominated Selection S ← NondominanceSelection(...) ===
    def is_dominated(row, others):
        return np.any(np.all(others <= row, axis=1) & np.any(others < row, axis=1))

    data_values = all_data_concat[objectives].values
    pareto_rows = []
    for i, row in enumerate(data_values):
        if not is_dominated(row, np.delete(data_values, i, axis=0)):
            pareto_rows.append(i)

    S_df = all_data_concat.iloc[pareto_rows].reset_index(drop=True)

    # === Normalize S_df and each method's solution set for the objectives ===
    # Min-max normalization to [0,1] per objective
    for obj in objectives:
        min_val = S_df[obj].min()
        max_val = S_df[obj].max()
        if max_val > min_val:
            S_df[obj] = (S_df[obj] - min_val) / (max_val - min_val)
        else:
            S_df[obj] = 0.0  # If no variation, set to 0
        # Also normalize each method's set
        for method in method_data:
            method_min = min_val
            method_max = max_val
            if method_max > method_min:
                method_data[method][obj] = (method_data[method][obj] - method_min) / (method_max - method_min)
            else:
                method_data[method][obj] = 0.0

    if print_interim_results:
        print("\n--- Normalized Combined Pareto Front ---")
        print(S_df)
        print("\n--- Normalized Solutions per Method ---")
        for method, df in method_data.items():
            print(f"\n--- {method} ---")
            print(df)

    S_values = S_df[objectives].values

    # === Algorithm 1 Step 2: Clustering(S) using Algorithm 2 ===
    # === Algorithm 2 Step 1: FindSortPair(S, σ) ===
    from scipy.special import factorial
    m = len(objectives)
    N = len(S_values)
    sigma = 1 / (((N * factorial(m - 1, exact=True)) ** (1 / (m - 1))) - (m / 2))
    #sigma = max(sigma, 1e-6)
    if print_interim_results:
        print(f"\n--- Calculated sigma threshold for clustering: {sigma:.6f}")

    def dominance_distance(p, Q):
        # dominance distance of point p to set Q
        # d(p,Q) = min_{q in Q} max(0, p_i - q_i)
        if len(Q) == 0:
            return 0.0
        min_q = np.min(Q, axis=0)
        diffs = np.where(p > min_q, p - min_q, 0)
        return np.linalg.norm(diffs)

    # Step 2.1: Find all valid pairs (si, sj) with max(D(si, sj), D(sj, si)) ≤ σ
    pairs = []
    n = len(S_values)
    for i in range(n):
        for j in range(i + 1, n):
            d_ij = dominance_distance(S_values[i], S_values[j:j+1])
            d_ji = dominance_distance(S_values[j], S_values[i:i+1])
            dist = max(d_ij, d_ji)
            if dist <= sigma:
                pairs.append((dist, i, j))

    # Step 2.2: Sort pairs by distance
    pairs.sort()

    if print_interim_results:
        print(len(pairs), "valid pairs of points with distances for the pareto front length of", len(S_values))


    # Step 2.3: Initialize clusters C1 ← s1, C2 ← s2, ..., Cn ← sn
    parent = list(range(n))

    def find(u):
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    def union(u, v):
        pu, pv = find(u), find(v)
        if pu != pv:
            parent[pu] = pv

    # Step 2.4: For each pair, locate clusters and merge if all pairwise dominance distances ≤ σ (Algorithm 2, full check)
    for dist, i, j in pairs:
        root_i, root_j = find(i), find(j)
        if root_i == root_j:
            continue

        cluster_i = [idx for idx in range(n) if find(idx) == root_i]
        cluster_j = [idx for idx in range(n) if find(idx) == root_j]

        any_within_sigma = False
        for a in cluster_i:
            for b in cluster_j:
                d_ab = dominance_distance(S_values[a], S_values[b:b+1])
                d_ba = dominance_distance(S_values[b], S_values[a:a+1])
                if d_ab <= sigma and d_ba <= sigma:
                    any_within_sigma = True
                    break
            if any_within_sigma:
                break

        if any_within_sigma:
            union(i, j)

    # Step 2.5: Return clusters C = {C1, ..., Ck} with |Ci| > 0
    clusters = {}
    for idx in range(n):
        root = find(idx)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(idx)

    cluster_points = [S_values[cluster_idxs] for cluster_idxs in clusters.values()]

    if print_interim_results:
        print("\n--- Clusters ---")
        for i, cluster in enumerate(cluster_points):
            print(f"Cluster {i} ({len(cluster)} points):")
            for point in cluster:
                print(f"  {np.round(point, 4).tolist()}")
            print("-" * 40)
        print("\nCluster assignments (root index -> point indices):")
        print(clusters)


    # === Algorithm 1 Step 3–14: Calculate PCI for each method ===
    # For each approximation set Pi and cluster Cj:
    # if Pi_j = Pi ∩ Cj has < 2 solutions → use min D(p, Cj)
    # else → use D'(Pi_j, Cj)
    pci_result = {}
    # --- Helper: set-to-set dominance distance ---
    def dominance_distance_set(P, Q):
        total_distance = 0.0
        for q in Q:
            distances = []
            for p in P:
                diffs = np.where(p > q, p - q, 0)
                distances.append(np.linalg.norm(diffs))
            total_distance += min(distances)
        return total_distance

    for method in method_paths.keys():
        X = S_df[S_df["Method"] == method][objectives].values
        pci_sum = 0.0
        for cluster in cluster_points:
            # Get the indices of points from the method that belong to the current cluster
            method_points_in_cluster = []
            for point in cluster:
                for idx, x in enumerate(X):
                    if np.allclose(x, point, atol=1e-8):
                        method_points_in_cluster.append(x)
            method_points_in_cluster = np.array(method_points_in_cluster)


            if len(method_points_in_cluster) < 2:
                # Use minimum dominance distance from X to cluster
                min_dist = min(dominance_distance(x, cluster) for x in X)
                pci_sum += min_dist
            else:
                # Use set-to-set dominance distance
                pci_sum += dominance_distance_set(method_points_in_cluster, cluster)

        pci_result[method] = pci_sum / len(cluster_points) if len(cluster_points) > 0 else 0.0

    # === Algorithm 1 Step 15: Return PCI(P1), ..., PCI(Pn) ===
    result_df = pd.DataFrame({
        "PCI": pci_result
    }).T

    if print_interim_results:
        print("\n--- PCI values per method ---")
        print(result_df)

    return result_df


def calculate_spread(method_paths=None, print_interim_results=False):
    """
    Calculate the spread metric for each method's Pareto front.
    All objectives are min-max normalized to [0, 1] (using global min and max across all methods) before calculating the spread.
    Returns a DataFrame with one row per method.
    """
    def spread(front):
        front_sorted = front[np.argsort(front[:, 0])]
        distances = [np.linalg.norm(front_sorted[i + 1] - front_sorted[i]) for i in range(len(front_sorted) - 1)]
        return np.std(distances) / np.mean(distances) if np.mean(distances) > 0 else 0

    # Load all method data for objectives
    all_data = []
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        all_data.append(df[objectives])
    all_data_concat = pd.concat(all_data, ignore_index=True)

    # Compute min and max per objective for normalization
    min_point = all_data_concat.min().to_numpy()
    max_point = all_data_concat.max().to_numpy()
    ranges = np.where(max_point - min_point != 0, max_point - min_point, 1)  # avoid division by zero

    spread_results = {}
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        front = df[objectives].to_numpy()
        normalized_front = (front - min_point) / ranges
        normalized_front = np.clip(normalized_front, 0, 1)  # Safety
        spread_results[method] = spread(normalized_front)

    result_df = pd.DataFrame({
        "Spread": spread_results
    }).T

    if print_interim_results:
        print("\n--- Spread values per method ---")
        print(result_df)

    return result_df


def calculate_hypervolume(method_paths=None, print_interim_results=False):
    """
    Calculate the normalized hypervolume for each method's Pareto front using min-max normalized objectives.
    Returns a DataFrame with one row per method.
    The hypervolume is computed after min-max normalizing all objectives to [0, 1] based on the global min and max.
    """
    # Helper: compute the hypervolume using shifted (1 - normalized) front, reference point at (1,...,1)
    def shifted_hypervolume(front, min_point, max_point):
        # Here, front is already normalized and shifted (1 - normalized)
        return np.sum(np.prod(front, axis=1))

    # Load all method data for objectives
    all_data = []
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        all_data.append(df[objectives])
    all_data_concat = pd.concat(all_data, ignore_index=True)

    # Compute min and max per objective for normalization
    min_point = all_data_concat.min().to_numpy()
    max_point = all_data_concat.max().to_numpy()

    hypervolume_results = {}
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        front = df[objectives].to_numpy()
        # Min-max normalization to [0, 1], safer version to avoid division by zero
        ranges = np.where(max_point - min_point != 0, max_point - min_point, 1)  # avoid division by zero
        normalized_front = (front - min_point) / ranges
        normalized_front = np.clip(normalized_front, 0, 1)  # Safety

        # Shift for hypervolume calculation: reference point at (1,...,1)
        shifted_front = 1 - normalized_front
        # Compute hypervolume as the sum of the hypercubes (product of shifted values)
        normalized_hv = np.sum(np.prod(shifted_front, axis=1))
        hypervolume_results[method] = normalized_hv

    result_df = pd.DataFrame({
        "Hypervolume": hypervolume_results
    }).T

    if print_interim_results:
        print("\n--- Hypervolume values per method (normalized objectives) ---")
        print(result_df)

    return result_df



if __name__ == "__main__":
    instance = "a10_o107_m5_an57_ar12"
    method_paths = get_methdod_paths(instance)

    # Calculate all metrics
    pci_result = calculate_pci(method_paths)
    dci_result = calculate_dci(method_paths)
    pf_share_result = calculate_pf_share(method_paths)
    spread_result = calculate_spread(method_paths)
    hypervolume_result = calculate_hypervolume(method_paths)

    # Combine all metrics
    combined_result = pd.concat([pf_share_result, pci_result, dci_result, spread_result, hypervolume_result], axis=0)

    # Special formatting
    formatted_result = combined_result.copy()

    # Format PF-Share: integer + percent sign
    if "PF-Share" in formatted_result.index:
        pf_row = formatted_result.loc["PF-Share"]
        formatted_pf_row = pf_row.round(0).astype(int).astype(str) + "%"
        # Convert DataFrame to object dtype before inserting text values to avoid FutureWarning
        formatted_result = formatted_result.astype(object)
        formatted_result.loc["PF-Share"] = formatted_pf_row

    # Round other metrics to 4 decimals
    for idx in formatted_result.index:
        if idx != "PF-Share":
            formatted_result.loc[idx] = formatted_result.loc[idx].astype(float).round(4)

    # Add thumbs up/down per metric
    annotated_result = formatted_result.copy()
    for idx in formatted_result.index:
        if idx == "PF-Share":
            continue  # Skip annotations for PF-Share
        row = formatted_result.loc[idx]
        # Determine best/worst: for PCI and Spread, best is min; for others, best is max
        if idx in ["PCI", "Spread"]:
            best_method = row.astype(float).idxmin()
            worst_method = row.astype(float).idxmax()
        else:
            best_method = row.astype(float).idxmax()
            worst_method = row.astype(float).idxmin()
        for col in formatted_result.columns:
            if col == best_method:
                annotated_result.at[idx, col] = f"{formatted_result.at[idx, col]} 👍"
            if col == worst_method:
                annotated_result.at[idx, col] = f"{formatted_result.at[idx, col]} 👎"

    # Print final summary with custom formatting for readability
    print("\n=== Combined Metrics Summary ===\n")
    for idx, row in annotated_result.iterrows():
        print(f"{idx}")
        for method in annotated_result.columns:
            print(f"  {method.ljust(8)}: {str(row[method]).ljust(15)}")
        print()  # blank line after each metric


# === Aggregated 3D Plotting ===
import matplotlib.pyplot as plt

def plot_aggregated_3d(method_paths, instance_name=None):
    """
    Create 3D scatter plots of the aggregated objectives for each method.
    - X-axis: Driver Violation
    - Y-axis: Sum of distance-based objectives (Commute Distance + Transport Machines + Transport Attachments)
    - Z-axis: Sum of resource-based objectives (Machines + Workers + Attachments)
    """
    for method, path in method_paths.items():
        df = pd.read_csv(path)

        x = df["Driver Violation"]
        y = df[["Commute Distance", "Transport Machines", "Transport Attachments"]].sum(axis=1)
        z = df[["Machines", "Workers", "Attachments"]].sum(axis=1)

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c='green', marker='o')

        ax.set_xlabel("Driver Violation")
        ax.set_ylabel("Total Distance")
        ax.set_zlabel("Total Resources")

        title = f"{method} - Aggregated 3D Plot"
        if instance_name:
            title = f"{instance_name} - {method} Aggregated 3D"
        ax.set_title(title)

        plt.tight_layout()
        plt.show()

# Call plot_aggregated_3d automatically after metrics output
#plot_aggregated_3d(method_paths, instance)

""" === Metrics === 

# === Interpretation ===

# PCI (Performance Comparison Indicator):
# Measures how well the solutions from each method dominate the reference clusters constructed from the combined Pareto front.
# Lower PCI values are better, indicating solutions are closer to dominating the entire reference space.

# DCI (Diversity Comparison Indicator):
# Measures how well the solutions from each method are distributed across the objective space.
# Higher DCI values indicate better diversity (more widespread and evenly distributed solutions).

# PF-Share (Pareto Front Share):
# Measures the proportion of globally non-dominated solutions that each method contributes.
# Higher PF-Share values indicate that a method produced more top-quality solutions.

# Spread:
# Measures the uniformity of the spacing between consecutive solutions.
# Lower Spread values are better, indicating solutions are evenly spread along the Pareto front.

# Hypervolume:
# Measures the volume of the objective space dominated by a solution set relative to a reference point.
# Higher Hypervolume values are better, indicating better convergence and coverage of the objective space.

# === Categories ===

# 1. Diversity (distribution and spread of solutions):
#    - DCI (Diversity Comparison Indicator)
#    - Spread

# 2. Convergence (how close solutions are to the ideal front):
#    - PCI (Performance Comparison Indicator)
#    - Hypervolume

# 3. Contribution / Coverage (relative contribution of methods):
#    - PF-Share
"""