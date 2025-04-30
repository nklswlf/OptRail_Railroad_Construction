"""
=== Summary of Required Inputs ===

- Global merged Pareto front needed for:
    - PF-Share
    - DCI
    - PCI

- Individual method fronts needed for:
    - Hypervolume (Exact, Hypercubes, Monte Carlo)
    - Spread
    - Spacing

- Normalized fronts needed for:
    - Hypervolume (Exact, Hypercubes, Monte Carlo)
    - Spread
    - Spacing
    - PCI

=== Metrics and Their Interpretations ===

# PCI (Performance Comparison Indicator)
- Purpose: Measures how well the solutions from each method dominate the reference clusters constructed from the global Pareto front.
- Calculation: Based on dominance distances between method solutions and reference clusters.
- Interpretation:
    - Lower PCI values are better.
    - Indicates better convergence toward the ideal front.
    - Low PCI → Solutions are close and well-dominating.
    - High PCI → Solutions are scattered or weakly dominating.

# DCI (Diversity Comparison Indicator)
- Purpose: Measures how well the solutions are distributed across the objective space.
- Calculation: Based on contribution degrees over a discretized objective space grid.
- Interpretation:
    - Higher DCI values are better.
    - Indicates better diversity and distribution.
    - High DCI → Solutions are widespread and cover the space well.

# PF-Share (Pareto Front Share)
- Purpose: Measures the proportion of globally non-dominated solutions contributed by each method.
- Calculation: Share of solutions in the merged global Pareto front.
- Interpretation:
    - Higher PF-Share values are better.
    - Indicates that a method contributes more high-quality (non-dominated) solutions.

# Hypervolume
- Purpose: Measures the volume in objective space dominated by the solution set relative to a reference point.
- Calculation: Several methods:
    - Exact Hypervolume
    - Approximate Hypervolume via Hypercubes
    - Approximate Hypervolume via Monte Carlo Sampling
- Interpretation:
    - Higher Hypervolume values are better.
    - Combines convergence (closeness to ideal) and coverage (spread across objectives).

# Spacing
- Purpose: Measures the uniformity of distances between consecutive solutions along the front.
- Calculation: Based on the variance and mean of pairwise distances between consecutive sorted points.
- Interpretation:
    - Lower Spacing values are better.
    - Indicates more uniform distribution of solutions along the front.

# Spread
- Purpose: Measures the total extent (width) of the solutions across all objectives.
- Calculation: Sum of (max - min) range per objective.
- Interpretation:
    - Higher Spread values are better.
    - Indicates that the solution set covers a wider part of the objective space.

=== Categories of Metrics ===

# Diversity (distribution and spread of solutions)
- DCI (Diversity Comparison Indicator)
- Spacing

# Convergence (closeness to the ideal front)
- PCI (Performance Comparison Indicator)
- Hypervolume

# Contribution / Coverage (relative contribution of methods)
- PF-Share

=== Important Notes for PCI Clustering Interpretation ===

- Many large clusters → Low PCI (good dominance relationships).
- Many small clusters → High PCI (poor dominance relationships).
- Single large cluster → Strong mutual dominance and similarity.
- PCI should always be interpreted **together** with DCI and Hypervolume.
- A method could have a low PCI but poor DCI (good convergence but bad diversity).
"""


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
#instance = "a10_o107_m5_an57_ar12"
instance = "a10_o114_m6_an57_ar11"
#instance = "a10_o128_m6_an51_ar13"
#instance = "a10_o144_m6_an53_ar12"
#instance = "a15_o170_m9_an80_ar18"
#instance = "a20_o236_m12_an106_ar24"
#instance = "a25_o306_m13_an127_ar31"
#instance = "a30_o355_m18_an148_ar42"
#instance = "a40_o476_m22_an215_ar51"
#instance = "a50_o578_m28_an276_ar66"
#instance = "PCI_Change_Reference"

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

# === Debugging ===
def debug_print(msg, print_debug=False):
    if print_debug:
        print(msg)

