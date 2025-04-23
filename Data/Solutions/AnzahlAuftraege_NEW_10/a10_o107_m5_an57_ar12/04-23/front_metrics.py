import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def dominates(a, b):
    return np.all(a <= b) and np.any(a < b)

def coverage_metric(front_a, front_b):
    count = sum(any(dominates(a, b) for a in front_a) for b in front_b)
    return count / len(front_b)

def epsilon_indicator(front_a, front_b):
    eps_values = []
    for b in front_b:
        eps_b = float('inf')
        for a in front_a:
            eps = max(a_i - b_i for a_i, b_i in zip(a, b))
            eps_b = min(eps_b, eps)
        eps_values.append(eps_b)
    return max(eps_values)

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

# === INPUT FILES ===
file_psa = "Data/Solutions/AnzahlAuftraege_NEW_10/a10_o107_m5_an57_ar12/04-23/PSA/ParetoFront.csv"
file_dbsa = "Data/Solutions/AnzahlAuftraege_NEW_10/a10_o107_m5_an57_ar12/04-23/DBSA/ParetoFront.csv"
file_tpsa = "Data/Solutions/AnzahlAuftraege_NEW_10/a10_o107_m5_an57_ar12/04-23/TPSA/ParetoFront.csv"

columns = ['Driver Violation', 'Commute Distance', 'Transport Machines',
           'Transport Attachments', 'Machines', 'Workers', 'Attachments']

# === LOAD DATA ===
df_psa = pd.read_csv(file_psa)
df_dbsa = pd.read_csv(file_dbsa)
df_tpsa = pd.read_csv(file_tpsa)
front_psa = df_psa[columns].to_numpy()
front_dbsa = df_dbsa[columns].to_numpy()
front_tpsa = df_tpsa[columns].to_numpy()

# === METRICS ===
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

# === SINGLE BEST VALUES ===
sbv_psa = df_psa[columns].min()
sbv_dbsa = df_dbsa[columns].min()
sbv_tpsa = df_tpsa[columns].min()

print("\n=== Single Best Values ===")
print(f"{'Metric':20} {'PSA (min)':>12} {'DBSA (min)':>12} {'TPSA (min)':>12}")
for col in columns:
    print(f"{col:20} {sbv_psa[col]:12.3f} {sbv_dbsa[col]:12.3f} {sbv_tpsa[col]:12.3f}")

# === PLOTS ===
plot_aggregated_3d(df_psa, "Pareto Front PSA - Aggregated")
plot_aggregated_3d(df_dbsa, "Pareto Front DBSA - Aggregated")
plot_aggregated_3d(df_tpsa, "Pareto Front TPSA - Aggregated")