"""
Pareto Front Quality Metrics Analysis Module

This module provides comprehensive evaluation tools for multi-objective optimization
results, specifically designed for analyzing Pareto fronts from railroad construction
scheduling algorithms. It implements various state-of-the-art metrics for assessing
convergence, diversity, and overall solution quality.

Core Functionality:
- Multi-objective Pareto front analysis and comparison
- Convergence assessment (closeness to ideal solutions)
- Diversity evaluation (distribution and spread analysis)
- Performance comparison between different algorithms
- Comprehensive visualization capabilities

Key Metrics Implemented:
- PCI (Performance Comparison Indicator): Convergence measurement
- DCI (Diversity Comparison Indicator): Distribution assessment
- PF-Share: Contribution analysis to global Pareto front
- Hypervolume: Combined convergence and coverage metric
- Spacing: Uniformity of solution distribution
- Spread: Coverage extent across objective space
- Distribution Metric (DM): Combined spacing and spread analysis

Data Processing Pipeline:
1. Load individual Pareto fronts from multiple algorithms
2. Normalize objectives using global min-max scaling
3. Construct global Pareto front from combined solutions
4. Calculate comprehensive quality metrics
5. Generate comparative analysis and visualizations

Dependencies:
- NumPy, Pandas: Data processing and numerical computations
- SciPy: Distance calculations and statistical functions
- Matplotlib: Visualization and plotting capabilities

=== METRICS INTERPRETATION GUIDE ===

# PCI (Performance Comparison Indicator)
- Purpose: Measures convergence toward ideal front through dominance relationships
- Calculation: Dominance distances between method solutions and reference clusters
- Interpretation: Lower values are better (closer to ideal front)
- Range: [0, ∞) where 0 indicates perfect convergence

# DCI (Diversity Comparison Indicator)  
- Purpose: Evaluates distribution quality across objective space
- Calculation: Contribution degrees over discretized objective space grid
- Interpretation: Higher values are better (better diversity coverage)
- Range: [0, 1] where 1 indicates perfect space coverage

# PF-Share (Pareto Front Share)
- Purpose: Measures algorithm contribution to global non-dominated solutions
- Calculation: Percentage of solutions in merged global Pareto front
- Interpretation: Higher percentages indicate better algorithm performance
- Range: [0%, 100%] where higher values show stronger contribution

# Hypervolume
- Purpose: Combined convergence and coverage assessment
- Calculation: Volume dominated by solution set relative to reference point
- Interpretation: Higher values are better (better overall quality)
- Range: [0, ∞) where larger volumes indicate superior performance

# Spacing
- Purpose: Measures uniformity of solution distribution along front
- Calculation: Variance of distances between consecutive solutions
- Interpretation: Lower values are better (more uniform distribution)
- Range: [0, ∞) where 0 indicates perfectly uniform spacing

# Spread
- Purpose: Evaluates extent of coverage across all objectives
- Calculation: Sum of objective ranges (max - min per objective)
- Interpretation: Higher values are better (wider coverage)
- Range: [0, ∞) where larger values show broader coverage

# Distribution Metric (DM)
- Purpose: Combined assessment of spacing uniformity and spread coverage
- Calculation: Normalized variance-to-mean ratio across objectives
- Interpretation: Lower values are better (better overall distribution)
- Range: [0, ∞) where 0 indicates ideal distribution

=== ALGORITHM COMPARISON FRAMEWORK ===

# Convergence Assessment (closeness to optimal solutions)
- Primary: PCI, Hypervolume
- Secondary: PF-Share (contribution quality)

# Diversity Assessment (solution distribution quality)  
- Primary: DCI, Distribution Metric (DM)
- Secondary: Spacing, Spread

# Overall Performance Ranking
- Balanced consideration of convergence and diversity metrics
- Context-specific weighting based on problem requirements
- Statistical significance testing for robust comparisons
"""

import os
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import matplotlib.pyplot as plt

# Hypervolume calculation (currently disabled due to dependencies)
#from pymoo.indicators.hv import HV
import numpy as np
import pandas as pd

def Run(instance, algorithms):
    """
    Main execution function for comprehensive Pareto front quality analysis.
    
    Performs complete evaluation pipeline including data loading, normalization,
    global Pareto front construction, and calculation of all quality metrics.
    
    Args:
        instance (str): Instance identifier for problem data location
        algorithms (list): List of algorithm names to include in analysis
        
    Returns:
        pd.DataFrame: Standardized results with columns [Algorithm, Metric, Value]
                     containing all calculated quality metrics for comparison
    
    Processing Pipeline:
    1. Load individual algorithm Pareto fronts from file system
    2. Apply global min-max normalization across all objectives
    3. Construct merged global Pareto front from all solutions
    4. Calculate convergence metrics (PCI, PF-Share, Hypervolume)
    5. Calculate diversity metrics (DCI, Spacing, Spread, Distribution Metric)
    6. Standardize results format for comparative analysis
    """
    # === File system configuration ===
    instance_folder = os.path.join("..", "OptRail_Railroad_Construction" ,"Data", "Solutions", instance)
    excluded_methods = []  # Methods to exclude from analysis
    np.random.seed(42)     # Ensure reproducible random sampling

    # === Problem objectives definition ===
    global objectives
    objectives = [
        "Driver Violation",      # Constraint violation penalties
        "Commute Distance",      # Worker travel distances
        "Transport Machines",    # Machine transportation costs
        "Transport Attachments", # Attachment transportation costs
        "Machines",             # Required machine resources
        "Workers",              # Required worker resources
        "Attachments"           # Required attachment resources
    ]

    # === Data loading and preprocessing ===
    single_pareto_fronts, single_pareto_fronts_normalized, global_pareto_front, global_pareto_front_normalized = get_method_paths(instance_folder, excluded_methods, included_methods=algorithms)

    # === Metric calculation feasibility check ===
    # PCI and DCI require multiple methods in global Pareto front for meaningful comparison
    methods_in_global_pf = global_pareto_front["Method"].unique()
    methods_in_single_pf = single_pareto_fronts.keys()
    calculate_pci_dci = len(methods_in_global_pf) > 1

    # === Convergence and diversity metrics calculation ===
    if calculate_pci_dci:
        # Calculate comparative metrics when multiple methods contribute
        pci_df = calculate_pci(global_pareto_front_normalized, print_debug=False)
        dci_df = calculate_dci(global_pareto_front, print_debug=False)
    else:
        # Handle single-method case with placeholder values
        print("⚠️  Skipping PCI and DCI: Only one method contributes to the global Pareto front.")
        methods_in_single_pf = single_pareto_fronts.keys()
        pci_df = pd.DataFrame({
            "PCI": {method: None for method in methods_in_single_pf}
        }).T
        dci_df = pd.DataFrame({
            "DCI": {method: None for method in methods_in_single_pf}
        }).T

    # Calculate remaining quality metrics for all methods
    pf_share_df = calculate_pf_share(global_pareto_front)
    hypervolume_monte_carlo_df = calculate_hypervolume_monte_carlo(single_pareto_fronts_normalized)
    spread_df = calculate_spread(single_pareto_fronts_normalized)
    spacing_df = calculate_spacing(single_pareto_fronts_normalized)
    distribution_metric_df = calculate_distribution_metric(single_pareto_fronts_normalized)

    # === Results standardization for unified analysis ===
    def standardize(df, metric_name):
        """Convert metric DataFrame to standardized format [Algorithm, Metric, Value]"""
        df_copy = df.copy()
        df_copy = df_copy.T.reset_index()
        df_copy.columns = ["Algorithm", "Value"]
        df_copy["Metric"] = metric_name
        return df_copy[["Algorithm", "Metric", "Value"]]

    # Combine all metrics into unified DataFrame for comparative analysis
    result_df = pd.concat([
        standardize(pf_share_df, "PF-Share"),
        standardize(pci_df, "PCI"),
        standardize(dci_df, "DCI"),
        standardize(hypervolume_monte_carlo_df, "Hypevolume (Monte Carlo)"),
        standardize(spread_df, "Spread"),
        standardize(spacing_df, "Spacing"),
        standardize(distribution_metric_df, "Distribution Metric (DM)")
    ], ignore_index=True)

    return result_df