# === Load function of ParetoFront.csv ===
def get_method_paths(instance_folder: str,excluded_methods=[], print_debug=False):
    # === Automatically find all methods based on subfolders containing ParetoFront.csv ===
    method_paths = {}
    single_pareto_fronts = {}
    all_solutions = []
    for root, dirs, files in os.walk(instance_folder):
        if "ParetoFront.csv" in files:
            method_name = os.path.basename(root)
            if method_name in excluded_methods:
                print(f"Skipping excluded method: {method_name}")
                continue
            path = os.path.join(root, "ParetoFront.csv")
            method_paths[method_name] = path
            # Load solutions and store them for duplicate analysis and single_pareto_fronts
            df = pd.read_csv(path)
            # Only keep the objectives columns for single_pareto_fronts
            if set(objectives).issubset(df.columns):
                single_pareto_fronts[method_name] = df[objectives].copy()
                all_solutions.append(df[objectives])
            else:
                print(f"⚠️  Warning: {method_name} ParetoFront.csv does not contain all objectives.")
                # Store the whole DataFrame if objectives are missing (for completeness)
                single_pareto_fronts[method_name] = df.copy()

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

    # === Build normalized DataFrames and global Pareto front ===
    # 1. Concatenate all objectives into a single DataFrame for normalization
    single_pareto_fronts_normalized = {}
    if all_solutions:
        all_obj_concat = pd.concat(all_solutions, ignore_index=True)
        # 2. Min-max normalization using global min/max
        min_point = all_obj_concat.min()
        max_point = all_obj_concat.max()
        ranges = max_point - min_point
        # Avoid division by zero
        ranges[ranges == 0] = 1
        # 3. Build normalized DataFrames for each method (only objectives columns)
        for method, df in single_pareto_fronts.items():
            # df is already only objectives columns (from above)
            if set(objectives).issubset(df.columns):
                df_norm_obj = (df[objectives] - min_point) / ranges
                df_norm_obj = df_norm_obj.clip(0, 1)
                single_pareto_fronts_normalized[method] = df_norm_obj.copy()
            else:
                single_pareto_fronts_normalized[method] = df.copy()
    else:
        single_pareto_fronts_normalized = {method: df.copy() for method, df in single_pareto_fronts.items()}

    # 4. Compute global Pareto front (non-dominated) from all combined original solutions
    global_pareto_front = None
    global_pareto_front_normalized = None
    global_pareto_front = None
    global_pareto_front_normalized = None
    if all_solutions:
        all_obj_concat_reset = all_obj_concat.reset_index(drop=True)
        data_values = all_obj_concat_reset.values
        def is_dominated(row, others):
            return np.any(np.all(others <= row, axis=1) & np.any(others < row, axis=1))
        pareto_rows = []
        for i, row in enumerate(data_values):
            if not is_dominated(row, np.delete(data_values, i, axis=0)):
                pareto_rows.append(i)
        global_pareto_front = all_obj_concat_reset.iloc[pareto_rows].reset_index(drop=True)
        # Compute normalized global Pareto front
        global_pareto_front_normalized = (global_pareto_front - min_point) / ranges
        global_pareto_front_normalized = global_pareto_front_normalized.clip(0, 1)
        global_pareto_front_normalized = global_pareto_front_normalized.reset_index(drop=True)
        # Merge global Pareto front with all method solutions to assign "Method" column
        all_method_solutions = []
        for method, df in single_pareto_fronts.items():
            df_obj = df[objectives].copy()
            df_obj["Method"] = method
            all_method_solutions.append(df_obj)
        all_data_concat = pd.concat(all_method_solutions, ignore_index=True)
        global_pareto_front = pd.merge(global_pareto_front, all_data_concat, on=objectives, how='left')
        # For normalized: merge with normalized method solutions
        all_method_solutions_norm = []
        for method, df in single_pareto_fronts_normalized.items():
            df_obj = df[objectives].copy()
            df_obj["Method"] = method
            all_method_solutions_norm.append(df_obj)
        all_data_concat_norm = pd.concat(all_method_solutions_norm, ignore_index=True)
        global_pareto_front_normalized = pd.merge(global_pareto_front_normalized, all_data_concat_norm, on=objectives, how='left')
    else:
        global_pareto_front = pd.DataFrame(columns=objectives)
        global_pareto_front_normalized = pd.DataFrame(columns=objectives)
        global_pareto_front = pd.DataFrame(columns=objectives + ["Method"])
        global_pareto_front_normalized = pd.DataFrame(columns=objectives + ["Method"])

    # Return all four results, plus the two "with_method" DataFrames for metrics
    # single_pareto_fronts: dict of DataFrames for each method (unnormalized)
    # single_pareto_fronts_normalized: dict of DataFrames for each method (normalized)
    # global_pareto_front: DataFrame of global Pareto front with "Method" column (unnormalized)
    # global_pareto_front_normalized: DataFrame of global Pareto front with "Method" column (normalized)
    
    print(f"\n=== Found {len(single_pareto_fronts)} methods ===")
    for method, df in single_pareto_fronts.items():
        print(f"Method: {method}, Solutions: {len(df)}")
    print(f"Global Pareto Front: {len(global_pareto_front)} solutions")

    debug_print("\n--- Single Pareto Fronts ---", print_debug)
    for method, df in single_pareto_fronts.items():
        debug_print(f"{method}: {df.shape}", print_debug)
        debug_print(df, print_debug)

    debug_print("\n--- Single Pareto Fronts Normalized ---", print_debug)
    for method, df in single_pareto_fronts_normalized.items():
        debug_print(f"{method}: {df.shape}", print_debug)
        debug_print(df, print_debug)

    debug_print("\n--- Global Pareto Front ---", print_debug)
    debug_print(global_pareto_front.shape, print_debug)
    debug_print(global_pareto_front, print_debug)
    debug_print("\n--- Global Pareto Front Normalized ---", print_debug)
    debug_print(global_pareto_front_normalized.shape, print_debug)
    debug_print(global_pareto_front_normalized, print_debug)




    return single_pareto_fronts, single_pareto_fronts_normalized, global_pareto_front, global_pareto_front_normalized


# === Metrics for Convergence and Coverage ===
def calculate_pf_share(global_pareto_front, print_debug=False):
    """
    Calculate the percentage share of each method's solutions in the global Pareto front.
    All results are returned as percentages (0–100, float).
    Returns a DataFrame with one row per method.
    NOTE: This function expects the global Pareto front with "Method" column.
    """

    debug_print("\n--- PF-Share Calculation Debug---", print_debug)

    pf_share_results = {}
    total_pareto = len(global_pareto_front)
    for method in global_pareto_front["Method"].unique():
        count = (global_pareto_front["Method"] == method).sum()
        pf_share_results[method] = (count / total_pareto) * 100 if total_pareto > 0 else 0.0
    result_df = pd.DataFrame({
        "PF-Share": pf_share_results
    }).T
    debug_print("\n--- PF-Share values per method ---", print_debug)
    debug_print(result_df, print_debug)
    return result_df

