def debug_print(msg, print_debug=False):
    if print_debug:
        print(msg)

import os
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import matplotlib.pyplot as plt

from pymoo.indicators.hv import HV
import numpy as np
import pandas as pd


# === Instance ===
#instance = "a3_o80_m10_an10_ar9_reduced"
instance = "a10_o107_m5_an57_ar12"
#instance = "a10_o114_m6_an57_ar11"
#instance = "a10_o128_m6_an51_ar13"
#instance = "a10_o144_m6_an53_ar12"
#instance = "a15_o170_m9_an80_ar18"
#instance = "a20_o236_m12_an106_ar24"
#instance = "a25_o306_m13_an127_ar31"
#instance = "a30_o355_m18_an148_ar42"
#instance = "a40_o476_m22_an215_ar51"
#instance = "a50_o578_m28_an276_ar66"
#instance = "Test"

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
    all_solutions = []
    for root, dirs, files in os.walk(instance_folder):
        if "ParetoFront.csv" in files:
            method_name = os.path.basename(root)
            path = os.path.join(root, "ParetoFront.csv")
            method_paths[method_name] = path

            # Load solutions and store them for duplicate analysis
            df = pd.read_csv(path)
            if set(objectives).issubset(df.columns):
                all_solutions.append(df[objectives])
            else:
                print(f"⚠️  Warning: {method_name} ParetoFront.csv does not contain all objectives.")

    if not method_paths:
        raise FileNotFoundError(f"No ParetoFront.csv files found in {instance_folder}")

    # === Analyze duplicates across methods ===
    if all_solutions:
        combined = pd.concat(all_solutions, ignore_index=True)
        duplicated = combined.duplicated(keep=False)
        duplicate_entries = combined[duplicated]

        if not duplicate_entries.empty:
            print("\n=== Duplicate Solutions Across Methods (ignoring method assignment) ===")
            print(f"Found {len(duplicate_entries)} duplicate entries (counting all appearances).")
        else:
            print("\nNo duplicate solutions across methods found.")

    return method_paths



def calculate_pf_share(method_paths=None, print_debug=False):
    """
    Calculate the percentage share of each method's solutions in the global Pareto front.
    All results are returned as percentages (0–100, float).
    Returns a DataFrame with one row per method.
    """

    debug_print("\n--- PF-Share Calculation Debug---", print_debug)

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

    debug_print("\n--- PF-Share values per method ---", print_debug)
    debug_print(result_df, print_debug)

    return result_df



def calculate_dci(method_paths=None, print_debug=False):

    debug_print("\n--- DCI Calculation Debug---", print_debug)

    # === 3. Create global Pareto front including method assignment ===
    all_data = []
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        df = df[objectives].copy()
        df["Method"] = method
        all_data.append(df)

    all_data_concat = pd.concat(all_data, ignore_index=True)

    debug_print("\n--- All solutions from all methods ---", print_debug)
    for method, df in method_paths.items():
        debug_print(f"\n--- {method} ---", print_debug)
        debug_print(df, print_debug)

    # Determine non-dominated solutions (globally across all methods)
    def is_dominated(row, others):
        return np.any(np.all(others <= row, axis=1) & np.any(others < row, axis=1))

    pareto_rows = []
    data_values = all_data_concat[objectives].values
    for i, row in enumerate(data_values):
        if not is_dominated(row, np.delete(data_values, i, axis=0)):
            pareto_rows.append(i)

    pareto_df = all_data_concat.iloc[pareto_rows].reset_index(drop=True)

    debug_print("\n--- Combined Pareto Front ---", print_debug)
    debug_print(pareto_df, print_debug)
    # === 3.1. Group Pareto front by method ===
    pareto_groups = {}
    for method in method_paths.keys():
        pareto_groups[method] = pareto_df[pareto_df["Method"] == method].reset_index(drop=True)
    debug_print("\n--- Combined Pareto Front grouped by method ---", print_debug)
    for method, group in pareto_groups.items():
        debug_print(f"\n--- {method} ---", print_debug)
        debug_print(group, print_debug)

    # === 4. Ideal, Nadir, and Upper Bound based on global Pareto front ===
    div = 5
    ideal_point = pareto_df[objectives].min()
    nadir_point = pareto_df[objectives].max()
    upper_bound = nadir_point + (nadir_point - ideal_point) / (2 * div)
    lower_bound = ideal_point

    box_size = (upper_bound - lower_bound) / div

    debug_print("\n--- Ideal Point ---", print_debug)
    debug_print(ideal_point, print_debug)
    debug_print("\n--- Nadir Point ---", print_debug)
    debug_print(nadir_point, print_debug)
    debug_print("\n--- Upper Bound ---", print_debug)
    debug_print(upper_bound, print_debug)
    debug_print("\n--- Box Size ---", print_debug)
    debug_print(box_size, print_debug)

    # === 4.2 Detect and remove objectives without variation ===
    valid_dims = box_size != 0
    if not valid_dims.all():
        removed = list(box_size[~valid_dims].index)
        debug_print(f"\n⚠️  These objectives have no variation and are removed for DCI calculation: {removed}", print_debug)

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
    debug_print("\n--- Example Contribution Degrees ---", print_debug)
    for method, contributions in cd_matrix.items():
        non_zero = {k: v for k, v in contributions.items() if v > 0}
        debug_print(f"{method}: {list(non_zero.items())[:5]}", print_debug)

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

    debug_print("\n--- DCI values per method ---", print_debug)
    debug_print(result_df, print_debug)

    return result_df