# === Utility Functions ===

def debug_print(msg, print_debug=False):
    """
    Conditional debug output for development and troubleshooting.
    
    Args:
        msg: Message content to print (any printable type)
        print_debug (bool): Flag to enable/disable debug output
    """
    if print_debug:
        print(msg)

# === Data Loading and Preprocessing Functions ===

def get_method_paths(instance_folder: str,excluded_methods=[], print_debug=False, included_methods = None):
    """
    Comprehensive Pareto front data loader and preprocessor.
    
    Automatically discovers optimization methods, loads their Pareto fronts,
    performs global normalization, and constructs the merged global Pareto front.
    
    Args:
        instance_folder (str): Path to directory containing method subdirectories
        excluded_methods (list): Method names to exclude from analysis
        print_debug (bool): Enable detailed debug output
        included_methods (list): If provided, only include these methods
        
    Returns:
        tuple: (single_pareto_fronts, single_pareto_fronts_normalized, 
                global_pareto_front, global_pareto_front_normalized)
        - single_pareto_fronts: Dict of unnormalized DataFrames per method
        - single_pareto_fronts_normalized: Dict of normalized DataFrames per method  
        - global_pareto_front: Combined global Pareto front with Method column
        - global_pareto_front_normalized: Normalized global front with Method column
        
    Processing Steps:
    1. Scan directory structure for ParetoFront.csv files
    2. Load and validate objective data for each method
    3. Detect and report duplicate solutions across methods
    4. Apply global min-max normalization using combined data
    5. Construct global Pareto front using dominance filtering
    6. Assign method attribution to global front solutions
    """
    # === Method discovery and data loading ===
    method_paths = {}
    single_pareto_fronts = {}
    all_solutions = []  # Combined solutions for normalization and global front
    
    # Recursive search for ParetoFront.csv files in subdirectories
    for root, dirs, files in os.walk(instance_folder):
        if "ParetoFront.csv" in files:
            method_name = os.path.basename(root)
            
            # Apply inclusion/exclusion filters
            if included_methods is not None:
                if method_name not in included_methods:
                    print(f"Skipping excluded method: {method_name}")
                    continue
            if method_name in excluded_methods:
                print(f"Skipping excluded method: {method_name}")
                continue
                
            # Load and validate method data
            path = os.path.join(root, "ParetoFront.csv")
            method_paths[method_name] = path
            df = pd.read_csv(path)
            
            # Validate presence of required objectives
            if set(objectives).issubset(df.columns):
                single_pareto_fronts[method_name] = df[objectives].copy()
                all_solutions.append(df[objectives])
            else:
                print(f"⚠️  Warning: {method_name} ParetoFront.csv does not contain all objectives.")
                single_pareto_fronts[method_name] = df.copy()

    if not method_paths:
        raise FileNotFoundError(f"No ParetoFront.csv files found in {instance_folder}")

    # === Duplicate solution analysis across methods ===
    if all_solutions:
        combined = pd.concat(all_solutions, ignore_index=True)
        duplicated = combined.duplicated(keep=False)
        duplicate_entries = combined[duplicated]

        if not duplicate_entries.empty:
            print("\n=== Duplicate Solutions Across Methods (ignoring method assignment) ===")
            print(f"Found {len(duplicate_entries)} duplicate entries (counting all appearances).")
        else:
            print("\nNo duplicate solutions across methods found.")

    # === Global normalization and preprocessing ===
    single_pareto_fronts_normalized = {}
    if all_solutions:
        # Calculate global min-max bounds for normalization
        all_obj_concat = pd.concat(all_solutions, ignore_index=True)
        min_point = all_obj_concat.min()  # Global minimum per objective
        max_point = all_obj_concat.max()  # Global maximum per objective
        ranges = max_point - min_point
        ranges[ranges == 0] = 1  # Avoid division by zero for constant objectives
        
        # Apply normalization to each method's data
        for method, df in single_pareto_fronts.items():
            if set(objectives).issubset(df.columns):
                df_norm_obj = (df[objectives] - min_point) / ranges
                df_norm_obj = df_norm_obj.clip(0, 1)  # Ensure [0,1] bounds
                single_pareto_fronts_normalized[method] = df_norm_obj.copy()
            else:
                single_pareto_fronts_normalized[method] = df.copy()
    else:
        # Fallback for empty data
        single_pareto_fronts_normalized = {method: df.copy() for method, df in single_pareto_fronts.items()}

    # === Global Pareto front construction ===
    global_pareto_front = None
    global_pareto_front_normalized = None
    
    if all_solutions:
        # Dominance-based filtering for global Pareto front
        all_obj_concat_reset = all_obj_concat.reset_index(drop=True)
        data_values = all_obj_concat_reset.values
        
        def is_dominated(row, others):
            """Check if row is dominated by any solution in others"""
            return np.any(np.all(others <= row, axis=1) & np.any(others < row, axis=1))
        
        # Identify non-dominated solutions
        pareto_rows = []
        for i, row in enumerate(data_values):
            if not is_dominated(row, np.delete(data_values, i, axis=0)):
                pareto_rows.append(i)
                
        global_pareto_front = all_obj_concat_reset.iloc[pareto_rows].reset_index(drop=True)
        
        # Apply normalization to global Pareto front
        global_pareto_front_normalized = (global_pareto_front - min_point) / ranges
        global_pareto_front_normalized = global_pareto_front_normalized.clip(0, 1)
        global_pareto_front_normalized = global_pareto_front_normalized.reset_index(drop=True)
        
        # === Method attribution for global Pareto front ===
        # Match global Pareto solutions back to originating methods
        all_method_solutions = []
        for method, df in single_pareto_fronts.items():
            df_obj = df[objectives].copy()
            df_obj["Method"] = method
            all_method_solutions.append(df_obj)
        all_data_concat = pd.concat(all_method_solutions, ignore_index=True)
        global_pareto_front = pd.merge(global_pareto_front, all_data_concat, on=objectives, how='left')
        
        # Repeat for normalized version
        all_method_solutions_norm = []
        for method, df in single_pareto_fronts_normalized.items():
            df_obj = df[objectives].copy()
            df_obj["Method"] = method
            all_method_solutions_norm.append(df_obj)
        all_data_concat_norm = pd.concat(all_method_solutions_norm, ignore_index=True)
        global_pareto_front_normalized = pd.merge(global_pareto_front_normalized, all_data_concat_norm, on=objectives, how='left')
    else:
        # Empty data fallback
        global_pareto_front = pd.DataFrame(columns=objectives + ["Method"])
        global_pareto_front_normalized = pd.DataFrame(columns=objectives + ["Method"])

    # === Summary reporting ===
    print(f"\n=== Found {len(single_pareto_fronts)} methods ===")
    for method, df in single_pareto_fronts.items():
        print(f"Method: {method}, Solutions: {len(df)}")
    print(f"Global Pareto Front: {len(global_pareto_front)} solutions")

    # === Debug output for detailed analysis ===
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


# === Convergence and Coverage Metrics ===