def calculate_pci(global_pareto_front_normalized, print_debug=False):
    """
    Calculate the PCI (Performance Comparison Indicator) using normalized data.
    - global_pareto_front_normalized: normalized global Pareto front with "Method" column
    """
    debug_print("\n--- PCI Calculation Debug (Normalized Data) ---", print_debug)
    S_df = global_pareto_front_normalized
    S_values = S_df[objectives].values
    methods = S_df["Method"].unique()
    debug_print(f"\n[DEBUG] Normalized global Pareto front merged with methods: {S_df.shape}", print_debug)
    debug_print(S_df.head(), print_debug)
    # === Clustering Step ===
    from scipy.special import factorial
    m = len(objectives)
    N = len(S_values)
    sigma = 1 / (((N * factorial(m - 1, exact=True)) ** (1 / (m - 1))) - (m / 2))
    debug_print(f"\n--- Calculated sigma threshold for clustering: {sigma:.6f}", print_debug)
    def dominance_distance(p, Q):
        if len(Q) == 0:
            return 0.0
        min_q = np.min(Q, axis=0)
        diffs = np.where(p > min_q, p - min_q, 0)
        return np.linalg.norm(diffs)
    pairs = []
    for i in range(N):
        for j in range(i + 1, N):
            d_ij = dominance_distance(S_values[i], S_values[j:j+1])
            d_ji = dominance_distance(S_values[j], S_values[i:i+1])
            dist = max(d_ij, d_ji)
            if dist <= sigma:
                pairs.append((dist, i, j))
    pairs.sort()
    debug_print(f"\n[DEBUG] Found {len(pairs)} valid pairs for clustering.", print_debug)
    parent = list(range(N))
    def find(u):
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u
    def union(u, v):
        pu, pv = find(u), find(v)
        if pu != pv:
            parent[pu] = pv
    for dist, i, j in pairs:
        union(i, j)

    clusters = {}
    for idx in range(N):
        root = find(idx)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(idx)
    cluster_points = [S_values[cluster_idxs] for cluster_idxs in clusters.values()]
    # --- Debug print for cluster composition ---
    if print_debug:
        print("\n--- Cluster Composition ---")
        for cluster_idx, cluster_idxs in enumerate(clusters.values()):
            methods_in_cluster = S_df.iloc[cluster_idxs]["Method"].value_counts()
            methods_summary = ", ".join([f"{method}: {count} solutions" for method, count in methods_in_cluster.items()])
            print(f"Cluster {cluster_idx}: {len(cluster_idxs)} solutions | {methods_summary}")
    debug_print(f"\n--- Number of clusters formed: {len(cluster_points)} ---", print_debug)
    pci_result = {}
    def dominance_distance_set(P, Q):
        total_distance = 0.0
        for q in Q:
            distances = []
            for p in P:
                diffs = np.where(p > q, p - q, 0)
                distances.append(np.linalg.norm(diffs))
            total_distance += min(distances)
        return total_distance
    for method in methods:
        X = S_df[S_df["Method"] == method][objectives].values
        pci_sum = 0.0
        for cluster_idx, cluster in enumerate(cluster_points):
            method_points_in_cluster = []
            for point in cluster:
                for idx, x in enumerate(X):
                    if np.allclose(x, point, atol=1e-8):
                        method_points_in_cluster.append(x)
            method_points_in_cluster = np.array(method_points_in_cluster)
            if len(method_points_in_cluster) < 2:
                min_dist = min(dominance_distance(x, cluster) for x in X) if len(X) > 0 else 0.0
                pci_sum += min_dist
                debug_print(f"[DEBUG] {method} cluster {cluster_idx} (len={len(cluster)}): <2 points, Point-to-set distance={min_dist:.6f}", print_debug)
            else:
                dset = dominance_distance_set(method_points_in_cluster, cluster)
                min_dist = min(dominance_distance(x, cluster) for x in X) if len(X) > 0 else 0.0
                pci_sum += min(dset, min_dist)
                if dset < min_dist:
                    debug_print(f"[DEBUG] {method} cluster {cluster_idx} (len={len(cluster)}): Set-to-set distance={dset:.6f} < Point-to-set distance={min_dist:.6f}", print_debug)
                else:
                    debug_print(f"[DEBUG] {method} cluster {cluster_idx} (len={len(cluster)}): Point-to-set distance={min_dist:.6f} < Set-to-set distance={dset:.6f}", print_debug)
        pci_result[method] = pci_sum / len(cluster_points) if len(cluster_points) > 0 else 0.0
    result_df = pd.DataFrame({
        "PCI": pci_result
    }).T
    debug_print("\n--- PCI values per method ---", print_debug)
    debug_print(result_df, print_debug)
    return result_df

def calculate_hypervolume_hypercubes(single_pareto_fronts=None, print_interim_results=False):
    """
    Calculate the normalized hypervolume for each method's Pareto front using min-max normalized objectives.
    Returns a DataFrame with one row per method.
    The hypervolume is computed after min-max normalizing all objectives to [0, 1] based on the global min and max.
    NOTE: This function expects normalized data to be passed directly.
    """
    # Helper: compute the hypervolume using shifted (1 - normalized) front, reference point at (1,...,1)
    def shifted_hypervolume(front):
        # Here, front is already normalized and shifted (1 - normalized)
        return np.sum(np.prod(front, axis=1))

    hypervolume_results = {}
    for method, df in single_pareto_fronts.items():
        front = df[objectives].to_numpy()
        shifted_front = 1 - front
        normalized_hv = np.sum(np.prod(shifted_front, axis=1))
        hypervolume_results[method] = normalized_hv

    result_df = pd.DataFrame({
        "Hypervolume": hypervolume_results
    }).T

    if print_interim_results:
        print("\n--- Hypervolume values per method hypercubes ---")
        print(result_df)

    return result_df

