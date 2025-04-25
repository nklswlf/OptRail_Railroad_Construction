import os
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist

# === 1. Pfad-Zuweisung: Methodenname → Pfad zur CSV-Datei ===
method_paths = {
    "PSA": "a10_o107_m5_an57_ar12/PSA/ParetoFront.csv",
    "DBSA": "a10_o107_m5_an57_ar12/DBSA/ParetoFront.csv",
    "TPSA": "a10_o107_m5_an57_ar12/TPSA/ParetoFront.csv"
}

# === 2. Zielfunktionen, die für DCI & PCI verwendet werden ===
objectives = [
    "Driver Violation",
    "Commute Distance",
    "Transport Machines",
    "Transport Attachments",
    "Machines",
    "Workers",
    "Attachments"
]

# === 3. Globale Pareto-Front erstellen inkl. Methoden-Zuordnung ===
all_data = []
for method, path in method_paths.items():
    df = pd.read_csv(path)
    df = df[objectives].copy()
    df["Method"] = method
    all_data.append(df)

all_data_concat = pd.concat(all_data, ignore_index=True)

print("\n--- All solutions from all methods ---")
print(all_data_concat)

# Nicht-dominierte Lösungen bestimmen (global über alle Methoden)
def is_dominated(row, others):
    return np.any(np.all(others <= row, axis=1) & np.any(others < row, axis=1))

pareto_rows = []
data_values = all_data_concat[objectives].values
for i, row in enumerate(data_values):
    if not is_dominated(row, np.delete(data_values, i, axis=0)):
        pareto_rows.append(i)

pareto_df = all_data_concat.iloc[pareto_rows].reset_index(drop=True)

print("\n--- Combined Pareto Front ---")
print(pareto_df)
# === 3.1. Pareto Front nach Methoden gruppieren ===
pareto_groups = {}
for method in method_paths.keys():
    pareto_groups[method] = pareto_df[pareto_df["Method"] == method].reset_index(drop=True)
print("\n--- Combined Pareto Front grouped by method ---")
for method, group in pareto_groups.items():
    print(f"\n--- {method} ---")
    print(group)

# === 4. Ideal, Nadir und Upper Bound auf Basis globaler Paretofront ===
div = 5
ideal_point = pareto_df[objectives].min()
nadir_point = pareto_df[objectives].max()
upper_bound = nadir_point + (nadir_point - ideal_point) / (2 * div)
lower_bound = ideal_point

box_size = (upper_bound - lower_bound) / div

print("\n--- Ideal Point ---")
print(ideal_point)
print("\n--- Nadir Point ---")
print(nadir_point)
print("\n--- Upper Bound ---")
print(upper_bound)
print("\n--- Box Size ---")
print(box_size)

# === 4.2 Ziele ohne Streuung erkennen und entfernen ===
valid_dims = box_size != 0
if not valid_dims.all():
    removed = list(box_size[~valid_dims].index)
    print(f"\n⚠️  These objectives have no variation and are removed for DCI calculation: {removed}")

# Angepasste Grid-Zuordnung basierend auf gültigen Dimensionen
def get_grid_index(row):
    return tuple(((row[valid_dims] - lower_bound[valid_dims]) / box_size[valid_dims]).astype(int))


# Belegte Boxen erfassen
grid_cells_by_method = {method: set() for method in method_paths}
cell_contributions = {}

for method, df in pareto_groups.items():
    for _, row in df[objectives].iterrows():
        cell = get_grid_index(row)
        grid_cells_by_method[method].add(cell)

# Alle belegten Zellen aus allen Methoden
all_cells = set().union(*grid_cells_by_method.values())

# === 4.3 Distanzbasierte Contribution Degree (CD) Berechnung ===
from math import sqrt

cd_matrix = {method: {} for method in method_paths}
m = valid_dims.sum()  # effektive Dimensionalität nach Ausschluss

# Precompute Grid-Zellen aller Lösungen pro Methode
grid_index_by_method = {
    method: [get_grid_index(row) for _, row in df[objectives].iterrows()]
    for method, df in pareto_groups.items()
}

# Für jede belegte Box berechne CD(P, h)
for cell in all_cells:
    for method, grid_indices in grid_index_by_method.items():
        # Berechne minimale Distanz D(P, h)
        distances = [np.linalg.norm(np.array(cell) - np.array(p_cell)) for p_cell in grid_indices]
        D = min(distances)
        threshold = sqrt(m + 1)
        if D < threshold:
            CD = 1 - (D**2) / (m + 1)
            cd_matrix[method][cell] = CD
        else:
            cd_matrix[method][cell] = 0.0

# Ausgabe: Beispielhafte CD-Werte
print("\n--- Example Contribution Degrees ---")
for method, contributions in cd_matrix.items():
    non_zero = {k: v for k, v in contributions.items() if v > 0}
    print(f"{method}: {list(non_zero.items())[:5]}")


# === 4. Diversity Comparison Indicator (DCI) ===
# === 4.4 Finaler DCI-Wert pro Methode berechnen ===
dci_result = {}
S = len(all_cells)
for method in method_paths:
    contribution_sum = sum(cd_matrix[method].get(cell, 0.0) for cell in all_cells)
    dci_result[method] = contribution_sum / S if S > 0 else 0.0


# === 5. Performance Comparison Indicator (PCI) ===


# === 6. Berechnung ===


# === 7. Ergebnis als Tabelle ===
result_df = pd.DataFrame({
    "DCI": dci_result
}).T

print("\n--- Vergleich der Methoden (DCI & PCI) ---")
print(result_df)