def calculate_pci(method_paths=None, print_debug=False):

    debug_print("\n--- PCI Calculation Debug---", print_debug)

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

    debug_print(f"\n[DEBUG] After Pareto selection: S_df shape = {S_df.shape}", print_debug)
    debug_print(S_df.head(), print_debug)

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

    debug_print("\n--- Normalized Combined Pareto Front ---", print_debug)
    debug_print(f"[DEBUG] S_df shape: {S_df.shape}", print_debug)
    debug_print(S_df.head(), print_debug)
    debug_print("\n--- Normalized Solutions per Method ---", print_debug)
    for method, df in method_data.items():
        debug_print(f"\n--- {method} ---", print_debug)
        debug_print(f"[DEBUG] {method} normalized shape: {df.shape}", print_debug)
        debug_print(df.head(), print_debug)
        debug_print(f"[DEBUG] {method} sample values:\n{df[objectives].head(3)}", print_debug)

    S_values = S_df[objectives].values

    # === Algorithm 1 Step 2: Clustering(S) using Algorithm 2 ===
    # === Algorithm 2 Step 1: FindSortPair(S, σ) ===
    from scipy.special import factorial
    m = len(objectives)
    N = len(S_values)
    sigma = 1 / (((N * factorial(m - 1, exact=True)) ** (1 / (m - 1))) - (m / 2))
    #sigma = max(sigma, 1e-6)
    debug_print(f"\n--- Calculated sigma threshold for clustering: {sigma:.6f}", print_debug)

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

    debug_print(f"\n[DEBUG] Found {len(pairs)} valid pairs (sigma={sigma:.6f}) for {len(S_values)} Pareto points.", print_debug)
    debug_print("[DEBUG] Sample pair distances:", print_debug)
    for sample in pairs[:5]:
        debug_print(f"  Distance: {sample[0]:.6f}, Indices: ({sample[1]}, {sample[2]})", print_debug)


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

    debug_print("\n--- Clusters ---", print_debug)
    debug_print(f"[DEBUG] Number of clusters: {len(cluster_points)}", print_debug)
    for i, cluster in enumerate(cluster_points[:5]):
        debug_print(f"Cluster {i} ({len(cluster)} points):", print_debug)
        for point in cluster[:3]:
            debug_print(f"  {np.round(point, 4).tolist()}", print_debug)
        if len(cluster) > 3:
            debug_print("  ...", print_debug)
        # Add bounding box volume calculation
        mins = np.min(cluster, axis=0)
        maxs = np.max(cluster, axis=0)
        volume = np.prod(maxs - mins)
        # Add average internal distance calculation
        if len(cluster) > 1:
            from scipy.spatial.distance import pdist
            avg_internal_distance = np.mean(pdist(cluster))
        else:
            avg_internal_distance = 0.0
        debug_print(f"  Bounding Box Volume: {volume:.6f}", print_debug)
        debug_print(f"  Avg. Internal Distance: {avg_internal_distance:.6f}", print_debug)
        debug_print("-" * 40, print_debug)
    debug_print("\n[DEBUG] Cluster assignments (root index -> point indices):", print_debug)
    for k, v in list(clusters.items())[:5]:
        debug_print(f"  Root {k}: {v}", print_debug)
    if len(clusters) > 5:
        debug_print("  ...", print_debug)

    # --- New Debug Print: Distribution of Methods inside Clusters ---
    debug_print("\n[DEBUG] Method distribution per cluster:", print_debug)
    for i, cluster in enumerate(cluster_points):
        method_counts = {}
        for point in cluster:
            for idx, x in enumerate(S_values):
                if np.allclose(x, point, atol=1e-8):
                    method = S_df.iloc[idx]["Method"]
                    method_counts[method] = method_counts.get(method, 0) + 1
        debug_print(f"Cluster {i} ({len(cluster)} points): {method_counts}", print_debug)
    debug_print("-" * 50, print_debug)


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

        for cluster_idx, cluster in enumerate(cluster_points):
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
  
                debug_print(f"[DEBUG] {method} cluster {cluster_idx} (len={len(cluster)}): <2 points, Point-to-set distance={min_dist:.6f}", print_debug)
            else:
                # Use set-to-set dominance distance
                dset = dominance_distance_set(method_points_in_cluster, cluster)
                min_dist = min(dominance_distance(x, cluster) for x in X)
                pci_sum += min(dset, min_dist)

                if dset < min_dist:
                    debug_print(f"[DEBUG] {method} cluster {cluster_idx} (len={len(cluster)}): Set-to-set distance={dset:.6f} < Point-to-set distance={min_dist:.6f}", print_debug)
                else:
                    debug_print(f"[DEBUG] {method} cluster {cluster_idx} (len={len(cluster)}): Point-to-set distance={min_dist:.6f} < Set-to-set distance={dset:.6f}", print_debug)


        pci_result[method] = pci_sum / len(cluster_points) if len(cluster_points) > 0 else 0.0




    # === Algorithm 1 Step 15: Return PCI(P1), ..., PCI(Pn) ===
    result_df = pd.DataFrame({
        "PCI": pci_result
    }).T

    debug_print("\n--- PCI values per method ---", print_debug)
    debug_print(result_df, print_debug)

    return result_df


