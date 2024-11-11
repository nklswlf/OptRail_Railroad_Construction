import gurobipy as gp
from gurobipy import GRB

# 1. Modell erstellen
model = gp.Model("Flow_Formulation_MIP")

# 2. Sets und Parameter definieren (als Beispiel)
# Hinweis: Hier muss der Nutzer die tatsächlichen Daten bereitstellen.
M = [...]  # Set of all machines
W = [...]  # Set of all workers
C = [...]  # Set of all construction sites
O = [...]  # Set of all order positions

# Beispiel-Parameter
d_ij = {...}    # Dictionary mit Distanzen zwischen Baustellen i und j
d_wj = {...}    # Dictionary mit Distanz zwischen dem Wohnort von w und der Baustelle j
T_max = 10      # Maximale Anzahl an Arbeitstagen
TW_max = 40     # Maximale Arbeitszeit

# 3. Variablen erstellen
# Beispiel: Binäre Variablen für den Besuch einer Baustelle durch Maschine und Arbeiter
x = model.addVars(M, O, O, vtype=GRB.BINARY, name="x")  # z.B. xm_ij = 1, wenn Maschine m von i nach j fährt
y = model.addVars(W, O, O, vtype=GRB.BINARY, name="y")  # z.B. yw_ij = 1, wenn Arbeiter w von i nach j fährt
z = model.addVars(M, C, vtype=GRB.BINARY, name="z")     # zmc = 1, wenn Maschine m für Baustelle c eingesetzt wird
s = model.addVars(M, vtype=GRB.INTEGER, name="s")       # Strafvariable für nicht-reguläre Fahrer

# 4. Zielfunktion definieren
# Beispiel-Zielfunktion (abhängig von Maschinen, Distanzen und Strafkosten)
model.setObjective(
    gp.quicksum(d_ij[i, j] * x[m, i, j] for m in M for i in O for j in O) +
    gp.quicksum(d_wj[w, j] * y[w, i, j] for w in W for i in O for j in O) +
    gp.quicksum(s[m] for m in M),
    GRB.MINIMIZE
)

# 5. Nebenbedingungen hinzufügen
# Beispiel für Flussgleichungen und Maschinenzuweisungen

# Maschinenfluss (jede Baustelle wird durch eine Maschine besucht)
for m in M:
    for i in O:
        model.addConstr(gp.quicksum(x[m, j, i] for j in O) == gp.quicksum(x[m, i, j] for j in O), name=f"Maschinenfluss_{m}_{i}")

# Ein Maschinenbesuch pro Baustelle
for i in O:
    model.addConstr(gp.quicksum(x[m, i, j] for m in M for j in O) == 1, name=f"Besuch_{i}")

# Maximale Arbeitszeit (für die Arbeitskräfte)
for w in W:
    model.addConstr(gp.quicksum(y[w, i, j] for i in O for j in O) <= TW_max, name=f"Arbeitszeit_{w}")

# Weitere spezifische Constraints gemäß Dokumentation hier hinzufügen.

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