def calculate_hypervolume_monte_carlo(single_pareto_fronts_normalized=None, samples=100000, print_interim_results=False):
    """
    Approximate the normalized hypervolume for each method's Pareto front using Monte Carlo sampling.
    Returns a DataFrame with one row per method.
    NOTE: This function expects normalized data to be passed directly.
    """
    debug_print("\n--- Monte Carlo Hypervolume Calculation Debug ---", print_interim_results)

    hypervolume_results = {}
    sample_points_1 = None

    for method, df in single_pareto_fronts_normalized.items():
        front = df[objectives].to_numpy()
        # Generate random sample points in [0, 1]^n
        # sample_points = np.random.rand(samples, front.shape[1])
        # New Reference point for normalized data (1.01, 1.01, ..., 1.01)
        sample_points = np.random.uniform(0, 1.01, size=(samples, front.shape[1]))

        if sample_points_1 is not None:
            if sample_points.all() != sample_points_1.all():
                raise ValueError("Sample points are not equal to the previous sample points.")

        sample_points_1 = sample_points.copy()
    
        # Check if each sample point is dominated by at least one solution in the front
        dominated = np.any(np.all(front <= sample_points[:, None, :], axis=2), axis=1)

        # Hypervolume approximation: fraction of dominated samples
        hv_approx = np.mean(dominated)
        hypervolume_results[method] = hv_approx

        debug_print(f"[DEBUG] {method} approximated hypervolume (Monte Carlo, {samples} samples): {hv_approx:.6f}", print_interim_results)

    result_df = pd.DataFrame({
        "Hypevolume (Monte Carlo)": hypervolume_results
    }).T

    debug_print("\n--- Hypervolume (Monte Carlo) values per method ---", print_interim_results)
    debug_print(result_df, print_interim_results)

    return result_df

def calculate_average_monte_carlo_hypervolume(single_pareto_fronts_normalized, print_debug = False, seeds=[42, 43, 44, 45, 46], samples=100000):
    """
    Compute the average Monte Carlo hypervolume across multiple seeds.
    Only DataFrames are passed; method_paths are not used.
    NOTE: This function expects normalized data to be passed directly.
    """
    results = []
    for seed in seeds:
        np.random.seed(seed)
        hv_result = calculate_hypervolume_monte_carlo(single_pareto_fronts_normalized, samples=samples)
        results.append(hv_result.T)

    avg_result = pd.concat(results).groupby(level=0).mean().T
    
    debug_print("\n--- Average Monte Carlo Hypervolume values per method ---", print_debug)
    debug_print(avg_result, print_debug)

    return avg_result

def calculate_exact_hypervolume(single_pareto_fronts_normalized=None, print_debug=False):
    """
    Calculate the exact hypervolume for each method's Pareto front.
    NOTE: This function expects normalized data to be passed directly.
    """

    debug_print("\n--- Exact Hypervolume Calculation Debug ---", print_debug)

    hypervolume_results = {}
    for method, df in single_pareto_fronts_normalized.items():
        front = df[objectives].to_numpy()
        # Reference point for normalized data (all ones) --> New Reference point for normalized data (1.01, 1.01, ..., 1.01)
        ref_point = np.ones(front.shape[1]) * 1.01
        # Calculate Hypervolume
        hv = HV(ref_point)
        hypervolume_value = hv.do(front)
        hypervolume_results[method] = hypervolume_value
        debug_print(f"[DEBUG] {method} hypervolume: {hypervolume_value:.6f}", print_debug)

    result_df = pd.DataFrame({
        "Exact Hypervolume": hypervolume_results
    }).T

    return result_df



# === Metrics for Diversity and Distribution ===
def calculate_dci(global_pareto_front, print_debug=False):
    """
    Calculate the DCI (Diversity Comparison Indicator) for each method using the global Pareto front with "Method" column.
    Returns a DataFrame with one row per method.
    NOTE: This function expects the global Pareto front with "Method" column (unnormalized).
    """
    debug_print("\n--- DCI Calculation Debug---", print_debug)
    # Group by method
    methods = global_pareto_front["Method"].unique()
    pareto_groups = {}
    for method in methods:
        pareto_groups[method] = global_pareto_front[global_pareto_front["Method"] == method].reset_index(drop=True)
    # === 4. Ideal, Nadir, and Upper Bound based on global Pareto front ===
    div = 5
    ideal_point = global_pareto_front[objectives].min()
    nadir_point = global_pareto_front[objectives].max()
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
    def get_grid_index(row):
        return tuple(((row[valid_dims] - lower_bound[valid_dims]) / box_size[valid_dims]).astype(int))
    # Record occupied boxes
    grid_cells_by_method = {method: set() for method in methods}
    for method, df in pareto_groups.items():
        for _, row in df[objectives].iterrows():
            cell = get_grid_index(row)
            grid_cells_by_method[method].add(cell)
    all_cells = set().union(*grid_cells_by_method.values())
    from math import sqrt
    cd_matrix = {method: {} for method in methods}
    m = valid_dims.sum()  # effective dimensionality after exclusion
    # Precompute grid cells of all solutions per method
    grid_index_by_method = {
        method: [get_grid_index(row) for _, row in df[objectives].iterrows()]
        for method, df in pareto_groups.items()
    }
    for cell in all_cells:
        for method, grid_indices in grid_index_by_method.items():
            if grid_indices:
                distances = [np.linalg.norm(np.array(cell) - np.array(p_cell)) for p_cell in grid_indices]
                D = min(distances)
            else:
                D = float('inf')
            threshold = sqrt(m + 1)
            if D < threshold:
                CD = 1 - (D**2) / (m + 1)
                cd_matrix[method][cell] = CD
            else:
                cd_matrix[method][cell] = 0.0
    debug_print("\n--- Example Contribution Degrees ---", print_debug)
    for method, contributions in cd_matrix.items():
        non_zero = {k: v for k, v in contributions.items() if v > 0}
        debug_print(f"{method}: {list(non_zero.items())[:5]}", print_debug)
    dci_result = {}
    S = len(all_cells)
    for method in methods:
        contribution_sum = sum(cd_matrix[method].get(cell, 0.0) for cell in all_cells)
        dci_result[method] = contribution_sum / S if S > 0 else 0.0
    result_df = pd.DataFrame({
        "DCI": dci_result
    }).T
    debug_print("\n--- DCI values per method ---", print_debug)
    debug_print(result_df, print_debug)
    return result_df