def calculate_spread(method_paths=None, print_debug=False):
    """
    Calculate the spread metric for each method's Pareto front.
    All objectives are min-max normalized to [0, 1] (using global min and max across all methods) before calculating the spread.
    Returns a DataFrame with one row per method.
    """
    debug_print("\n--- Spread Calculation Debug---", print_debug)

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

    debug_print("\n--- Spread values per method ---", print_debug)
    debug_print(result_df, print_debug)

    return result_df

def calculate_hypervolume_hypercubes(method_paths=None, print_interim_results=False):
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
        print("\n--- Hypervolume values per method hypercubes ---")
        print(result_df)

    return result_df

def calculate_hypervolume_monte_carlo(method_paths=None, samples=50000, print_interim_results=False):
    """
    Approximate the normalized hypervolume for each method's Pareto front using Monte Carlo sampling.
    Returns a DataFrame with one row per method.
    """
    debug_print("\n--- Monte Carlo Hypervolume Calculation Debug ---", print_interim_results)

    # Load all method data
    all_data = []
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        all_data.append(df[objectives])
    all_data_concat = pd.concat(all_data, ignore_index=True)

    # Min-Max Normalization
    min_point = all_data_concat.min().to_numpy()
    max_point = all_data_concat.max().to_numpy()
    ranges = np.where(max_point - min_point != 0, max_point - min_point, 1)  # avoid division by zero

    hypervolume_results = {}
    

    for method, path in method_paths.items():
        df = pd.read_csv(path)
        front = df[objectives].to_numpy()
        normalized_front = (front - min_point) / ranges
        normalized_front = np.clip(normalized_front, 0, 1)

        # Generate random sample points in [0, 1]^n
        sample_points = np.random.rand(samples, normalized_front.shape[1])
        
        print(f"[DEBUG] {method} - Sample points shape: {sample_points.shape}")
    
        # Check if each sample point is dominated by at least one solution in the front
        dominated = np.any(np.all(normalized_front <= sample_points[:, None, :], axis=2), axis=1)

        # Hypervolume approximation: fraction of dominated samples
        hv_approx = np.mean(dominated)
        hypervolume_results[method] = hv_approx

        debug_print(f"[DEBUG] {method} approximated hypervolume (Monte Carlo, {samples} samples): {hv_approx:.6f}", print_interim_results)

    result_df = pd.DataFrame({
        "Monte Carlo Hypervolume": hypervolume_results
    }).T

    debug_print("\n--- Monte Carlo Hypervolume values per method ---", print_interim_results)
    debug_print(result_df, print_interim_results)

    return result_df

def calculate_average_monte_carlo_hypervolume(method_paths, print_debug = False, seeds=[42, 43, 44, 45, 46], samples=50000):
    results = []
    for seed in seeds:
        np.random.seed(seed)
        hv_result = calculate_hypervolume_monte_carlo(method_paths, samples=samples)
        results.append(hv_result.T)

    avg_result = pd.concat(results).groupby(level=0).mean().T
    
    debug_print("\n--- Average Monte Carlo Hypervolume values per method ---", print_debug)
    debug_print(avg_result, print_debug)

    return avg_result

