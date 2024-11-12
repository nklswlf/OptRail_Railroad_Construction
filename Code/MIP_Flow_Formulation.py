import gurobipy as gp
from gurobipy import GRB

# 1. Modell erstellen
model = gp.Model("MIP_Flow_Formulation")

# 2. Sets und Parameter (Beispielhaft, müssen an die realen Daten angepasst werden)
M = [...]  # Set der Maschinen
W = [...]  # Set der Arbeiter
A = [...]  # Set der Anbaugeräte
N = [...]  # Set der Nodes
dij = {...}  # Distanzen zwischen den Knoten (Dictionary mit Tupeln (i, j) als Schlüssel)

# 3. Variablen erstellen
x = model.addVars(M, N, N, vtype=GRB.BINARY, name="x")  # Maschinenflussvariablen
y = model.addVars(W, N, N, vtype=GRB.BINARY, name="y")  # Arbeiterflussvariablen
z = model.addVars(A, N, N, vtype=GRB.BINARY, name="z")  # Anbaugeräteflussvariablen
s = model.addVars(M, N, vtype=GRB.BINARY, name="s")     # Non-regular driver Nutzung

# 4. Zielfunktion setzen (Beispielhaft)
model.setObjective(
    gp.quicksum(dij[i, j] * x[m, i, j] for m in M for i in N for j in N) +
    gp.quicksum(dij[i, j] * y[w, i, j] for w in W for i in N for j in N) +
    gp.quicksum(dij[i, j] * z[a, i, j] for a in A for i in N for j in N),
    GRB.MINIMIZE
)

# 5. Nebenbedingungen
# Maschinenfluss-Balance
for m in M:
    for i in N:
        model.addConstr(
            gp.quicksum(x[m, j, i] for j in N) == gp.quicksum(x[m, i, j] for j in N),
            name=f"machine_flow_balance_{m}_{i}"
        )

# Arbeiterfluss-Balance
for w in W:
    for i in N:
        model.addConstr(
            gp.quicksum(y[w, j, i] for j in N) == gp.quicksum(y[w, i, j] for j in N),
            name=f"worker_flow_balance_{w}_{i}"
        )

# Anbaugerätefluss-Balance
for a in A:
    for i in N:
        model.addConstr(
            gp.quicksum(z[a, j, i] for j in N) == gp.quicksum(z[a, i, j] for j in N),
            name=f"attachment_flow_balance_{a}_{i}"
        )

# Regelmäßige Fahrer - Nebenbedingung
for m in M:
    for i in N:
        model.addConstr(
            gp.quicksum(x[m, i, j] for j in N) <= gp.quicksum(y[w, i, j] for w in W for j in N) + s[m, i],
            name=f"regular_driver_constraint_{m}_{i}"
        )

# Weitere Constraints können gemäß dem Modell hinzugefügt werden...

# 6. Optimierung
model.optimize()

# 7. Ergebnisse ausgeben
if model.status == GRB.OPTIMAL:
    print("Optimale Lösung gefunden:")
    for v in model.getVars():
        print(f"{v.varName} = {v.x}")
    print(f"Zielfunktionswert = {model.objVal}")
else:
    print("Keine optimale Lösung gefunden.")