def calculate_spread(single_pareto_fronts=None, print_debug=False):
    """
    Calculate the Spread (sum of width for each objective) for each method's Pareto front.
    Objectives are min-max normalized to [0, 1] before calculating the Spread.
    Spread = sum over objectives of (max value - min value).
    Returns a DataFrame with one row per method.
    NOTE: This function expects normalized data to be passed directly.
    """
    debug_print("\n--- Spread Calculation Debug (Normalized) ---", print_debug)

    spread_results = {}

    for method, df in single_pareto_fronts.items():
        front = df[objectives].to_numpy()
        # Print per-objective spread before summing
        for i, obj in enumerate(objectives):
            objective_spread = np.max(front[:, i]) - np.min(front[:, i])
            debug_print(f"[DEBUG] {method} spread for {obj}: {objective_spread:.6f}", print_debug)
        # Spread: sum over all objectives of (max - min) after normalization
        spread = np.mean(np.max(front, axis=0) - np.min(front, axis=0))
        spread_results[method] = spread
        debug_print(f"[DEBUG] {method} normalized spread: {spread:.6f}", print_debug)

    result_df = pd.DataFrame({
        "Spread": spread_results
    }).T

    debug_print("\n--- Spread values per method (Normalized) ---", print_debug)
    debug_print(result_df, print_debug)

    return result_df

def calculate_spacing(single_pareto_fronts_normalized=None, print_debug=False):
    """
    Calculate the spacing metric for each method's Pareto front.
    All objectives are min-max normalized to [0, 1] (using global min and max across all methods) before calculating the spacing.
    Returns a DataFrame with one row per method.
    NOTE: This function expects normalized data to be passed directly.
    """
    debug_print("\n--- Spacing Calculation Debug---", print_debug)

    def spacing(front):
        n = len(front)
        distances = []
        for i in range(n):
            dists = np.linalg.norm(front[i] - np.delete(front, i, axis=0), axis=1)
            di = np.min(dists)
            distances.append(di)
        distances = np.array(distances)
        mean_d = np.mean(distances)
        spacing_value = np.sqrt(np.sum((distances - mean_d) ** 2) / (n - 1))
        return spacing_value

    spacing_results = {}
    for method, df in single_pareto_fronts_normalized.items():
        front = df[objectives].to_numpy()
        spacing_results[method] = spacing(front)

    result_df = pd.DataFrame({
        "Spacing": spacing_results
    }).T

    debug_print("\n--- Spacing values per method ---", print_debug)
    debug_print(result_df, print_debug)

    return result_df

def calculate_distribution_metric(single_pareto_fronts_normalized=None, print_debug=False):
    """
    Calculate the Distribution Metric (DM) for each method's Pareto front according to the Wu and Azarm (2001) definition.
    Handles normalized [0,1] or unnormalized data.
    Returns a DataFrame with one row per method.
    """
    debug_print("\n--- Distribution Metric (DM) Calculation Debug (Updated) ---", print_debug)

    dm_results = {}

    for method, df in single_pareto_fronts_normalized.items():
        front = df[objectives].to_numpy()

        per_objective_dm = []
        for i, obj in enumerate(objectives):
            # Sort the front by the current objective
            sorted_values = np.sort(front[:, i])

            # Calculate distances between consecutive solutions
            gaps = np.diff(sorted_values)

            if len(gaps) == 0:
                mean_gap = 1e-10  # avoid division by zero
                std_gap = 0.0
            else:
                mean_gap = np.mean(gaps)
                std_gap = np.std(gaps, ddof=1)  # sample standard deviation (ddof=1)

            # Range R_h of objective
            R_h = np.max(sorted_values) - np.min(sorted_values)
            R_h = max(R_h, 1e-10)  # avoid division by zero

            # Assume objectives are normalized [0,1], but if not, the R_h will capture the real range

            # Calculate σ_h / μ_h
            if mean_gap > 0:
                sigma_over_mu = std_gap / mean_gap
            else:
                sigma_over_mu = 0.0

            # Normalization factor |f_h(P_G) - f_h(P_B)|:
            # Since we work normalized [0,1], |1-0|=1, otherwise approximate using R_h
            normalization_factor = 1.0  # because global normalization should ensure [0,1] spread
            term_h = (sigma_over_mu) / (R_h / normalization_factor)

            per_objective_dm.append(term_h)

            debug_print(f"[DEBUG] {method} objective {obj}: mean_gap={mean_gap:.6f}, std_gap={std_gap:.6f}, range={R_h:.6f}, term_h={term_h:.6f}", print_debug)

        # Sum terms over all objectives and divide by |S|
        if len(front) > 0:
            dm_value = (1 / len(front)) * np.sum(per_objective_dm)
        else:
            dm_value = np.nan

        dm_results[method] = dm_value

        debug_print(f"[DEBUG] {method} final DM value: {dm_value:.6f}", print_debug)

    result_df = pd.DataFrame({
        "Distribution Metric (DM)": dm_results
    }).T

    debug_print("\n--- DM values per method ---", print_debug)
    debug_print(result_df, print_debug)

    return result_df