def calculate_exact_hypervolume(method_paths=None, print_debug=False):
    """
    Calculate the exact hypervolume for each method's Pareto front.
    """

    debug_print("\n--- Exact Hypervolume Calculation Debug ---", print_debug)

    # Load all method data
    all_data = []
    for method, path in method_paths.items():
        df = pd.read_csv(path)
        all_data.append(df[objectives])
    all_data_concat = pd.concat(all_data, ignore_index=True)

    # Min-Max Normalization
    min_point = all_data_concat.min().to_numpy()
    max_point = all_data_concat.max().to_numpy()
    ranges = np.where(max_point - min_point != 0, max_point - min_point, 1)  # avoid division by zero

    hypervolume_results = {}

    for method, path in method_paths.items():
        df = pd.read_csv(path)
        front = df[objectives].to_numpy()
        normalized_front = (front - min_point) / ranges
        normalized_front = np.clip(normalized_front, 0, 1)

        # Reference point for normalized data (all ones)
        ref_point = np.ones(normalized_front.shape[1])

        # Calculate Hypervolume
        hv = HV(ref_point)
        hypervolume_value = hv.do(normalized_front)
        hypervolume_results[method] = hypervolume_value

        debug_print(f"[DEBUG] {method} hypervolume: {hypervolume_value:.6f}", print_debug)

    result_df = pd.DataFrame({
        "Exact Hypervolume": hypervolume_results
    }).T

    return result_df


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


def plot_3d_custom_objectives(method_paths, selected_objectives, instance_name=None):
    """
    Create 3D scatter plots of three selected objectives for each method.
    - X-axis: selected_objectives[0]
    - Y-axis: selected_objectives[1]
    - Z-axis: selected_objectives[2]
    """
    if len(selected_objectives) != 3:
        raise ValueError("Exactly three objectives must be selected for 3D plotting.")

    for method, path in method_paths.items():
        df = pd.read_csv(path)

        x = df[selected_objectives[0]]
        y = df[selected_objectives[1]]
        z = df[selected_objectives[2]]

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c='blue', marker='o')

        ax.set_xlabel(selected_objectives[0])
        ax.set_ylabel(selected_objectives[1])
        ax.set_zlabel(selected_objectives[2])

        title = f"{method} - Custom 3D Plot"
        if instance_name:
            title = f"{instance_name} - {method} Custom 3D"
        ax.set_title(title)

        plt.tight_layout()
        plt.show()



if __name__ == "__main__":
    np.random.seed(42)
    method_paths = get_methdod_paths(instance)

    # Calculate all metrics
    pci_result = calculate_pci(method_paths, print_debug=True)
    dci_result = calculate_dci(method_paths, print_debug=True)
    pf_share_result = calculate_pf_share(method_paths, print_debug=True)
    spread_result = calculate_spread(method_paths, print_debug=True)
    
    hypervolume_result_2 = calculate_hypervolume_monte_carlo(method_paths, print_interim_results=True)
    hypervolume_result_3 = calculate_average_monte_carlo_hypervolume(method_paths, print_debug=True)
    hypervolume_result_4 = calculate_hypervolume_hypercubes(method_paths, print_interim_results=True)
    hypervolume_result = calculate_exact_hypervolume(method_paths, print_debug=True)


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
    print("Instance:", instance)
    print("Methods:", ", ".join(method_paths.keys()), "\n")
    for idx, row in annotated_result.iterrows():
        print(f"{idx}")
        for method in annotated_result.columns:
            print(f"  {method.ljust(8)}: {str(row[method]).ljust(15)}")
        print()  # blank line after each metric


    # Plots of pareto fronts and chosen objectives
    plot_3d_custom_objectives(method_paths, ["Transport Machines", "Commute Distance", "Transport Attachments"], instance_name=instance)
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

""" === Interpretation of Clustering Results (PCI) ===

- When many solutions are grouped into large clusters, the PCI tends to be low (good).
- When solutions are grouped individually or into small clusters, the PCI is higher (bad).
- Many small clusters indicate weak dominance among solutions and thus a poorer approximation of the Pareto front.
- A single large cluster suggests that solutions are similar and strong regarding dominance relationships.

In practice:
- Low PCI: Solutions barely dominate each other but are collectively very close to the ideal front.
- High PCI: Solutions are scattered or poorly distributed in terms of dominance relationships.

Important:
- PCI should always be interpreted together with DCI (Diversity) and Hypervolume (Convergence).
"""