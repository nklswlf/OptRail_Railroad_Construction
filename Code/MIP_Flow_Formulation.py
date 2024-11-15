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
    N_w = dict() # ANNAHME: N_w ist die Menge der Bestellungen, die ein Arbeiter bearbeiten kann
    for worker in data.workers:
        W.append(worker.personal_number)
        for orderItem in data.order_items:
            if orderItem.worker_qualifications == []:
                if worker.personal_number not in N_w:
                    N_w[worker.personal_number] = list()
                N_w[worker.personal_number].append(orderItem.id)
            elif orderItem.worker_qualifications == worker.qualifications:
                if worker.personal_number not in N_w:
                    N_w[worker.personal_number] = list()
                N_w[worker.personal_number].append(orderItem.id)
            
    
    '''
    A = list()
    A_Class = list()
    N_a = dict() # ANNAHME: N_a ist die Menge der Bestellungen, die ein Anbaugerät bearbeiten kann
    for attachment in data.attachments:
        A.append(attachment.id)
        A_Class.append(attachment.type)
    '''
        
    N = list()
    for orderItem in data.order_items:
        N.append(orderItem.id)
    
    C = list()
    N_c = dict()
    for order in data.orders:
        C.append(order.site_number)
        N_c[order.site_number] = order.order_item_ids

    
    start_date = data.start_date
    end_date = data.end_date


    O_t = dict()  # Startzeiten --> im Modell angegeben    
    O_t_end = dict()  # Endzeiten
    O_t_start_inverted = dict()  # Umgekehrtes O_t (Startzeiten)
    O_t_end_inverted = dict()  # Umgekehrtes O_t_end (Endzeiten)

    SECONDS_IN_A_DAY = 86400

    for orderItem in data.order_items:
        orderID = orderItem.id 

        # Startzeit
        orderItem_start_date = orderItem.start_time
        delta_start = (orderItem_start_date - start_date)
        t_start = delta_start.total_seconds() / SECONDS_IN_A_DAY
        
        # Original O_t: Gruppiert nach Startzeit
        if t_start not in O_t:
            O_t[t_start] = []
        O_t[t_start].append(orderID)
        
        # Invertiertes Dictionary O_t_start_inverted
        O_t_start_inverted[orderID] = t_start

        # Endzeit
        orderItem_end_date = orderItem.end_time
        delta_end = (orderItem_end_date - start_date)
        t_end = delta_end.total_seconds() / SECONDS_IN_A_DAY

        # O_t_end: Gruppiert nach Endzeit
        if t_end not in O_t_end:
            O_t_end[t_end] = []
        O_t_end[t_end].append(orderID)
        
        # Invertiertes Dictionary O_t_end_inverted
        O_t_end_inverted[orderID] = t_end



    P_mn = dict()
    S_mn = dict()

    for m in M:
        for n in N_m[m]:
            P_mn[m,n] = list()
            S_mn[m,n] = list()
            for i in N_m[m]:
                if n != i:
                    start_time_n = O_t_start_inverted[n]
                    end_time_n = O_t_end_inverted[n]
                    start_time_i = O_t_start_inverted[i]
                    end_time_i = O_t_end_inverted[i]

                    if start_time_n > end_time_i:  # Mit Travel time und kleiner gleich
                        P_mn[m,n].append(i)

                    if start_time_i > end_time_n:
                        S_mn[m,n].append(i)


    P_wn = dict()
    S_wn = dict()

    # Hier muss die Ruhezeit noch berücksichtigt werden

    for w in W:
        for n in N_w[w]:
            P_wn[w,n] = list()
            S_wn[w,n] = list()
            for i in N_w[w]:
                if n != i:
                    start_time_n = O_t_start_inverted[n]
                    end_time_n = O_t_end_inverted[n]
                    start_time_i = O_t_start_inverted[i]
                    end_time_i = O_t_end_inverted[i]

                    if start_time_n > end_time_i:
                        P_mn[m,n].append(i)

                    if start_time_i > end_time_n:
                        S_mn[m,n].append(i)
            



    day_difference = end_date - start_date
    T_range = list(range(day_difference.days))


    # 2b. Parameter

    T = day_difference.days

    d_ij = data.transport_routes
    d_wj = data.work_routes

    S_Nmax = 5 # Maximal Anzahl an aufeinanderfolgenden Nachtschichten
    S_max = 10 # Maximal Anzahl an Schichten im Zeitraum T_Smax
    T_Smax = 14 # Zeitraum für S_max
    T_Wmax = 40 # Maximale Arbeistzeit im Betrachtungszeitraum/Monat ?
    
    t_o = list()
    for orderItem in data.order_items:
        t_o.append(orderItem.duration)


    # XX. Laufende Indizes --> Möglicherweise gar nicht nötig

    K = range(len(C)) # ANNAHME: Es geht um die Baustellen als Indizierte Menge

    I = range(len(N))
    J = range(len(N)) # ANNAHME: Es geht bei I und J um die Bestllpositionen und nicht die Baustellen als Indizierte Menge


    # 3. Variablen erstellen
    x = model.addVars(M, N, N, vtype=GRB.BINARY, name="x")  # Maschinenflussvariablen
    y = model.addVars(W, N, N, vtype=GRB.BINARY, name="y")  # Arbeiterflussvariablen
    
    '''
    z = model.addVars(A, N, N, vtype=GRB.BINARY, name="z")  # Anbaugeräteflussvariablen --> ANNAHME
    '''

    s = model.addVars(M, N, vtype=GRB.BINARY, name="s")     # Non-regular driver Nutzung
    u = model.addVars(C, vtype=GRB.BINARY, name="u")     # (Komplette) Baustellen-Erfüllung True/False



    # 4. Zielfunktion setzen
    model.setObjective(
        gp.quicksum(100 * u[k] for k in C) -  # Baustellen-Erfüllung --> Fällt bspw. 100x ins Gewicht
        gp.quicksum(d_ij[i, j] * x[m, i, j] for m in M for i in N_m[m] for j in N_m[m]) + # Transportaufwand Maschinen
        gp.quicksum(d_ij[i, j] * y[w, i, j] for w in W for i in N for j in N) + # Arbeitswegeaufwand Arbeiter        
        gp.quicksum(s[m, i] for m in M for i in N), # Strafkosten für Non-regular driver Nutzung
        GRB.MAXIMIZE
    )

    '''
    gp.quicksum(d_ij[i, j] * z[a, i, j] for a in A for i in N for j in N), # Transportaufwand Anbaugeräte
    '''


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

    '''
    # Anbaugerätefluss-Balance
    for a in A:
        for i in N:
            model.addConstr(
                gp.quicksum(z[a, j, i] for j in N) == gp.quicksum(z[a, i, j] for j in N),
                name=f"attachment_flow_balance_{a}_{i}"
            )
    '''
            
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