# === Plotting Functions for single Pareto fronts ===
def plot_aggregated_3d(single_pareto_fronts_normalized, instance_name=None):
    """
    Create 3D scatter plots of the aggregated objectives for each method.
    - X-axis: Driver Violation
    - Y-axis: Sum of distance-based objectives (Commute Distance + Transport Machines + Transport Attachments)
    - Z-axis: Sum of resource-based objectives (Machines + Workers + Attachments)
    """
    for method, df in single_pareto_fronts_normalized.items():
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

def plot_3d_custom_objectives(single_pareto_fronts_normalized, selected_objectives, instance_name=None):
    """
    Create 3D scatter plots of three selected objectives for each method.
    - X-axis: selected_objectives[0]
    - Y-axis: selected_objectives[1]
    - Z-axis: selected_objectives[2]
    """
    if len(selected_objectives) != 3:
        raise ValueError("Exactly three objectives must be selected for 3D plotting.")

    for method, df in single_pareto_fronts_normalized.items():
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


# === Plotting Functions for combined plots but single Pareto fronts ===
def plot_aggregated_3d_combined(single_pareto_fronts_normalized, instance_name=None):
    """
    Erstellt einen kombinierten 3D-Scatterplot, in dem alle Punkte aller Methoden gemeinsam dargestellt werden.
    - X-Achse: Driver Violation
    - Y-Achse: Summe der Distanz-Objectives (Commute Distance + Transport Machines + Transport Attachments)
    - Z-Achse: Summe der Ressourcen-Objectives (Machines + Workers + Attachments)
    Jede Methode erhält eine eigene Farbe, und eine Legende wird hinzugefügt.
    """
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from itertools import cycle

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Farben je Methode
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_cycler = cycle(colors)
    method_to_color = {}
    for method in single_pareto_fronts_normalized.keys():
        method_to_color[method] = next(color_cycler)

    handles = []
    for method, df in single_pareto_fronts_normalized.items():
        x = df["Driver Violation"]
        y = df[["Commute Distance", "Transport Machines", "Transport Attachments"]].sum(axis=1)
        z = df[["Machines", "Workers", "Attachments"]].sum(axis=1)
        color = method_to_color[method]
        scatter = ax.scatter(x, y, z, c=color, marker='o', label=method, alpha=0.7)
        handles.append(scatter)

    ax.set_xlabel("Driver Violation")
    ax.set_ylabel("Total Distance")
    ax.set_zlabel("Total Resources")

    title = "Aggregated 3D Plot (All Methods)"
    if instance_name:
        title = f"{instance_name} - Aggregated 3D (All Methods)"
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()

def plot_aggregated_3d_combined_global(global_pareto_front_normalized, instance_name=None):
    """
    Create a combined 3D scatterplot for the global Pareto front (normalized), colored by Method.
    - X-axis: Driver Violation
    - Y-axis: Sum of distance-based objectives (Commute Distance + Transport Machines + Transport Attachments)
    - Z-axis: Sum of resource-based objectives (Machines + Workers + Attachments)
    Each method is shown with a different color and a legend is added.
    """
    import matplotlib.pyplot as plt
    from itertools import cycle
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    if "Method" not in global_pareto_front_normalized.columns:
        raise ValueError("global_pareto_front_normalized must include a 'Method' column")
    methods = global_pareto_front_normalized["Method"].unique()
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_cycler = cycle(colors)
    method_to_color = {method: next(color_cycler) for method in methods}
    handles = []
    for method in methods:
        df = global_pareto_front_normalized[global_pareto_front_normalized["Method"] == method]
        x = df["Driver Violation"]
        y = df[["Commute Distance", "Transport Machines", "Transport Attachments"]].sum(axis=1)
        z = df[["Machines", "Workers", "Attachments"]].sum(axis=1)
        color = method_to_color[method]
        scatter = ax.scatter(x, y, z, c=color, marker='o', label=method, alpha=0.7)
        handles.append(scatter)
    ax.set_xlabel("Driver Violation (normalized)")
    ax.set_ylabel("Total Distance (normalized)")
    ax.set_zlabel("Total Resources (normalized)")
    title = "Aggregated 3D Plot (Global Pareto Front, All Methods)"
    if instance_name:
        title = f"{instance_name} - Aggregated 3D (Global Pareto Front, All Methods)"
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()