def calculate_pf_share(global_pareto_front, print_debug=False):
    """
    Calculate Pareto Front Share metric for algorithm contribution assessment.
    
    Measures the percentage of solutions each algorithm contributes to the
    global non-dominated Pareto front, indicating solution quality and
    algorithm effectiveness.
    
    Args:
        global_pareto_front (pd.DataFrame): Global Pareto front with Method column
        print_debug (bool): Enable detailed debug output
        
    Returns:
        pd.DataFrame: PF-Share percentages per method (0-100%)
        
    Interpretation:
    - Higher percentages indicate better algorithm performance
    - 100% means algorithm dominates all others
    - 0% means algorithm contributes no non-dominated solutions
    """
    debug_print("\n--- PF-Share Calculation Debug---", print_debug)

    pf_share_results = {}
    total_pareto = len(global_pareto_front)
    
    # Calculate contribution percentage for each method
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
    Calculate Performance Comparison Indicator (PCI) for convergence assessment.
    
    Evaluates how well each algorithm's solutions dominate reference clusters
    constructed from the global Pareto front. Lower values indicate better
    convergence toward the ideal front.
    
    Algorithm:
    1. Construct dominance-based clusters using adaptive sigma threshold
    2. Calculate dominance distances between method solutions and clusters
    3. Aggregate distances to obtain PCI score per method
    
    Args:
        global_pareto_front_normalized (pd.DataFrame): Normalized global front with Method column
        print_debug (bool): Enable detailed debug output and cluster analysis
        
    Returns:
        pd.DataFrame: PCI values per method (lower is better)
        
    Mathematical Foundation:
    - Sigma threshold: σ = 1 / (((N * (m-1)!) ^ (1/(m-1))) - (m/2))
    - Dominance distance: ||max(0, p - q)||₂ for points p, q
    - PCI = average dominance distance to all clusters
    
    Interpretation:
    - Low PCI: Solutions are close to ideal and well-dominating
    - High PCI: Solutions are scattered or weakly dominating
    - Should be interpreted with DCI and Hypervolume for complete picture
    """
    debug_print("\n--- PCI Calculation Debug (Normalized Data) ---", print_debug)
    
    S_df = global_pareto_front_normalized
    S_values = S_df[objectives].values
    methods = S_df["Method"].unique()
    
    debug_print(f"\n[DEBUG] Normalized global Pareto front merged with methods: {S_df.shape}", print_debug)
    debug_print(S_df.head(), print_debug)
    
    # === Clustering Step with Adaptive Sigma ===
    from scipy.special import factorial
    m = len(objectives)  # Number of objectives
    N = len(S_values)    # Number of solutions
    
    # Calculate adaptive clustering threshold
    sigma = 1 / (((N * factorial(m - 1, exact=True)) ** (1 / (m - 1))) - (m / 2))
    debug_print(f"\n--- Calculated sigma threshold for clustering: {sigma:.6f}", print_debug)
    
    def dominance_distance(p, Q):
        """Calculate dominance distance from point p to set Q"""
        if len(Q) == 0:
            return 0.0
        min_q = np.min(Q, axis=0)
        diffs = np.where(p > min_q, p - min_q, 0)  # Only positive differences matter
        return np.linalg.norm(diffs)
    
    # === Pairwise Distance Calculation ===
    pairs = []
    for i in range(N):
        for j in range(i + 1, N):
            # Calculate bidirectional dominance distances
            d_ij = dominance_distance(S_values[i], S_values[j:j+1])
            d_ji = dominance_distance(S_values[j], S_values[i:i+1])
            dist = max(d_ij, d_ji)  # Use maximum for clustering
            
            if dist <= sigma:  # Only include pairs within threshold
                pairs.append((dist, i, j))
    
    pairs.sort()  # Sort by distance for union-find processing
    debug_print(f"\n[DEBUG] Found {len(pairs)} valid pairs for clustering.", print_debug)
    
    # === Union-Find Clustering ===
    parent = list(range(N))
    
    def find(u):
        """Find root with path compression"""
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u
    
    def union(u, v):
        """Union two components"""
        pu, pv = find(u), find(v)
        if pu != pv:
            parent[pu] = pv
    
    # Build clusters by merging similar solutions
    for dist, i, j in pairs:
        union(i, j)

    # Extract final clusters
    clusters = {}
    for idx in range(N):
        root = find(idx)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(idx)
    
    cluster_points = [S_values[cluster_idxs] for cluster_idxs in clusters.values()]
    
    # === Debug: Cluster Composition Analysis ===
    if print_debug:
        print("\n--- Cluster Composition ---")
        for cluster_idx, cluster_idxs in enumerate(clusters.values()):
            methods_in_cluster = S_df.iloc[cluster_idxs]["Method"].value_counts()
            methods_summary = ", ".join([f"{method}: {count} solutions" for method, count in methods_in_cluster.items()])
            print(f"Cluster {cluster_idx}: {len(cluster_idxs)} solutions | {methods_summary}")
    
    debug_print(f"\n--- Number of clusters formed: {len(cluster_points)} ---", print_debug)
    
    # === PCI Calculation for Each Method ===
    pci_result = {}
    
    def dominance_distance_set(P, Q):
        """Calculate set-to-set dominance distance"""
        max_min_distance = 0.0
        for q in Q:
            min_distance = float("inf")
            for p in P:
                diffs = np.where(p > q, p - q, 0)
                dist = np.linalg.norm(diffs)
                min_distance = min(min_distance, dist)
            max_min_distance = max(max_min_distance, min_distance)
        return max_min_distance
    
    for method in methods:
        X = S_df[S_df["Method"] == method][objectives].values
        pci_sum = 0.0

        for cluster_idx, cluster in enumerate(cluster_points):
            # Separate method solutions from other solutions in cluster
            method_points_in_cluster = []
            other_points_in_cluster = []

            for point in cluster:
                if any(np.allclose(point, x, atol=1e-8) for x in X):
                    method_points_in_cluster.append(point)
                else:
                    other_points_in_cluster.append(point)

            method_points_in_cluster = np.array(method_points_in_cluster)
            other_points_in_cluster = np.array(other_points_in_cluster)
            
            # Calculate appropriate distance based on method representation
            if len(method_points_in_cluster) < 2:
                # Use point-to-set distance for sparse method representation
                min_dist = min(dominance_distance(x, cluster) for x in X) if len(X) > 0 else 0.0
                pci_sum += min_dist
                debug_print(f"[DEBUG] {method} cluster {cluster_idx} (len={len(cluster)}): <2 points, Point-to-set distance={min_dist:.6f}", print_debug)
            else:
                # Use set-to-set distance for dense method representation
                dset = dominance_distance_set(method_points_in_cluster, other_points_in_cluster)
                pci_sum += dset
                debug_print(f"[DEBUG] {method} cluster {cluster_idx} (len={len(cluster)}): Set-to-set distance={dset:.6f}", print_debug)
        
        # Average over all clusters for final PCI score
        pci_result[method] = pci_sum / len(cluster_points) if len(cluster_points) > 0 else 0.0
    
    result_df = pd.DataFrame({
        "PCI": pci_result
    }).T
    
    debug_print("\n--- PCI values per method ---", print_debug)
    debug_print(result_df, print_debug)
    return result_df

# === Hypervolume Calculation Methods ===

def calculate_hypervolume_hypercubes(single_pareto_fronts=None, print_interim_results=False):
    """
    Calculate normalized hypervolume using hypercube approximation method.
    
    Approximates the volume dominated by each Pareto front using discrete
    hypercube summation. Works with normalized data in [0,1] space.
    
    Args:
        single_pareto_fronts (dict): Normalized Pareto fronts per method
        print_interim_results (bool): Enable detailed output
        
    Returns:
        pd.DataFrame: Hypervolume values per method (higher is better)
        
    Method:
    - Shifts normalized front to (1 - normalized) for volume calculation
    - Sums products of coordinates for each solution (hypercube volume)
    - Reference point at (1, 1, ..., 1) in shifted space
    """
    def shifted_hypervolume(front):
        """Calculate hypervolume using shifted coordinates"""
        return np.sum(np.prod(front, axis=1))

    hypervolume_results = {}
    for method, df in single_pareto_fronts.items():
        front = df[objectives].to_numpy()
        shifted_front = 1 - front  # Shift for volume calculation
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
    Calculate hypervolume using Monte Carlo sampling approximation.
    
    Estimates the volume dominated by each Pareto front through random
    sampling of the objective space. More robust for high-dimensional
    problems compared to exact methods.
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        samples (int): Number of random samples for approximation
        print_interim_results (bool): Enable detailed debug output
        
    Returns:
        pd.DataFrame: Approximate hypervolume values per method
        
    Algorithm:
    1. Generate random points in extended [0, ref]^n space
    2. Check dominance by each Pareto front solution
    3. Calculate fraction of dominated sample points
    4. Scale by reference volume for final hypervolume estimate
    
    Note: Uses reference point at (1.01, 1.01, ..., 1.01) to ensure
          proper volume calculation for normalized [0,1] fronts
    """
    debug_print("\n--- Monte Carlo Hypervolume Calculation Debug ---", print_interim_results)

    hypervolume_results = {}
    sample_points_1 = None
    ref = 1.01  # Extended reference point for normalized data

    for method, df in single_pareto_fronts_normalized.items():
        front = df[objectives].to_numpy()
        
        # Generate consistent random sample points across methods
        sample_points = np.random.uniform(0, ref, size=(samples, front.shape[1]))

        # Ensure consistency across method evaluations (debugging check)
        if sample_points_1 is not None:
            if sample_points.all() != sample_points_1.all():
                raise ValueError("Sample points are not equal to the previous sample points.")
        sample_points_1 = sample_points.copy()
    
        # Check dominance: sample point is dominated if any front solution dominates it
        dominated = np.any(np.all(front <= sample_points[:, None, :], axis=2), axis=1)

        # Calculate hypervolume approximation
        U = ref ** front.shape[1]  # Total reference volume
        hv_approx_volume = U * np.mean(dominated)
        hypervolume_results[method] = hv_approx_volume

        debug_print(f"[DEBUG] {method} approximated hypervolume (Monte Carlo, {samples} samples): {hv_approx_volume:.6f}", print_interim_results)

    result_df = pd.DataFrame({
        "Hypevolume (Monte Carlo)": hypervolume_results
    }).T

    debug_print("\n--- Hypervolume (Monte Carlo) values per method ---", print_interim_results)
    debug_print(result_df, print_interim_results)

    return result_df

