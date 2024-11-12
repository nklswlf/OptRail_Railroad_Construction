import gurobipy as gp
from gurobipy import GRB

# 1. Modell erstellen
model = gp.Model("MIP_StaffScheduling")

# 2. Sets und Parameter (Beispielhaft, müssen an die realen Daten angepasst werden)
M = [...]  # Set der Maschinen
W = [...]  # Set der Arbeiter
A = [...]  # Set der Anbaugeräte
O = [...]  # Set der Aufträge
C = [...]  # Set der Baustellen

# Beispielhafte Parameter
Rc = {...}          # Einnahmen für das Erfüllen der Baustellen (Dictionary)
Dwo = {...}         # Reisekosten eines Arbeiters w zum Bauauftrag o
P_regular = {...}   # Strafkosten, wenn Maschine nicht von regulärem Fahrer genutzt wird
D_transport = {...} # Transportkosten einer Maschine für Bauauftrag o

# 3. Variablen erstellen
x = model.addVars(M, O, vtype=GRB.BINARY, name="x")  # Maschinenbelegung
y = model.addVars(W, O, vtype=GRB.BINARY, name="y")  # Arbeiterbelegung
z = model.addVars(A, O, vtype=GRB.BINARY, name="z")  # Anbaugerätebelegung
s = model.addVars(M, O, vtype=GRB.BINARY, name="s")  # Non-regular driver Nutzung
u = model.addVars(C, vtype=GRB.BINARY, name="u")     # Baustelle erfüllt

# 4. Zielfunktion setzen
model.setObjective(
    gp.quicksum(Rc[c] * u[c] for c in C) +
    gp.quicksum(Dwo[w, o] * y[w, o] for w in W for o in O) +
    gp.quicksum(P_regular[m, o] * s[m, o] for m in M for o in O) +
    gp.quicksum(D_transport[m, o] * x[m, o] for m in M for o in O),
    GRB.MINIMIZE
)

# 5. Nebenbedingungen

# Arbeiterzuweisung
for c in C:
    model.addConstr(
        gp.quicksum(y[w, o] for w in W for o in O) >= len(O) * u[c],
        name=f"worker_assignment_{c}"
    )

for o in O:
    model.addConstr(
        gp.quicksum(y[w, o] for w in W) <= 1,
        name=f"one_worker_per_order_{o}"
    )

# Maschinenzuweisung
for o in O:
    model.addConstr(
        gp.quicksum(x[m, o] for m in M) == gp.quicksum(y[w, o] for w in W),
        name=f"machine_worker_match_{o}"
    )

# Anbaugerätezuweisung
for o in O:
    model.addConstr(
        gp.quicksum(z[a, o] for a in A) == gp.quicksum(x[m, o] for m in M),
        name=f"attachment_assignment_{o}"
    )

# Regelmäßiger Fahrer
for m in M:
    for o in O:
        model.addConstr(
            x[m, o] <= gp.quicksum(y[w, o] for w in W) + s[m, o],
            name=f"regular_driver_{m}_{o}"
        )

# Arbeitszeitregelungen - Beispielhaft
T_max = 10  # Maximale Arbeitsstunden pro Arbeiter, hier beispielhaft
for w in W:
    model.addConstr(
        gp.quicksum(y[w, o] for o in O) <= T_max,
        name=f"max_working_hours_{w}"
    )

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