# === Plotting Functions for combined plots with global Pareto front ===
def plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, selected_objectives, instance_name=None):
    """
    Create a combined 3D scatter plot of three selected objectives across all methods.
    - X-axis: selected_objectives[0]
    - Y-axis: selected_objectives[1]
    - Z-axis: selected_objectives[2]
    Each method is shown with a different color and a legend is added.
    """
    if len(selected_objectives) != 3:
        raise ValueError("Exactly three objectives must be selected for 3D plotting.")

    import matplotlib.pyplot as plt
    from itertools import cycle

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_cycler = cycle(colors)
    method_to_color = {}

    for method in single_pareto_fronts_normalized.keys():
        method_to_color[method] = next(color_cycler)

    handles = []
    for method, df in single_pareto_fronts_normalized.items():
        x = df[selected_objectives[0]]
        y = df[selected_objectives[1]]
        z = df[selected_objectives[2]]
        color = method_to_color[method]
        scatter = ax.scatter(x, y, z, c=color, marker='o', label=method, alpha=0.7)
        handles.append(scatter)

    ax.set_xlabel(selected_objectives[0])
    ax.set_ylabel(selected_objectives[1])
    ax.set_zlabel(selected_objectives[2])

    title = f"Combined 3D Plot ({', '.join(selected_objectives)})"
    if instance_name:
        title = f"{instance_name} - Combined 3D ({', '.join(selected_objectives)})"
    ax.set_title(title)

    ax.legend()
    plt.tight_layout()
    plt.show()

def plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, selected_objectives, instance_name=None):
    """
    Create a combined 3D scatter plot of three selected objectives across all methods for the global Pareto front (normalized).
    - X-axis: selected_objectives[0]
    - Y-axis: selected_objectives[1]
    - Z-axis: selected_objectives[2]
    Each method is shown with a different color and a legend is added.
    """
    if len(selected_objectives) != 3:
        raise ValueError("Exactly three objectives must be selected for 3D plotting.")
    import matplotlib.pyplot as plt
    from itertools import cycle
    if "Method" not in global_pareto_front_normalized.columns:
        raise ValueError("global_pareto_front_normalized must include a 'Method' column")
    methods = global_pareto_front_normalized["Method"].unique()
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_cycler = cycle(colors)
    method_to_color = {method: next(color_cycler) for method in methods}
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    handles = []
    for method in methods:
        df = global_pareto_front_normalized[global_pareto_front_normalized["Method"] == method]
        x = df[selected_objectives[0]]
        y = df[selected_objectives[1]]
        z = df[selected_objectives[2]]
        color = method_to_color[method]
        scatter = ax.scatter(x, y, z, c=color, marker='o', label=method, alpha=0.7)
        handles.append(scatter)
    ax.set_xlabel(f"{selected_objectives[0]} (normalized)")
    ax.set_ylabel(f"{selected_objectives[1]} (normalized)")
    ax.set_zlabel(f"{selected_objectives[2]} (normalized)")
    title = f"Combined 3D Plot (Global Pareto Front, {', '.join(selected_objectives)})"
    if instance_name:
        title = f"{instance_name} - Combined 3D (Global Pareto Front, {', '.join(selected_objectives)})"
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()



