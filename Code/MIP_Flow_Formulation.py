import gurobipy as gp
from gurobipy import GRB
from InputData import *
from OutputData import *


def Run_MIP():
    # Daten einlesen
    instance_filename = "AnzahlAuftraege_NEW_10/Construction_a10_o107_m5_an57_ar12.json"

    # Erstellen einer InputData-Instanz
    data = InputData(instance_filename)


    # 1. Modell erstellen
    model = gp.Model("MIP_Flow_Formulation")

    # 2a. Sets
    M = list()
    W_m = dict()
    N_m = dict()
    for machine in data.machines:
        M.append(machine.id)
        W_m[machine.id] = machine.default_drivers
        N_m[machine.id] = list()
        for orderItem in data.order_items:
            if orderItem.machine_type == machine.type:
                N_m[machine.id].append(orderItem.id)
    
    W = list()
    for worker in data.workers:
        W.append(worker.personal_number)
    
    A = list()
    A_Class = list()
    for attachment in data.attachments:
        A.append(attachment.id)
        A_Class.append(attachment.type)
        
    N = list()
    for orderItem in data.order_items:
        N.append(orderItem.id)
    
    C = list()
    N_c = dict()
    for order in data.orders:
        C.append(order.site_number)
        N_c[order.site_number] = order.order_item_ids

    
    # SETS für Jobs und Zeiten fehlen


    day_difference = data.end_date - data.start_date
    T_range = list(range(day_difference.days))


    # 2b. Parameter

    T = day_difference.days

    d_ij = data.transport_routes
    d_wj = data.work_routes

    # Daten benötige ich noch von Daniel
    S_Nmax = 10 # Maximal Anzahl an aufeinanderfolgenden Nachtschichten
    S_max = 5 # Maximal Anzahl an Schichten im Zeitraum T_Smax
    T_Smax = 7 # Zeitraum für S_max
    T_Wmax = 10 # Maximale Arbeistzeit pro Schicht
    
    t_o = list()
    for orderItem in data.order_items:
        t_o.append(orderItem.duration)


    # 3a. Laufende Indizes


    K = range(len(C)) # ANNAHME: Es geht um die Baustellen als Indizierte Menge

    I = range(len(N))
    J = range(len(N)) # ANNAHME: Es geht bei I und J um die Bestllpositionen und nicht die Baustellen als Indizierte Menge


    # 3b. Variablen erstellen
    x = model.addVars(M, I, J, vtype=GRB.BINARY, name="x")  # Maschinenflussvariablen
    y = model.addVars(W, I, J, vtype=GRB.BINARY, name="y")  # Arbeiterflussvariablen
    z = model.addVars(A, I, J, vtype=GRB.BINARY, name="z")  # Anbaugeräteflussvariablen --> ANNAHME
    
    s = model.addVars(M, I, vtype=GRB.BINARY, name="s")     # Non-regular driver Nutzung
    u = model.addVars(K, vtype=GRB.BINARY, name="u")     # (Komplette) Baustellen-Erfüllung True/False



    # 4. Zielfunktion setzen
    model.setObjective(
        gp.quicksum(100 * u[k] for k in K) -  # Baustellen-Erfüllung --> Fällt bspw. 100x ins Gewicht
        gp.quicksum(d_ij[i, j] * x[m, i, j] for m in M for i in I for j in J) + # Transportaufwand Maschinen
        gp.quicksum(d_ij[i, j] * y[w, i, j] for w in W for i in I for j in J) + # Arbeitswegeaufwand Arbeiter
        gp.quicksum(d_ij[i, j] * z[a, i, j] for a in A for i in I for j in J), # Transportaufwand Anbaugeräte
        GRB.MAXIMIZE
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


if __name__ == "__main__":
    Run_MIP()