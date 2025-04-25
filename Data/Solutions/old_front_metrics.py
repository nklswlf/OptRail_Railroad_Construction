import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
from scipy.spatial import distance

def dominates(a, b):
    return np.all(a <= b) and np.any(a < b)

def coverage_metric(front_a, front_b):
    return sum(any(dominates(a, b) for a in front_a) for b in front_b) / len(front_b)

def epsilon_indicator(front_a, front_b):
    eps_values = []
    for b in front_b:
        eps_b = float('inf')
        for a in front_a:
            eps = max(a_i - b_i for a_i, b_i in zip(a, b))
            eps_b = min(eps_b, eps)
        eps_values.append(eps_b)
    return max(eps_values)

def spread(front):
    front_sorted = front[np.argsort(front[:, 0])]
    distances = [np.linalg.norm(front_sorted[i + 1] - front_sorted[i]) for i in range(len(front_sorted) - 1)]
    return np.std(distances) / np.mean(distances) if np.mean(distances) > 0 else 0

def hypervolume(front, reference_point):
    dominated = np.maximum(reference_point - front, 0)
    return np.sum(np.prod(dominated, axis=1))

def plot_aggregated_3d(df, title):
    x = df['Driver Violation']
    y = df[['Commute Distance', 'Transport Machines', 'Transport Attachments']].sum(axis=1)
    z = df[['Machines', 'Workers', 'Attachments']].sum(axis=1)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x, y, z, c='green', marker='o')
    ax.set_xlabel('Driver Violation')
    ax.set_ylabel('Total Distance')
    ax.set_zlabel('Total Resources')
    ax.set_title(title)
    plt.tight_layout()
    plt.show()

def load_pareto_file(base_path, method):
    file_path = next(Path(base_path).rglob(f"{method}/ParetoFront.csv"), None)
    if file_path is None:
        raise FileNotFoundError(f"ParetoFront.csv not found for method {method} in {base_path}")
    return pd.read_csv(file_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python front_metrics.py <instance_name>")
        sys.exit(1)

    instance = sys.argv[1]
    base_dir = Path(__file__).resolve().parents[0]
    matches = [p for p in base_dir.rglob(f"{instance}") if p.is_dir()]
    if not matches:
        print(f"Instance folder not found for: {instance}")
        sys.exit(1)
    instance_path = matches[0]

    columns = ['Driver Violation', 'Commute Distance', 'Transport Machines',
               'Transport Attachments', 'Machines', 'Workers', 'Attachments']

    df_psa = load_pareto_file(instance_path, "PSA")
    df_dbsa = load_pareto_file(instance_path, "DBSA")
    df_tpsa = load_pareto_file(instance_path, "TPSA")

    front_psa = df_psa[columns].to_numpy()
    front_dbsa = df_dbsa[columns].to_numpy()
    front_tpsa = df_tpsa[columns].to_numpy()

    print("=== Coverage Metrics ===")
    print(f"Coverage C(PSA,DBSA): {coverage_metric(front_psa, front_dbsa):.3f}")
    print(f"Coverage C(DBSA,PSA): {coverage_metric(front_dbsa, front_psa):.3f}")
    print(f"Coverage C(PSA,TPSA): {coverage_metric(front_psa, front_tpsa):.3f}")
    print(f"Coverage C(TPSA,PSA): {coverage_metric(front_tpsa, front_psa):.3f}")
    print(f"Coverage C(DBSA,TPSA): {coverage_metric(front_dbsa, front_tpsa):.3f}")
    print(f"Coverage C(TPSA,DBSA): {coverage_metric(front_tpsa, front_dbsa):.3f}")

    print("\n=== Epsilon Indicators ===")
    print(f"Epsilon E(PSA,DBSA): {epsilon_indicator(front_psa, front_dbsa):.3f}")
    print(f"Epsilon E(DBSA,PSA): {epsilon_indicator(front_dbsa, front_psa):.3f}")
    print(f"Epsilon E(PSA,TPSA): {epsilon_indicator(front_psa, front_tpsa):.3f}")
    print(f"Epsilon E(TPSA,PSA): {epsilon_indicator(front_tpsa, front_psa):.3f}")
    print(f"Epsilon E(DBSA,TPSA): {epsilon_indicator(front_dbsa, front_tpsa):.3f}")
    print(f"Epsilon E(TPSA,DBSA): {epsilon_indicator(front_tpsa, front_dbsa):.3f}")

    print("\n=== Single Best Values ===")
    sbv_psa = df_psa[columns].min()
    sbv_dbsa = df_dbsa[columns].min()
    sbv_tpsa = df_tpsa[columns].min()

    print(f"{'Metric':20} {'PSA (min)':>12} {'DBSA (min)':>12} {'TPSA (min)':>12}")
    for col in columns:
        print(f"{col:20} {sbv_psa[col]:12.3f} {sbv_dbsa[col]:12.3f} {sbv_tpsa[col]:12.3f}")

    print("\n=== Hypervolume and Spread ===")
    all_data = pd.concat([df_psa, df_dbsa, df_tpsa])
    min_point = all_data[columns].min().to_numpy()
    reference_point = all_data[columns].max().to_numpy() + 1
    volume_box = reference_point - min_point
    max_volume = np.prod(volume_box)

    def shifted_hypervolume(front, min_point, reference_point):
        shifted = np.clip(reference_point - front, 0, None)
        return np.sum(np.prod(shifted, axis=1))

    for name, front in [("PSA", front_psa), ("DBSA", front_dbsa), ("TPSA", front_tpsa)]:
        shifted_front = front - min_point
        volume_box = reference_point - min_point
        max_volume = np.prod(volume_box)

        hv = shifted_hypervolume(shifted_front, min_point, reference_point)
        normalized_hv = hv / max_volume

        sp = spread(front)
        print(f"{name}:")
        print(f"  Hypervolume: {normalized_hv:.4f}")
        print(f"  Spread: {sp:.4f}")

    plot_aggregated_3d(df_psa, "Pareto Front PSA - Aggregated")
    plot_aggregated_3d(df_dbsa, "Pareto Front DBSA - Aggregated")
    plot_aggregated_3d(df_tpsa, "Pareto Front TPSA - Aggregated")