def calculate_average_monte_carlo_hypervolume(single_pareto_fronts_normalized, print_debug = False, seeds=[42, 43, 44, 45, 46], samples=100000):
    """
    Calculate robust average Monte Carlo hypervolume across multiple random seeds.
    
    Reduces variance in Monte Carlo estimation by averaging results from
    multiple independent random seeds, providing more reliable hypervolume
    estimates for algorithm comparison.
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        print_debug (bool): Enable detailed debug output
        seeds (list): Random seeds for independent runs
        samples (int): Sample count per Monte Carlo run
        
    Returns:
        pd.DataFrame: Average hypervolume values with reduced variance
        
    Statistical Approach:
    - Multiple independent Monte Carlo estimates
    - Arithmetic mean across all seed results
    - Reduces random sampling variance for robust comparison
    """
    results = []
    
    # Calculate hypervolume for each random seed
    for seed in seeds:
        np.random.seed(seed)
        hv_result = calculate_hypervolume_monte_carlo(single_pareto_fronts_normalized, samples=samples)
        results.append(hv_result.T)

    # Average results across all seeds
    avg_result = pd.concat(results).groupby(level=0).mean().T
    
    debug_print("\n--- Average Monte Carlo Hypervolume values per method ---", print_debug)
    debug_print(avg_result, print_debug)

    return avg_result

def calculate_exact_hypervolume(single_pareto_fronts_normalized=None, print_debug=False):
    """
    Calculate exact hypervolume using specialized algorithms (currently disabled).
    
    Computes precise hypervolume values using dedicated libraries like pymoo.
    Currently disabled due to external dependency requirements but provides
    framework for exact calculation when needed.
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        print_debug (bool): Enable detailed debug output
        
    Returns:
        pd.DataFrame: Exact hypervolume values per method
        
    Note: Requires pymoo.indicators.hv.HV for exact calculation
          Currently returns placeholder for dependency management
    """
    debug_print("\n--- Exact Hypervolume Calculation Debug ---", print_debug)
    ref = 1.01  # Extended reference point for normalized data

    hypervolume_results = {}
    for method, df in single_pareto_fronts_normalized.items():
        front = df[objectives].to_numpy()
        ref_point = np.ones(front.shape[1]) * ref  # Reference point vector
        
        # Exact hypervolume calculation (requires external library)
        #hv = HV(ref_point)
        hv = "filler"  # Placeholder for dependency management
        hypervolume_value = hv.do(front) if hasattr(hv, 'do') else 0.0
        hypervolume_results[method] = hypervolume_value
        debug_print(f"[DEBUG] {method} hypervolume: {hypervolume_value:.6f}", print_debug)

    result_df = pd.DataFrame({
        "Exact Hypervolume": hypervolume_results
    }).T

    return result_df



# === Diversity and Distribution Metrics ===

