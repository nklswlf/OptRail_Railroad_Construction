import gurobipy as gp
from gurobipy import GRB
import pandas as pd
from InputData import *
from OutputData import *


def Run_MIP():
    # Daten einlesen
    #instance_filename = "AnzahlAuftraege_NEW_10/Construction_a10_o107_m5_an57_ar12.json"
    instance_filename = "Construction_a1_o12_m3_an5_ar3_reduced.json"

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
        W_m[machine.id] = [int(driver) for driver in machine.default_drivers]
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
        N_c[order.site_number] = [int(item_id) for item_id in order.order_item_ids]
    print("C: ", C)

    
    start_date = data.start_date
    end_date = data.end_date

    O_t = dict()  # Tag an dem der Auftrag startet
    O_t_start = dict()  # Startzeiten  
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
        t_start_int = int(t_start)


        # O_t: Gruppiert nach Tagen
        if t_start_int not in O_t:
            O_t[t_start_int] = []
        O_t[t_start_int].append(orderID)
        
        
        # Startzeit
        if t_start not in O_t_start:
            O_t_start[t_start] = []
        O_t_start[t_start].append(orderID)
        
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

    d_ab = data.transport_routes
    d_wb = data.work_routes
    d_ij = list()
    d_wj = list()

    for i in data.order_items:
        row = []
        for j in data.order_items:
            a = next((k for k,v in N_c.items() if i.id in v))
            b = next((k for k,v in N_c.items() if j.id in v))
            row.append(d_ab[a][b])
        d_ij.append(row)


    for i in data.workers:
        row = []
        for j in data.order_items:
            a = next((k for k,v in N_c.items() if j.id in v))
            row.append(d_wb[i.personal_number][a])
        d_wj.append(row)



    SPEED = 1680 # Durchschnittliche Geschwindigkeit des Maschinentransports in 1680 km/Tag --> entspricht 70 km/h
    
    end = len(N)

    for m in M:
        for n in N_m[m]:
            P_mn[m,n] = list()
            S_mn[m,n] = list()

            if n not in P_mn:
                P_mn[m,end] = list()
            P_mn[m,end].append(n) # Anfügen n als Vorgänger des Endknotens
            S_mn[m,n].append(end) # Anfügen Endknoten als Nachfolger von n
            
            for i in N_m[m]:
                if n != i:
                    start_time_n = O_t_start_inverted[n]
                    end_time_n = O_t_end_inverted[n]
                    start_time_i = O_t_start_inverted[i]
                    end_time_i = O_t_end_inverted[i]


                    if start_time_n >= end_time_i: #+ d_ij[i][n] / SPEED: 
                        P_mn[m,n].append(i)

                    if start_time_i > end_time_n:# + d_ij[n][i] / SPEED:
                        S_mn[m,n].append(i)


    P_wn = dict()
    S_wn = dict()

    P_time = 9/24 # 9 Stunden Pausenzeit zwischen zwei Schichten --> 9/24 Tage

    for w in W:
        for n in N_w[w]:
            P_wn[w,n] = list()
            S_wn[w,n] = list()

            if n not in P_wn:
                P_wn[w,end] = list()
            P_wn[w,end].append(n) # Anfügen n als Vorgänger des Endknotens
            S_wn[w,n].append(end) # Anfügen Endknoten als Nachfolger von n
            
            for i in N_w[w]:
                if n != i:
                    start_time_n = O_t_start_inverted[n]
                    end_time_n = O_t_end_inverted[n]
                    start_time_i = O_t_start_inverted[i]
                    end_time_i = O_t_end_inverted[i]

                    if start_time_n >= end_time_i:# + P_time:
                        P_wn[w,n].append(i)

                    if start_time_i >= end_time_n:# + P_time:
                        S_wn[w,n].append(i)
            



    day_difference = end_date - start_date
    T_range = list(range(day_difference.days + 1))

    for m in M:
        N_m[m].append(end)
    for w in W:
        N_w[w].append(end)

    # 2b. Parameter

    T = day_difference.days + 1


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
    x = model.addVars(((m, i, j) for m in M for i in N_m[m] for j in N_m[m]),vtype=GRB.BINARY,name="x")  # Maschinenflussvariablen
    y = model.addVars(((w, i, j) for w in W for i in N_w[w] for j in N_w[w]),vtype=GRB.BINARY,name="y")  # Arbeiterflussvariablen
    
    '''
    z = model.addVars(A, N, N, vtype=GRB.BINARY, name="z")  # Anbaugeräteflussvariablen --> ANNAHME
    '''

    r = model.addVars(((m, i) for m in M for i in N_m[m]),vtype=GRB.BINARY,name="r")    # Non-regular driver Nutzung
    u = model.addVars(C, vtype=GRB.BINARY, name="u")     # (Komplette) Baustellen-Erfüllung True/False



    # 4. Zielfunktion setzen
    model.setObjective(
        gp.quicksum(10 * u[c] for c in C),
        GRB.MAXIMIZE
    )

    '''
        -  # Baustellen-Erfüllung --> Fällt bspw. 100x ins Gewicht
        gp.quicksum(d_ij[i][j] * x[m, i, j] for m in M for i in N_m[m] for j in N_m[m]) - # Transportaufwand Maschinen
        gp.quicksum(d_wj[w][j] * y[w, i, j] for w in W for i in N_w[w] for j in N_w[w]) - # Arbeitswegeaufwand Arbeiter        
        gp.quicksum(r[m, i] for m in M for i in N_m[m]), # Strafkosten für Non-regular driver Nutzung
        GRB.MAXIMIZE
    )
    '''

    '''
    gp.quicksum(d_ij[i, j] * z[a, i, j] for a in A for i in N for j in N), # Transportaufwand Anbaugeräte
    '''


    # 5. Nebenbedingungen
    # Maschinenfluss-Balance
    for m in M:
        for i in N_m[m]:
            model.addConstr(
                gp.quicksum(x[m, j, i] for j in P_mn[m,i]) == gp.quicksum(x[m, i, j] for j in S_mn[m, i]),
                name=f"machine_flow_balance_{m}_{i}"
            )


    for m in M:
        for s in N_m[m]:
            for t in N_m[m]:
                if s != t:
                    left_sum = gp.quicksum(x[m, s, j] for j in S_mn[m,s] if j != t)
                    right_sum = gp.quicksum(x[m, i, t] for i in P_mn[m,t] if i != s)
                    model.addConstr(left_sum == right_sum, name=f"machine_balance_{m}_{s}_{t}")


    # Arbeiterfluss-Balance
    for w in W:
        for i in N_w[w]:
            model.addConstr(
                gp.quicksum(y[w, j, i] for j in P_wn[w,i]) == gp.quicksum(y[w, i, j] for j in S_wn[w,i]),
                name=f"worker_flow_balance_{w}_{i}"
            )


    for w in W:
        for s in N_w[w]:
            for t in N_w[w]: 
                if s != t: 
                    left_sum = gp.quicksum(y[w, s, j] for j in S_wn[w, s] if j != t)
                    right_sum = gp.quicksum(y[w, i, t] for i in P_wn[w, t] if i != s)
                    model.addConstr(left_sum == right_sum, name=f"worker_balance_w_{w}_s{s}_t{t}")


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
        for i in N_m[m]:
            model.addConstr(
                gp.quicksum(x[m, i, j] for j in S_mn[m, i]) 
                <= gp.quicksum(
                    y[w, i, j] 
                    for w in W_m[m] 
                    if (w, i) in S_wn  # Überprüfe, ob der Schlüssel existiert
                    for j in S_wn[(w, i)]
                ) + r[m, i],
                name=f"regular_driver_constraint_{m}_{i}"
            )

    # Baustellen-Erfüllung
    for c in C:
        for i in N_c[c]:
            model.addConstr(
                gp.quicksum(x[m, i, j] for m in M if (m,i) in S_mn for j in S_mn[m,i]) == u[c],
                name=f"machine_site_fulfillment_site:{c}_order:{i}"
            )
            model.addConstr(
                gp.quicksum(y[w, i, j] for w in W if (w,i) in S_wn for j in S_wn[w,i]) == u[c],
                name=f"worker_site_fulfillment_site:{c}_order:{i}"
            )


    # Nachschicht-Beschränkung
    '''
    for w in W:
        for t in T_range with t <= T_Smax - S_max:
            model.addConstr(
                gp.quicksum(y[w, i, j] for i in P_wn[w][j] for j in D if j in T_range) >= 1,
                name=f"shift_constraint_{w}_{t}"
            )
    '''
        
    # Schichtanzahl-Beschränkung
    '''
    for w in W:
        for t in T_range:
            model.addConstr(
                gp.quicksum(y[w, i, j] for j in S_wn[w,i] if j in T_range) <= S_Nmax,
                name=f"night_shift_constraint_{w}_{i}_{t}"
            )
    '''

    # Arbeitszeit-Beschränkung
    for w in W:
        model.addConstr(
            gp.quicksum(t_o[i]*y[w, i, j] for i in N_w[w] for j in S_wn[w,i]) <= T_Wmax,
            name=f"work_time_constraint_{w}"
        )

    
    # Testnebenbedingung
    '''    
    for c in C:
        model.addConstr(
            gp.quicksum(u[c] for c in C) == 1,
            name=f"site_constraint_{c}"
        )
    '''


    # 6. Optimierung
    model.optimize()

    if model.status == GRB.INFEASIBLE:
        print("Das Modell ist nicht lösbar.")
        model.computeIIS()
        return

    # 7. Ergebnisse ausgeben
    if model.status == GRB.OPTIMAL:
        print("Optimale Lösung gefunden:")
        for v in model.getVars():
            if v.x > 2:
                print(f"{v.varName} = {v.x}")
        print(f"Zielfunktionswert = {model.objVal}")
    else:
        print("Keine optimale Lösung gefunden.")


    print("P_mn: ", P_mn)
    print("S_mn: ", S_mn)
    print("P_wn: ", P_wn)
    print("S_wn: ", S_wn)


    # Maschinenfluss-Ergebnisse
    machine_flows = []
    for m in M:
        for i in N_m[m]:
            for j in N_m[m]:
                if x[m, i, j].x > 0.5:  # Nur positive Variablen
                    machine_flows.append([m, i, j, x[m, i, j].x])

    # Arbeiterfluss-Ergebnisse
    worker_flows = []
    for w in W:
        for i in N_w[w]:
            for j in N_w[w]:
                if y[w, i, j].x > 0.5:
                    worker_flows.append([w, i, j, y[w, i, j].x])

    # Baustellen-Erfüllung
    site_fulfillment = []
    for c in C:
        site_fulfillment.append([c, u[c].x])

    # Ergebnisse als DataFrame darstellen
    df_machine = pd.DataFrame(machine_flows, columns=["Machine", "From Order", "To Order", "Flow"])
    df_worker = pd.DataFrame(worker_flows, columns=["Worker", "From Order", "To Order", "Flow"])
    df_site = pd.DataFrame(site_fulfillment, columns=["Site", "Fulfilled"])

    # DataFrames anzeigen
    print("Maschinenfluss:")
    print(df_machine)
    print("\nArbeiterfluss:")
    print(df_worker)
    print("\nBaustellen-Erfüllung:")
    print(df_site)

    model.write("model.lp")



if __name__ == "__main__":
    Run_MIP()