if __name__ == "__main__":
    np.random.seed(42)
    # Updated: Unpack all four returned values (now includes "with_method" DataFrames)
    single_pareto_fronts, single_pareto_fronts_normalized, global_pareto_front, global_pareto_front_normalized = get_method_paths(instance, excluded_methods = [], print_debug=False)

    # Insert check for number of methods in global Pareto front
    methods_in_global_pf = global_pareto_front["Method"].unique()
    calculate_pci_dci = len(methods_in_global_pf) > 1

    # Calculate all metrics with appropriate DataFrames
    # PCI and DCI only if more than one method in global Pareto front
    if calculate_pci_dci:
        pci_result = calculate_pci(global_pareto_front_normalized, print_debug=False)
        dci_result = calculate_dci(global_pareto_front, print_debug=False)
    else:
        print("⚠️  Skipping PCI and DCI: Only one method contributes to the global Pareto front.")
        pci_result = pd.DataFrame()
        dci_result = pd.DataFrame()
    # PF-Share expects unnormalized global Pareto front
    pf_share_result = calculate_pf_share(global_pareto_front, print_debug=False)
    # Spacing expects normalized single Pareto fronts
    spacing_results = calculate_spacing(single_pareto_fronts_normalized, print_debug=False)
    # Spread expects normalized single Pareto fronts
    spread_results = calculate_spread(single_pareto_fronts_normalized, print_debug=False)
    # Hypervolume (Monte Carlo average) expects normalized data
    hypervolume_results = calculate_average_monte_carlo_hypervolume(single_pareto_fronts_normalized, print_debug=False)
    # Distribution Metric (DM) expects normalized single Pareto fronts
    distribution_metric_results = calculate_distribution_metric(single_pareto_fronts_normalized, print_debug=False)

    #hypervolume_results_2 = calculate_hypervolume_monte_carlo(single_pareto_fronts_normalized, print_interim_results=True)
    #hypervolume_results_3 = calculate_hypervolume_hypercubes(single_pareto_fronts_normalized, print_interim_results=True)
    #hypervolume_result_4 = calculate_exact_hypervolume(single_pareto_fronts_normalized, print_debug=True)

    # Split metrics into convergence and diversity groups
    convergence_metrics = ["PF-Share", "PCI", "Hypervolume"]
    diversity_metrics = ["DCI", "Distribution Metric (DM)", "Spacing", "Spread"]

    # Create DataFrames for each group (preserving order), only include non-empty DataFrames
    convergence_result = pd.concat(
        [df for name, df in [("PF-Share", pf_share_result), ("PCI", pci_result), ("Hypervolume", hypervolume_results)] if not df.empty],
        axis=0
    )
    diversity_result = pd.concat(
        [df for name, df in [("DCI", dci_result), ("Distribution Metric (DM)", distribution_metric_results), ("Spacing", spacing_results), ("Spread", spread_results)] if not df.empty],
        axis=0
    )

    # Special formatting for convergence metrics
    formatted_convergence = convergence_result.copy()
    if "PF-Share" in formatted_convergence.index:
        pf_row = formatted_convergence.loc["PF-Share"]
        formatted_pf_row = pf_row.apply(
            lambda x: f"{int(round(x))}%" if pd.notna(x) else "0%"
        )
        formatted_convergence = formatted_convergence.astype(object)
        formatted_convergence.loc["PF-Share"] = formatted_pf_row
    formatted_convergence = formatted_convergence.astype(object)
    for idx in formatted_convergence.index:
        if idx != "PF-Share":
            formatted_convergence.loc[idx] = formatted_convergence.loc[idx].astype(float).round(4)

    # Special formatting for diversity metrics
    formatted_diversity = diversity_result.copy()
    formatted_diversity = formatted_diversity.astype(object)
    for idx in formatted_diversity.index:
        formatted_diversity.loc[idx] = formatted_diversity.loc[idx].astype(float).round(4)

    # Annotate convergence metrics (thumbs up/down)
    annotated_convergence = formatted_convergence.copy()
    for idx in formatted_convergence.index:
        if idx == "PF-Share":
            continue  # Skip annotations for PF-Share
        row = formatted_convergence.loc[idx]
        # Determine best/worst: for PCI, best is min; for others, best is max
        if idx in ["PCI"]:
            best_method = row.astype(float).idxmin()
            worst_method = row.astype(float).idxmax()
        else:
            best_method = row.astype(float).idxmax()
            worst_method = row.astype(float).idxmin()
        for col in formatted_convergence.columns:
            if col == best_method:
                annotated_convergence.at[idx, col] = f"{formatted_convergence.at[idx, col]} 👍"
            if col == worst_method:
                annotated_convergence.at[idx, col] = f"{formatted_convergence.at[idx, col]} 👎"

    # Annotate diversity metrics (thumbs up/down)
    annotated_diversity = formatted_diversity.copy()
    for idx in formatted_diversity.index:
        row = formatted_diversity.loc[idx]
        # For Spacing and Distribution Metric (DM), best is min; for others, best is max
        if idx in ["Spacing", "Distribution Metric (DM)"]:
            best_method = row.astype(float).idxmin()
            worst_method = row.astype(float).idxmax()
        else:
            best_method = row.astype(float).idxmax()
            worst_method = row.astype(float).idxmin()
        for col in formatted_diversity.columns:
            if col == best_method:
                annotated_diversity.at[idx, col] = f"{formatted_diversity.at[idx, col]} 👍"
            if col == worst_method:
                annotated_diversity.at[idx, col] = f"{formatted_diversity.at[idx, col]} 👎"

    print("\n=== Instance Information ===\n")
    print("Instance:", instance)
    print("Methods:", ", ".join(single_pareto_fronts.keys()), "\n")

    # Print final summary split into convergence and diversity metrics
    print("\n=== Convergence Metrics ===\n")
    for idx, row in annotated_convergence.iterrows():
        print(f"{idx}")
        for method in annotated_convergence.columns:
            print(f"  {method.ljust(8)}: {str(row[method]).ljust(15)}")
        print()  # blank line after each metric

    print("\n=== Diversity Metrics ===\n")  
    for idx, row in annotated_diversity.iterrows():
        print(f"{idx}")
        for method in annotated_diversity.columns:
            print(f"  {method.ljust(8)}: {str(row[method]).ljust(15)}")
        print()  # blank line after each metric

    # Plots of single Pareto fronts
    #plot_aggregated_3d(single_pareto_fronts_normalized, instance_name=instance)

    #plot_3d_custom_objectives(single_pareto_fronts_normalized, ["Transport Machines", "Commute Distance", "Transport Attachments"], instance_name=instance)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, [ "Machines", "Workers", "Attachments"], instance_name=instance)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, ["Driver Violation", "Workers", "Commute Distance"], instance_name=instance)ce)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, ["Driver Violation", "Machines", "Transport Machines"], instance_name=instance)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, ["Driver Violation", "Attachments", "Transport Attachments"], instance_name=instance)
    
    # Plots of combined Pareto fronts
    plot_aggregated_3d_combined(single_pareto_fronts_normalized, instance_name=instance)

    plot_aggregated_3d_combined_global(global_pareto_front_normalized, instance_name=instance)


    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Transport Machines", "Commute Distance", "Transport Attachments"], instance_name=instance)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Machines", "Workers", "Attachments"], instance_name=instance)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Driver Violation", "Workers", "Commute Distance"], instance_name=instance)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Driver Violation", "Machines", "Transport Machines"], instance_name=instance)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Driver Violation", "Attachments", "Transport Attachments"], instance_name=instance)


    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Transport Machines", "Commute Distance", "Transport Attachments"], instance_name=instance)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Machines", "Workers", "Attachments"], instance_name=instance)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Driver Violation", "Workers", "Commute Distance"], instance_name=instance)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Driver Violation", "Machines", "Transport Machines"], instance_name=instance)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Driver Violation", "Attachments", "Transport Attachments"], instance_name=instance)

