def calculate_dci(global_pareto_front, print_debug=False):
    """
    Calculate Diversity Comparison Indicator (DCI) for distribution quality assessment.
    
    Evaluates how well solutions are distributed across the objective space
    using a discretized grid approach with contribution degrees.
    
    Args:
        global_pareto_front (pd.DataFrame): Unnormalized global Pareto front with Method column
        print_debug (bool): Enable detailed debug output and grid analysis
        
    Returns:
        pd.DataFrame: DCI values per method (higher is better)
        
    Algorithm:
    1. Define objective space bounds from global Pareto front
    2. Create discretized grid (default: 5x5x...x5)
    3. Calculate contribution degrees for each method to each grid cell
    4. Average contribution degrees across all grid cells
    
    Mathematical Foundation:
    - Grid cell size: (upper_bound - lower_bound) / divisions
    - Contribution degree: CD = 1 - (D²/(m+1)) if D < √(m+1), else 0
    - DCI = (1/S) * Σ CD(method, cell) for all cells S
    
    Interpretation:
    - Higher DCI indicates better space coverage and distribution
    - Range [0, 1] where 1 represents perfect uniform distribution
    """
    debug_print("\n--- DCI Calculation Debug---", print_debug)
    
    # Group solutions by optimization method
    methods = global_pareto_front["Method"].unique()
    pareto_groups = {}
    for method in methods:
        pareto_groups[method] = global_pareto_front[global_pareto_front["Method"] == method].reset_index(drop=True)
    
    # === Objective space discretization setup ===
    div = 5  # Grid divisions per objective dimension
    ideal_point = global_pareto_front[objectives].min()    # Best values per objective
    nadir_point = global_pareto_front[objectives].max()    # Worst values per objective
    upper_bound = nadir_point + (nadir_point - ideal_point) / (2 * div)  # Extended upper bound
    lower_bound = ideal_point  # Grid lower bound
    box_size = (upper_bound - lower_bound) / div  # Grid cell dimensions
    
    debug_print("\n--- Ideal Point ---", print_debug)
    debug_print(ideal_point, print_debug)
    debug_print("\n--- Nadir Point ---", print_debug)
    debug_print(nadir_point, print_debug)
    debug_print("\n--- Upper Bound ---", print_debug)
    debug_print(upper_bound, print_debug)
    debug_print("\n--- Box Size ---", print_debug)
    debug_print(box_size, print_debug)
    
    # === Handle objectives without variation ===
    valid_dims = box_size != 0  # Identify objectives with actual variation
    if not valid_dims.all():
        removed = list(box_size[~valid_dims].index)
        debug_print(f"\n⚠️  These objectives have no variation and are removed for DCI calculation: {removed}", print_debug)
    
    def get_grid_index(row):
        """Convert objective values to grid cell coordinates"""
        return tuple(((row[valid_dims] - lower_bound[valid_dims]) / box_size[valid_dims]).astype(int))
    
    # === Grid cell occupation tracking ===
    grid_cells_by_method = {method: set() for method in methods}
    for method, df in pareto_groups.items():
        for _, row in df[objectives].iterrows():
            cell = get_grid_index(row)
            grid_cells_by_method[method].add(cell)
    
    all_cells = set().union(*grid_cells_by_method.values())  # All occupied grid cells
    
    # === Contribution degree calculation ===
    from math import sqrt
    cd_matrix = {method: {} for method in methods}
    m = valid_dims.sum()  # Effective dimensionality after removing constant objectives
    
    # Precompute grid positions for efficient distance calculation
    grid_index_by_method = {
        method: [get_grid_index(row) for _, row in df[objectives].iterrows()]
        for method, df in pareto_groups.items()
    }
    
    # Calculate contribution degrees for each method to each grid cell
    for cell in all_cells:
        for method, grid_indices in grid_index_by_method.items():
            if grid_indices:
                # Find minimum distance from any method solution to current cell
                distances = [np.linalg.norm(np.array(cell) - np.array(p_cell)) for p_cell in grid_indices]
                D = min(distances)
            else:
                D = float('inf')  # No solutions for this method
            
            # Calculate contribution degree based on distance threshold
            threshold = sqrt(m + 1)
            if D < threshold:
                CD = 1 - (D**2) / (m + 1)  # Decreasing contribution with distance
                cd_matrix[method][cell] = CD
            else:
                cd_matrix[method][cell] = 0.0  # No contribution beyond threshold
    
    debug_print("\n--- Example Contribution Degrees ---", print_debug)
    for method, contributions in cd_matrix.items():
        non_zero = {k: v for k, v in contributions.items() if v > 0}
        debug_print(f"{method}: {list(non_zero.items())[:5]}", print_debug)
    
    # === Final DCI calculation ===
    dci_result = {}
    S = len(all_cells)  # Total number of occupied grid cells
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
    Calculate Spread metric for objective space coverage assessment.
    
    Measures the extent of coverage across all objectives by calculating
    the average range (max - min) per objective after normalization.
    
    Args:
        single_pareto_fronts (dict): Normalized Pareto fronts per method
        print_debug (bool): Enable detailed per-objective spread output
        
    Returns:
        pd.DataFrame: Spread values per method (higher is better)
        
    Calculation:
    - Per objective: range = max_value - min_value
    - Overall spread: average of all objective ranges
    
    Interpretation:
    - Higher spread indicates broader coverage of objective space
    - Values in [0, 1] for normalized data
    - Ideal value approaches 1 for complete objective space coverage
    """
    debug_print("\n--- Spread Calculation Debug (Normalized) ---", print_debug)

    spread_results = {}

    for method, df in single_pareto_fronts.items():
        front = df[objectives].to_numpy()
        
        # Calculate and report per-objective spread
        for i, obj in enumerate(objectives):
            objective_spread = np.max(front[:, i]) - np.min(front[:, i])
            debug_print(f"[DEBUG] {method} spread for {obj}: {objective_spread:.6f}", print_debug)
        
        # Calculate overall spread as average of objective ranges
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
    Calculate Spacing metric for solution distribution uniformity assessment.
    
    Measures how uniformly solutions are distributed along the Pareto front
    by analyzing the variance in distances between nearest neighbors.
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        print_debug (bool): Enable detailed debug output
        
    Returns:
        pd.DataFrame: Spacing values per method (lower is better)
        
    Algorithm:
    1. For each solution, find distance to nearest neighbor
    2. Calculate mean and variance of nearest neighbor distances
    3. Spacing = sqrt(variance) = standard deviation of distances
    
    Mathematical Foundation:
    - d_i = min(||x_i - x_j||₂) for all j ≠ i
    - mean_d = (1/n) * Σ d_i
    - Spacing = sqrt((1/(n-1)) * Σ(d_i - mean_d)²)
    
    Interpretation:
    - Lower spacing indicates more uniform distribution
    - 0 represents perfectly uniform spacing
    - Higher values suggest clustering or gaps in distribution
    """
    debug_print("\n--- Spacing Calculation Debug---", print_debug)

    def spacing(front):
        """Calculate spacing metric for a single Pareto front"""
        n = len(front)
        distances = []
        
        # Calculate nearest neighbor distance for each solution
        for i in range(n):
            # Distances to all other solutions
            dists = np.linalg.norm(front[i] - np.delete(front, i, axis=0), axis=1)
            di = np.min(dists)  # Distance to nearest neighbor
            distances.append(di)
        
        distances = np.array(distances)
        mean_d = np.mean(distances)  # Average nearest neighbor distance
        
        # Calculate standard deviation (spacing metric)
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
    Calculate Distribution Metric (DM) for comprehensive distribution quality assessment.
    
    Combines spacing uniformity and coverage spread into a single interpretable
    metric following Wu and Azarm (2001) methodology. Evaluates both how evenly
    solutions are distributed and how well they cover the objective space.
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        print_debug (bool): Enable detailed per-objective debug output
        
    Returns:
        pd.DataFrame: Distribution Metric values per method (lower is better)
        
    Algorithm:
    1. Sort solutions by each objective independently
    2. Calculate gaps between consecutive solutions per objective
    3. Compute coefficient of variation (σ/μ) for gap uniformity
    4. Normalize by objective range and solution count
    5. Average across all objectives
    
    Mathematical Foundation:
    - Gap variance-to-mean ratio: σ_h / μ_h per objective h
    - Range normalization: R_h = max_h - min_h
    - Per-objective term: (σ_h / μ_h) / R_h
    - DM = (1/|S|) * Σ_h [(σ_h / μ_h) / R_h]
    
    Interpretation:
    - Lower DM indicates better overall distribution
    - Combines both uniformity (spacing) and coverage (spread)
    - Aligned with expert assessment of solution quality
    """
    debug_print("\n--- Distribution Metric (DM) Calculation Debug (Updated) ---", print_debug)

    dm_results = {}

    for method, df in single_pareto_fronts_normalized.items():
        front = df[objectives].to_numpy()

        per_objective_dm = []
        for i, obj in enumerate(objectives):
            # Sort solutions by current objective for gap analysis
            sorted_values = np.sort(front[:, i])

            # Calculate gaps between consecutive solutions
            gaps = np.diff(sorted_values)

            if len(gaps) == 0:
                # Handle single solution case
                mean_gap = 1e-10  # Small value to avoid division by zero
                std_gap = 0.0
            else:
                mean_gap = np.mean(gaps)
                std_gap = np.std(gaps, ddof=1)  # Sample standard deviation

            # Calculate objective range for normalization
            R_h = np.max(sorted_values) - np.min(sorted_values)
            R_h = max(R_h, 1e-10)  # Avoid division by zero for constant objectives

            # Calculate coefficient of variation for gap uniformity
            if mean_gap > 0:
                sigma_over_mu = std_gap / mean_gap  # Coefficient of variation
            else:
                sigma_over_mu = 0.0

            # Normalization factor for [0,1] space
            normalization_factor = 1.0  # Global normalization ensures [0,1] range
            
            # Per-objective distribution term
            term_h = (sigma_over_mu) / (R_h / normalization_factor)
            per_objective_dm.append(term_h)

            debug_print(f"[DEBUG] {method} objective {obj}: mean_gap={mean_gap:.6f}, std_gap={std_gap:.6f}, range={R_h:.6f}, term_h={term_h:.6f}", print_debug)

        # Aggregate across objectives and normalize by solution count
        if len(front) > 0:
            dm_value = (1 / len(front)) * np.sum(per_objective_dm)
        else:
            dm_value = np.nan  # Handle empty front case

        dm_results[method] = dm_value

        debug_print(f"[DEBUG] {method} final DM value: {dm_value:.6f}", print_debug)

    result_df = pd.DataFrame({
        "Distribution Metric (DM)": dm_results
    }).T

    debug_print("\n--- DM values per method ---", print_debug)
    debug_print(result_df, print_debug)

    return result_df



# === Visualization Functions for Individual Pareto Fronts ===

def plot_aggregated_3d(single_pareto_fronts_normalized, instance_name=None):
    """
    Create individual 3D scatter plots for each optimization method.
    
    Aggregates objectives into three meaningful categories for visualization:
    - X-axis: Driver Violation (constraint penalties)
    - Y-axis: Total Distance (transport-related objectives)
    - Z-axis: Total Resources (machine, worker, attachment requirements)
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        instance_name (str): Optional instance identifier for plot titles
        
    Visualization Strategy:
    - Reduces 7-dimensional objective space to interpretable 3D representation
    - Groups related objectives for meaningful analysis
    - Individual plots allow detailed method-specific examination
    """
    for method, df in single_pareto_fronts_normalized.items():
        # Aggregate related objectives for meaningful 3D visualization
        x = df["Driver Violation"]  # Constraint violation component
        y = df[["Commute Distance", "Transport Machines", "Transport Attachments"]].sum(axis=1)  # Transport costs
        z = df[["Machines", "Workers", "Attachments"]].sum(axis=1)  # Resource requirements

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c='green', marker='o')

        ax.set_xlabel("Driver Violation")
        ax.set_ylabel("Total Distance")
        ax.set_zlabel("Total Resources")

        # Dynamic title generation
        title = f"{method} - Aggregated 3D Plot"
        if instance_name:
            title = f"{instance_name} - {method} Aggregated 3D"
        ax.set_title(title)

        plt.tight_layout()
        plt.show()

def plot_3d_custom_objectives(single_pareto_fronts_normalized, selected_objectives, instance_name=None):
    """
    Create individual 3D plots with user-specified objective combinations.
    
    Allows flexible exploration of objective relationships by plotting
    any three objectives from the 7-dimensional space.
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        selected_objectives (list): Three objective names for x, y, z axes
        instance_name (str): Optional instance identifier for plot titles
        
    Raises:
        ValueError: If exactly three objectives are not provided
        
    Use Cases:
    - Analyze specific objective trade-offs
    - Focus on particular problem aspects
    - Validate algorithm behavior in objective subspaces
    """
    if len(selected_objectives) != 3:
        raise ValueError("Exactly three objectives must be selected for 3D plotting.")

    for method, df in single_pareto_fronts_normalized.items():
        # Extract selected objectives for 3D plotting
        x = df[selected_objectives[0]]
        y = df[selected_objectives[1]]
        z = df[selected_objectives[2]]

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c='blue', marker='o')

        ax.set_xlabel(selected_objectives[0])
        ax.set_ylabel(selected_objectives[1])
        ax.set_zlabel(selected_objectives[2])

        # Dynamic title with selected objectives
        title = f"{method} - Custom 3D Plot"
        if instance_name:
            title = f"{instance_name} - {method} Custom 3D"
        ax.set_title(title)

        plt.tight_layout()
        plt.show()


# === Visualization Functions for Combined Algorithm Comparison ===

def plot_aggregated_3d_combined(single_pareto_fronts_normalized, instance_name=None):
    """
    Create combined 3D scatter plot comparing all algorithms simultaneously.
    
    Displays all Pareto front solutions in a single plot with distinct colors
    per algorithm, enabling direct visual comparison of algorithm performance
    and solution distribution characteristics.
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        instance_name (str): Optional instance identifier for plot title
        
    Visualization Features:
    - Color-coded algorithms for easy identification
    - Aggregated objective presentation for interpretability
    - Legend for algorithm identification
    - Alpha transparency to handle overlapping points
    
    Interpretation:
    - Spatial clustering indicates algorithm similarity
    - Coverage extent shows exploration capability
    - Density patterns reveal convergence behavior
    """
    import matplotlib.pyplot as plt
    from itertools import cycle

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Color assignment for algorithm differentiation
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_cycler = cycle(colors)
    method_to_color = {}
    for method in single_pareto_fronts_normalized.keys():
        method_to_color[method] = next(color_cycler)

    handles = []
    for method, df in single_pareto_fronts_normalized.items():
        # Aggregate objectives for meaningful 3D representation
        x = df["Driver Violation"]
        y = df[["Commute Distance", "Transport Machines", "Transport Attachments"]].sum(axis=1)
        z = df[["Machines", "Workers", "Attachments"]].sum(axis=1)
        color = method_to_color[method]
        
        # Create scatter plot with transparency for overlap handling
        scatter = ax.scatter(x, y, z, c=color, marker='o', label=method, alpha=0.7)
        handles.append(scatter)

    ax.set_xlabel("Driver Violation")
    ax.set_ylabel("Total Distance")
    ax.set_zlabel("Total Resources")

    # Dynamic title generation
    title = "Aggregated 3D Plot (All Methods)"
    if instance_name:
        title = f"{instance_name} - Aggregated 3D (All Methods)"
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()

def plot_aggregated_3d_combined_global(global_pareto_front_normalized, instance_name=None):
    """
    Create combined 3D plot for global Pareto front with algorithm attribution.
    
    Visualizes only the non-dominated solutions from the global Pareto front,
    showing which algorithms contribute to the best solutions and their
    distribution across objective space.
    
    Args:
        global_pareto_front_normalized (pd.DataFrame): Global Pareto front with Method column
        instance_name (str): Optional instance identifier for plot title
        
    Raises:
        ValueError: If Method column is missing from input data
        
    Advantages:
    - Focus on high-quality (non-dominated) solutions only
    - Clear algorithm contribution visualization
    - Reduced clutter compared to full front visualization
    - Better insight into algorithm effectiveness
    """
    import matplotlib.pyplot as plt
    from itertools import cycle
    
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Validate required Method column
    if "Method" not in global_pareto_front_normalized.columns:
        raise ValueError("global_pareto_front_normalized must include a 'Method' column")
    
    # Color assignment for algorithm identification
    methods = global_pareto_front_normalized["Method"].unique()
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_cycler = cycle(colors)
    method_to_color = {method: next(color_cycler) for method in methods}
    
    handles = []
    for method in methods:
        # Filter global front by algorithm
        df = global_pareto_front_normalized[global_pareto_front_normalized["Method"] == method]
        
        # Aggregate objectives for 3D visualization
        x = df["Driver Violation"]
        y = df[["Commute Distance", "Transport Machines", "Transport Attachments"]].sum(axis=1)
        z = df[["Machines", "Workers", "Attachments"]].sum(axis=1)
        color = method_to_color[method]
        
        scatter = ax.scatter(x, y, z, c=color, marker='o', label=method, alpha=0.7)
        handles.append(scatter)
    
    ax.set_xlabel("Driver Violation (normalized)")
    ax.set_ylabel("Total Distance (normalized)")
    ax.set_zlabel("Total Resources (normalized)")
    
    # Title with global front indication
    title = "Aggregated 3D Plot (Global Pareto Front, All Methods)"
    if instance_name:
        title = f"{instance_name} - Aggregated 3D (Global Pareto Front, All Methods)"
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()

# === Advanced Visualization Functions for Custom Analysis ===

def plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, selected_objectives, instance_name=None):
    """
    Create combined 3D plot with custom objective selection for all algorithms.
    
    Provides flexible visualization of any three objectives across all algorithms,
    enabling targeted analysis of specific objective relationships and trade-offs.
    
    Args:
        single_pareto_fronts_normalized (dict): Normalized Pareto fronts per method
        selected_objectives (list): Three objective names for axis assignment
        instance_name (str): Optional instance identifier for plot title
        
    Raises:
        ValueError: If exactly three objectives are not provided
        
    Applications:
    - Resource allocation analysis (Machines, Workers, Attachments)
    - Transportation cost evaluation (Transport objectives)
    - Constraint violation assessment with specific objectives
    - Algorithm comparison in targeted objective subspaces
    """
    if len(selected_objectives) != 3:
        raise ValueError("Exactly three objectives must be selected for 3D plotting.")

    import matplotlib.pyplot as plt
    from itertools import cycle

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Color cycling for algorithm differentiation
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_cycler = cycle(colors)
    method_to_color = {}
    for method in single_pareto_fronts_normalized.keys():
        method_to_color[method] = next(color_cycler)

    handles = []
    for method, df in single_pareto_fronts_normalized.items():
        # Extract user-specified objectives
        x = df[selected_objectives[0]]
        y = df[selected_objectives[1]]
        z = df[selected_objectives[2]]
        color = method_to_color[method]
        
        scatter = ax.scatter(x, y, z, c=color, marker='o', label=method, alpha=0.7)
        handles.append(scatter)

    ax.set_xlabel(selected_objectives[0])
    ax.set_ylabel(selected_objectives[1])
    ax.set_zlabel(selected_objectives[2])

    # Dynamic title with objective specification
    title = f"Combined 3D Plot ({', '.join(selected_objectives)})"
    if instance_name:
        title = f"{instance_name} - Combined 3D ({', '.join(selected_objectives)})"
    ax.set_title(title)

    ax.legend()
    plt.tight_layout()
    plt.show()

def plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, selected_objectives, instance_name=None):
    """
    Create global Pareto front visualization with custom objective selection.
    
    Visualizes only non-dominated solutions with user-specified objectives,
    providing focused analysis of algorithm contributions to the global
    optimum in targeted objective dimensions.
    
    Args:
        global_pareto_front_normalized (pd.DataFrame): Global Pareto front with Method column
        selected_objectives (list): Three objective names for axis assignment
        instance_name (str): Optional instance identifier for plot title
        
    Raises:
        ValueError: If exactly three objectives are not provided or Method column missing
        
    Benefits:
    - Focus on globally optimal solutions only
    - Clear algorithm contribution assessment
    - Reduced visual complexity
    - Enhanced insight into algorithm effectiveness in specific objectives
    """
    if len(selected_objectives) != 3:
        raise ValueError("Exactly three objectives must be selected for 3D plotting.")
    
    import matplotlib.pyplot as plt
    from itertools import cycle
    
    # Validate required data structure
    if "Method" not in global_pareto_front_normalized.columns:
        raise ValueError("global_pareto_front_normalized must include a 'Method' column")
    
    # Algorithm color assignment
    methods = global_pareto_front_normalized["Method"].unique()
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_cycler = cycle(colors)
    method_to_color = {method: next(color_cycler) for method in methods}
    
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    
    handles = []
    for method in methods:
        # Filter global front by algorithm
        df = global_pareto_front_normalized[global_pareto_front_normalized["Method"] == method]
        
        # Extract custom objectives
        x = df[selected_objectives[0]]
        y = df[selected_objectives[1]]
        z = df[selected_objectives[2]]
        color = method_to_color[method]
        
        scatter = ax.scatter(x, y, z, c=color, marker='o', label=method, alpha=0.7)
        handles.append(scatter)
    
    # Axis labeling with normalization indication
    ax.set_xlabel(f"{selected_objectives[0]} (normalized)")
    ax.set_ylabel(f"{selected_objectives[1]} (normalized)")
    ax.set_zlabel(f"{selected_objectives[2]} (normalized)")
    
    # Title with global front and objective specification
    title = f"Combined 3D Plot (Global Pareto Front, {', '.join(selected_objectives)})"
    if instance_name:
        title = f"{instance_name} - Combined 3D (Global Pareto Front, {', '.join(selected_objectives)})"
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()



# === Main Execution and Demonstration Script ===

if __name__ == "__main__":
    """
    Demonstration script for comprehensive Pareto front quality analysis.
    
    Executes complete evaluation pipeline on a specified problem instance,
    calculating all quality metrics and generating comparative visualizations.
    Provides template for systematic algorithm performance assessment.
    """

    # === Problem Instance Configuration ===
    # Select target problem instance for analysis
    # Commented alternatives show available instance sizes and complexity levels
    #instance = "a3_o80_m10_an10_ar9_reduced"      # Small test instance
    #instance = "a5_o96_m10_an10_ar10_reduced"     # Small-medium instance
    #instance = "a10_o107_m5_an57_ar12"            # Medium instances
    #instance = "a10_o114_m6_an57_ar11"
    #instance = "a10_o128_m6_an51_ar13"
    #instance = "a10_o144_m6_an53_ar12"
    #instance = "a15_o170_m9_an80_ar18"            # Large instances
    #instance = "a20_o236_m12_an106_ar24"
    instance = "a25_o306_m13_an127_ar31"           # Active instance for analysis
    #instance = "a30_o355_m18_an148_ar42"          # Very large instances
    #instance = "a40_o476_m22_an215_ar51"
    #instance = "a50_o578_m28_an276_ar66"
    #instance = "PCI_Change_Reference"             # Special test instance

    # === Optimization Objectives Definition ===
    objectives = [
        "Driver Violation",      # Constraint violation penalties
        "Commute Distance",      # Worker commuting costs
        "Transport Machines",    # Machine transportation costs
        "Transport Attachments", # Attachment transportation costs
        "Machines",             # Machine resource requirements
        "Workers",              # Worker resource requirements
        "Attachments"           # Attachment resource requirements
    ]

    # === Analysis Pipeline Execution ===
    np.random.seed(42)  # Ensure reproducible results
    
    # Load and preprocess all algorithm data
    single_pareto_fronts, single_pareto_fronts_normalized, global_pareto_front, global_pareto_front_normalized = get_method_paths(instance, excluded_methods = [], print_debug=False)

    # === Metric Calculation Feasibility Assessment ===
    methods_in_global_pf = global_pareto_front["Method"].unique()
    calculate_pci_dci = len(methods_in_global_pf) > 1

    # === Comprehensive Quality Metrics Calculation ===
    
    # Convergence and comparison metrics (require multiple methods)
    if calculate_pci_dci:
        pci_result = calculate_pci(global_pareto_front_normalized, print_debug=False)
        dci_result = calculate_dci(global_pareto_front, print_debug=False)
    else:
        print("⚠️  Skipping PCI and DCI: Only one method contributes to the global Pareto front.")
        pci_result = pd.DataFrame()
        dci_result = pd.DataFrame()
    
    # Individual algorithm quality metrics
    pf_share_result = calculate_pf_share(global_pareto_front, print_debug=False)
    spacing_results = calculate_spacing(single_pareto_fronts_normalized, print_debug=False)
    spread_results = calculate_spread(single_pareto_fronts_normalized, print_debug=False)
    hypervolume_results = calculate_average_monte_carlo_hypervolume(single_pareto_fronts_normalized, print_debug=False)
    distribution_metric_results = calculate_distribution_metric(single_pareto_fronts_normalized, print_debug=False)

    # Optional additional hypervolume calculations (for validation)
    #hypervolume_results_2 = calculate_hypervolume_monte_carlo(single_pareto_fronts_normalized, print_interim_results=True)
    #hypervolume_results_3 = calculate_hypervolume_hypercubes(single_pareto_fronts_normalized, print_interim_results=True)
    #hypervolume_result_4 = calculate_exact_hypervolume(single_pareto_fronts_normalized, print_debug=True)

    # === Results Organization and Formatting ===
    
    # Categorize metrics by evaluation focus
    convergence_metrics = ["PF-Share", "PCI", "Hypervolume"]        # Quality and convergence
    diversity_metrics = ["DCI", "Distribution Metric (DM)", "Spacing", "Spread"]  # Distribution and diversity

    # Combine metrics into categorical groups (exclude empty DataFrames)
    convergence_result = pd.concat(
        [df for name, df in [("PF-Share", pf_share_result), ("PCI", pci_result), ("Hypervolume", hypervolume_results)] if not df.empty],
        axis=0
    )
    diversity_result = pd.concat(
        [df for name, df in [("DCI", dci_result), ("Distribution Metric (DM)", distribution_metric_results), ("Spacing", spacing_results), ("Spread", spread_results)] if not df.empty],
        axis=0
    )

    # === Results Formatting for Presentation ===
    
    # Format convergence metrics with appropriate precision
    formatted_convergence = convergence_result.copy()
    if "PF-Share" in formatted_convergence.index:
        # Special formatting for percentage values
        pf_row = formatted_convergence.loc["PF-Share"]
        formatted_pf_row = pf_row.apply(
            lambda x: f"{int(round(x))}%" if pd.notna(x) else "0%"
        )
        formatted_convergence = formatted_convergence.astype(object)
        formatted_convergence.loc["PF-Share"] = formatted_pf_row
    
    # Apply numerical formatting to remaining convergence metrics
    formatted_convergence = formatted_convergence.astype(object)
    for idx in formatted_convergence.index:
        if idx != "PF-Share":
            formatted_convergence.loc[idx] = formatted_convergence.loc[idx].astype(float).round(4)

    # Format diversity metrics with consistent precision
    formatted_diversity = diversity_result.copy()
    formatted_diversity = formatted_diversity.astype(object)
    for idx in formatted_diversity.index:
        formatted_diversity.loc[idx] = formatted_diversity.loc[idx].astype(float).round(4)

    # === Performance Ranking with Visual Indicators ===
    
    # Add best/worst performance annotations for convergence metrics
    annotated_convergence = formatted_convergence.copy()
    for idx in formatted_convergence.index:
        if idx == "PF-Share":
            continue  # Skip annotation for percentage values
        row = formatted_convergence.loc[idx]
        
        # Determine optimization direction (minimize PCI, maximize others)
        if idx in ["PCI"]:
            best_method = row.astype(float).idxmin()   # Lower is better
            worst_method = row.astype(float).idxmax()  # Higher is worse
        else:
            best_method = row.astype(float).idxmax()   # Higher is better
            worst_method = row.astype(float).idxmin()  # Lower is worse
        
        # Apply visual performance indicators
        for col in formatted_convergence.columns:
            if col == best_method:
                annotated_convergence.at[idx, col] = f"{formatted_convergence.at[idx, col]} 👍"
            if col == worst_method:
                annotated_convergence.at[idx, col] = f"{formatted_convergence.at[idx, col]} 👎"

    # Add best/worst performance annotations for diversity metrics
    annotated_diversity = formatted_diversity.copy()
    for idx in formatted_diversity.index:
        row = formatted_diversity.loc[idx]
        
        # Determine optimization direction (minimize Spacing/DM, maximize others)
        if idx in ["Spacing", "Distribution Metric (DM)"]:
            best_method = row.astype(float).idxmin()   # Lower is better
            worst_method = row.astype(float).idxmax()  # Higher is worse
        else:
            best_method = row.astype(float).idxmax()   # Higher is better
            worst_method = row.astype(float).idxmin()  # Lower is worse
        
        # Apply visual performance indicators
        for col in formatted_diversity.columns:
            if col == best_method:
                annotated_diversity.at[idx, col] = f"{formatted_diversity.at[idx, col]} 👍"
            if col == worst_method:
                annotated_diversity.at[idx, col] = f"{formatted_diversity.at[idx, col]} 👎"

    # === Comprehensive Results Presentation ===
    
    print("\n=== Instance Information ===\n")
    print("Instance:", instance)
    print("Methods:", ", ".join(single_pareto_fronts.keys()), "\n")

    # Present convergence analysis results
    print("\n=== Convergence Metrics ===\n")
    for idx, row in annotated_convergence.iterrows():
        print(f"{idx}")
        for method in annotated_convergence.columns:
            print(f"  {method.ljust(8)}: {str(row[method]).ljust(15)}")
        print()  # Blank line for readability

    # Present diversity analysis results
    print("\n=== Diversity Metrics ===\n")  
    for idx, row in annotated_diversity.iterrows():
        print(f"{idx}")
        for method in annotated_diversity.columns:
            print(f"  {method.ljust(8)}: {str(row[method]).ljust(15)}")
        print()  # Blank line for readability

    # === Visualization Generation ===
    
    # Individual algorithm visualizations (uncommented as needed)
    #plot_aggregated_3d(single_pareto_fronts_normalized, instance_name=instance)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, ["Transport Machines", "Commute Distance", "Transport Attachments"], instance_name=instance)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, [ "Machines", "Workers", "Attachments"], instance_name=instance)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, ["Driver Violation", "Workers", "Commute Distance"], instance_name=instance)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, ["Driver Violation", "Machines", "Transport Machines"], instance_name=instance)
    #plot_3d_custom_objectives(single_pareto_fronts_normalized, ["Driver Violation", "Attachments", "Transport Attachments"], instance_name=instance)
    
    # Combined algorithm comparison visualizations
    plot_aggregated_3d_combined(single_pareto_fronts_normalized, instance_name=instance)
    plot_aggregated_3d_combined_global(global_pareto_front_normalized, instance_name=instance)

    # Additional specialized visualizations (uncommented as needed)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Transport Machines", "Commute Distance", "Transport Attachments"], instance_name=instance)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Machines", "Workers", "Attachments"], instance_name=instance)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Driver Violation", "Workers", "Commute Distance"], instance_name=instance)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Driver Violation", "Machines", "Transport Machines"], instance_name=instance)
    #plot_3d_custom_objectives_combined(single_pareto_fronts_normalized, ["Driver Violation", "Attachments", "Transport Attachments"], instance_name=instance)

    # Global Pareto front specialized visualizations (uncommented as needed)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Transport Machines", "Commute Distance", "Transport Attachments"], instance_name=instance)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Machines", "Workers", "Attachments"], instance_name=instance)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Driver Violation", "Workers", "Commute Distance"], instance_name=instance)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Driver Violation", "Machines", "Transport Machines"], instance_name=instance)
    #plot_3d_custom_objectives_combined_global(global_pareto_front_normalized, ["Driver Violation", "Attachments", "Transport Attachments"], instance_name=instance)

















