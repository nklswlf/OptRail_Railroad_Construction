import gurobipy as gp
from gurobipy import GRB

# 1. Modell erstellen
model = gp.Model("Staff_Scheduling_MIP")

# 2. Sets und Parameter definieren (Beispiele; tatsächliche Werte erforderlich)
M = [...]    # Set of all machines
W = [...]    # Set of all workers
A = [...]    # Set of all attachments
O = [...]    # Set of all orders
C = [...]    # Set of all construction sites

D_oo = {...}        # Dictionary mit Distanzen zwischen Baustellen für Aufträge o und o'
D_wj = {...}        # Dictionary für Reisekosten zwischen Wohnort des Arbeiters w und Baustelle j
D_transport_mo = {...}   # Transportkosten der Maschinen
P_regular_mo = {...}     # Strafkosten, wenn Maschine m nicht von Stammfahrer verwendet wird
R_c = {...}              # Einnahmen durch Erfüllung von Baustelle c

# 3. Variablen definieren
x = model.addVars(M, O, vtype=GRB.BINARY, name="x")         # Maschinenzuweisung zu Auftrag
y = model.addVars(W, O, vtype=GRB.BINARY, name="y")         # Mitarbeiterzuweisung zu Auftrag
z = model.addVars(A, O, vtype=GRB.BINARY, name="z")         # Anbaugerätezuweisung zu Auftrag
u = model.addVars(C, vtype=GRB.BINARY, name="u")            # Erfüllung von Baustelle
s_mo = model.addVars(M, O, vtype=GRB.BINARY, name="s_mo")   # Strafkostenvariable für Maschinen ohne Stammfahrer

# 4. Zielfunktion definieren
# Minimierung der Gesamtkosten: Kosten für Distanz, Arbeitswege, Strafkosten und Transport
model.setObjective(
    gp.quicksum(R_c[c] * u[c] for c in C) -
    gp.quicksum(D_oo[o, o] * x[m, o] for m in M for o in O for o in O) -
    gp.quicksum(D_wj[w, o] * y[w, o] for w in W for o in O) -
    gp.quicksum(P_regular_mo[m, o] * s_mo[m, o] for m in M for o in O),
    GRB.MINIMIZE
)

# 5. Nebenbedingungen
# Beispiel für die Zuweisung von Arbeitern und Maschinen zu Aufträgen

# Jeder Auftrag o wird maximal einmal pro Maschine und Mitarbeiter zugewiesen
for o in O:
    model.addConstr(gp.quicksum(x[m, o] for m in M) == 1, name=f"Auftrag_Maschinenzuweisung_{o}")
    model.addConstr(gp.quicksum(y[w, o] for w in W) <= 1, name=f"Auftrag_Arbeiterzuweisung_{o}")

# Maschine und Mitarbeiter müssen demselben Auftrag zugewiesen sein
for o in O:
    for m in M:
        model.addConstr(x[m, o] <= gp.quicksum(y[w, o] for w in W), name=f"Maschine_Arbeiter_{m}_{o}")

# Einhaltung der maximalen Arbeitszeit für Mitarbeiter
TW_max = 40  # Maximale Arbeitsstunden (Beispiel)
for w in W:
    model.addConstr(gp.quicksum(y[w, o] for o in O) <= TW_max, name=f"MaxArbeitszeit_{w}")

# Stammfahrerbedingung für Maschinen (Strafkosten bei nicht-stammfahrer)
for m in M:
    for o in O:
        model.addConstr(x[m, o] <= gp.quicksum(y[w, o] for w in W), name=f"Stammfahrer_{m}_{o}")

# Erfüllung der Baustellen (wenn Aufträge abgedeckt sind, ist Baustelle erfüllt)
for c in C:
    model.addConstr(gp.quicksum(u[c] for o in O if o in c) <= 1, name=f"BaustelleErfüllung_{c}")

# 6. Modell optimieren
model.optimize()

# 7. Ergebnisse ausgeben
if model.status == GRB.OPTIMAL:
    print(f"Optimaler Zielfunktionswert: {model.objVal}")
    for v in model.getVars():
        print(f"{v.varName} = {v.x}")
elif model.status == GRB.INFEASIBLE:
    print("Das Modell ist unlösbar.")
elif model.status == GRB.UNBOUNDED:
    print("Das Modell ist unbeschränkt.")
else:
    print("Optimierung konnte nicht abgeschlossen werden.")