import gurobipy as gp
from gurobipy import GRB
import pandas as pd
from InputData import *
from OutputData import *
import json
from Gantt_Plan import CreateGanttDiagram

# Instanz-Datei
# Reduced
#instance_filename = "Construction_a1_o12_m3_an5_ar3_reduced.json"
#instance_filename = "Construction_a3_o80_m10_an10_ar9_reduced.json"
#instance_filename = "Construction_a5_o96_m10_an10_ar10_reduced.json"

# 10 Baustellen
instance_filename = "Construction_a10_o107_m5_an57_ar12.json"
#instance_filename = "Construction_a10_o114_m6_an57_ar11.json"
#instance_filename = "Construction_a10_o118_m6_an53_ar13.json"
#instance_filename = "Construction_a10_o119_m5_an54_ar13.json"

# 15 Baustellen
#instance_filename = "Construction_a15_o191_m8_an74_ar18.json"

# 20 Baustellen
#instance_filename = "Construction_a20_o259_m11_an101_ar26.json"

# 50 Baustellen
#instance_filename = "Construction_a50_o578_m28_an276_ar66.json"



# Definition der Abeitszeit-Parameter
S_Nmax = 5 # Maximal Anzahl an aufeinanderfolgenden Nachtschichten
S_max = 10 # Maximal Anzahl an Schichten im Zeitraum T_Smax
T_Smax = 14 # Zeitraum für S_max
T_Wmax = 160 # Maximale Arbeistzeit im Betrachtungszeitraum/Monat


def Run_MIP():

    data, M, W, W_m, N_m, N_w, N, C, N_c, P_mn, S_mn, P_wn, S_wn, d_ij, d_wj, start, end, T_range,  T, t_o, D_r, N_r, A_r = DefineData(instance_filename)

    model,x,y,r,u = DefineModel(M, W, W_m, N_m, N_w, N, C, N_c, P_mn, S_mn, P_wn, S_wn, d_ij, d_wj, start, end, T_range,  T,t_o, D_r, N_r, A_r)

    
    model.optimize()
    





    # Maschinenfluss-Ergebnisse
    machine_flows = []
    for m in M:
        for i in N_m[m]:
            for j in N_m[m]:
                if x[m, start, j].x > 0.5 and [m, "start", j, x[m, start, j].x] not in machine_flows:
                    machine_flows.append([m, "start", j, x[m, start, j].x])
                if x[m, i, j].x > 0.5:
                    machine_flows.append([m, i, j, x[m, i, j].x])
            if x[m, i, end].x > 0.5 and [m, i, "end", x[m, i, end].x] not in machine_flows:
                machine_flows.append([m, i, "end", x[m, i, end].x])
        if x[m, start, end].x > 0.5 and [m, "start", "end", x[m, start, end].x] not in machine_flows:
            machine_flows.append([m, "start", "end", x[m, start, end].x])
        

    # Arbeiterfluss-Ergebnisse
    worker_flows = []
    for w in W:
        for i in N_w[w]:
            for j in N_w[w]:
                if y[w, start, j].x > 0.5 and [w, "start", j, y[w, start, j].x] not in worker_flows:
                    worker_flows.append([w, "start", j, y[w, start, j].x])
                if y[w, i, j].x > 0.5:
                    worker_flows.append([w, i, j, y[w, i, j].x])
            if y[w, i, end].x > 0.5 and [w, i, "end", y[w, i, end].x] not in worker_flows:
                worker_flows.append([w, i, "end", y[w, i, end].x])
        if y[w, start, end].x > 0.5 and [w, "start", "end", y[w, start, end].x] not in worker_flows:
            worker_flows.append([w, "start", "end", y[w, start, end].x])

    # Baustellen-Erfüllung
    site_fulfillment = []
    for c in C:
        site_fulfillment.append([c, u[c].x])

    # Ergebnisse als DataFrame darstellen
    df_machine = pd.DataFrame(machine_flows, columns=["Machine", "From Order", "To Order", "Flow"])
    df_worker = pd.DataFrame(worker_flows, columns=["Worker", "From Order", "To Order", "Flow"])
    df_site = pd.DataFrame(site_fulfillment, columns=["Site", "Fulfilled"])

    # DataFrames anzeigen
    print("\nMaschinenfluss:")
    print(df_machine)
    print("\nArbeiterfluss:")
    print(df_worker)
    print("\nBaustellen-Erfüllung:")
    print(df_site)
    print("\nRegular Driver nicht beachtet:")
    summe = sum(r[i].x for i in N)
    print("Anzahl an Aufträgen mit Non-regular driver von Gesamt: ", int(summe), "/", len(N))

    model.write("model.lp")


    # Ergebnisse in Output-Datei speichern
    solution_data = {"Arbeiterzuweisung": {}}

    for w in W:
        current_worker = next(worker for worker in data.workers if worker.personal_number == w)   
        for i in N_w[w]:
            current_orderItem = next(orderItem for orderItem in data.order_items if orderItem.id == i)            
            for j in N_w[w]:
                if i != j and y[w, i, j].x > 0.5:
                    if current_worker.name not in solution_data["Arbeiterzuweisung"]:
                        solution_data["Arbeiterzuweisung"][current_worker.name] = []
                    set = {"ID": current_orderItem.id,
                           "Start": current_orderItem.start_time.isoformat(),
                           "Ende": current_orderItem.end_time.isoformat(),
                           "Dauer": current_orderItem.duration,
                           "Auftragsnummer": current_orderItem.order_number,
                           "MaschinenTyp": current_orderItem.machine_type,
                           "AnbaugeraeteTypen": current_orderItem.equipment_types,
                           "Arbeiterqualifikationen": current_orderItem.worker_qualifications,
                           "zugewieseneMaschine" : current_orderItem.assigned_machine,
                           "Typ": current_orderItem.type}
                    solution_data["Arbeiterzuweisung"][current_worker.name].append(set)


            if y[w, i, end].x > 0.5:
                if current_worker.name not in solution_data["Arbeiterzuweisung"]:
                    solution_data["Arbeiterzuweisung"][current_worker.name] = []
                set = {"ID": current_orderItem.id,
                          "Start": current_orderItem.start_time.isoformat(),
                          "Ende": current_orderItem.end_time.isoformat(),
                          "Dauer": current_orderItem.duration,
                          "Auftragsnummer": current_orderItem.order_number,
                          "MaschinenTyp": current_orderItem.machine_type,
                          "AnbaugeraeteTypen": current_orderItem.equipment_types,
                          "Arbeiterqualifikationen": current_orderItem.worker_qualifications,
                          "zugewieseneMaschine" : current_orderItem.assigned_machine,
                          "Typ": current_orderItem.type}
                solution_data["Arbeiterzuweisung"][current_worker.name].append(set)

    solution_data["Maschinenzuweisung"] = {}

    for m in M:
        current_machine = next(machine for machine in data.machines if machine.id == m)
        for i in N_m[m]:
            current_orderItem = next(orderItem for orderItem in data.order_items if orderItem.id == i)            
            for j in N_m[m]:
                if i != j and x[m, i, j].x > 0.5:
                    if current_machine.name not in solution_data["Maschinenzuweisung"]:
                        solution_data["Maschinenzuweisung"][current_machine.name] = []
                    set = {"ID": current_orderItem.id,
                        "Start": current_orderItem.start_time.isoformat(),
                        "Ende": current_orderItem.end_time.isoformat(),
                        "Dauer": current_orderItem.duration,
                        "Auftragsnummer": current_orderItem.order_number,
                        "MaschinenTyp": current_orderItem.machine_type,
                        "AnbaugeraeteTypen": current_orderItem.equipment_types,
                        "Arbeiterqualifikationen": current_orderItem.worker_qualifications,
                        "zugewieseneMaschine" : current_orderItem.assigned_machine,
                        "Typ": current_orderItem.type}
                    solution_data["Maschinenzuweisung"][current_machine.name].append(set)
            if x[m, i, end].x > 0.5:
                set = {"ID": current_orderItem.id,
                        "Start": current_orderItem.start_time.isoformat(),
                        "Ende": current_orderItem.end_time.isoformat(),
                        "Dauer": current_orderItem.duration,
                        "Auftragsnummer": current_orderItem.order_number,
                        "MaschinenTyp": current_orderItem.machine_type,
                        "AnbaugeraeteTypen": current_orderItem.equipment_types,
                        "Arbeiterqualifikationen": current_orderItem.worker_qualifications,
                        "zugewieseneMaschine" : current_orderItem.assigned_machine,
                        "Typ": current_orderItem.type}
                solution_data["Maschinenzuweisung"][current_machine.name].append(set)


    parent_folder = data._parent_folder
    print(parent_folder)
    solution_path = Path.cwd().parent / "Data" / "Solution" / parent_folder
    solution_path.mkdir(parents=True, exist_ok=True)
    output_filename = solution_path / f"Loesung_{instance_filename}"
    with open(output_filename, "w") as output_file:
        json.dump(solution_data, output_file, indent=4)


    print("Runtime:" , round(model.Runtime,4) , " Sekunden")
    print(f"Zielfunktionswert = {model.objVal}")


    
    CreateGanttDiagram(instance_filename, parent_folder)


def DefineData(instance_filename):

    data = InputData(instance_filename)

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
    N_w = dict()
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
            
        
    N = list()
    for orderItem in data.order_items:
        N.append(orderItem.id)

    C = list()
    N_c = dict()
    for order in data.orders:
        C.append(order.site_number)
        N_c[order.site_number] = [int(item_id) for item_id in order.order_item_ids]


    start_date = data.start_date
    end_date = data.end_date

    O_t = dict()  # Tag an dem der Auftrag startet
    D_r = dict()  # Tagschichten mit Tag als Key
    N_r = dict()  # Nachtschichten mit Tag als Key
    A_r = dict()  # Alle Schichten mit Tag als Key
    O_t_start = dict()  # Startzeiten  
    O_t_end = dict()  # Endzeiten
    O_t_start_inverted = dict()  # Umgekehrtes O_t (Startzeiten)
    O_t_end_inverted = dict()  # Umgekehrtes O_t_end (Endzeiten)

    SECONDS_IN_A_DAY = 86400 # 

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


        # D_r Tagschichten mit Tag als Key
        if t_start_int not in D_r:
            D_r[t_start_int] = []
        if orderItem.start_time.hour <= 12:
            D_r[t_start_int].append(orderID)

        # N_r Nachtschichten mit Tag als Key
        if t_start_int not in N_r:
            N_r[t_start_int] = []
        if orderItem.start_time.hour > 12:
            N_r[t_start_int].append(orderID)
         
        # A_r Alle Schichten mit Tag als Key
        if t_start_int not in A_r:
            A_r[t_start_int] = []
        A_r[t_start_int].append(orderID)
        
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

    start = len(N)
    end = len(N) + 1

    for m in M:
        for n in N_m[m]:

            if (m,start) not in P_mn:
                P_mn[m,start] = list()
                S_mn[m,start] = list()
                S_mn[m,start].append(end) # Anfügen Endknoten als Nachfolger des Startknotens
            if (m,end) not in P_mn:
                P_mn[m,end] = list()
                S_mn[m,end] = list()
                P_mn[m,end].append(start) # Anfügen Startknoten als Vorgänger des Endknotens


            P_mn[m,n] = list()
            S_mn[m,n] = list()


            P_mn[m,n].append(start) # Anfügen Startknoten als Vorgänger von n
            S_mn[m,start].append(n) # Anfügen n als Nachfolger des Startknotens

            P_mn[m,end].append(n) # Anfügen n als Vorgänger des Endknotens
            S_mn[m,n].append(end) # Anfügen Endknoten als Nachfolger von n
            
            for i in N_m[m]:
                if n != i:
                    start_time_n = O_t_start_inverted[n]
                    end_time_n = O_t_end_inverted[n]
                    start_time_i = O_t_start_inverted[i]
                    end_time_i = O_t_end_inverted[i]


                    if start_time_n >= end_time_i + d_ij[i][n] / SPEED: 
                        P_mn[m,n].append(i)

                    if start_time_i > end_time_n + d_ij[n][i] / SPEED:
                        S_mn[m,n].append(i)


    P_wn = dict()
    S_wn = dict()

    P_time = 9/24 # 9 Stunden Pausenzeit zwischen zwei Schichten --> 9/24 Tage

    for w in W:
        for n in N_w[w]:
            
            if (w,start) not in P_wn:
                P_wn[w,start] = list()
                S_wn[w,start] = list()
                S_wn[w,start].append(end)
            if (w,end) not in P_wn:
                P_wn[w,end] = list()
                S_wn[w,end] = list()
                P_wn[w,end].append(start)
            
            P_wn[w,n] = list()
            S_wn[w,n] = list()

            P_wn[w,n].append(start)
            S_wn[w,start].append(n)
            
            P_wn[w,end].append(n)
            S_wn[w,n].append(end)
            
            for i in N_w[w]:
                if n != i:
                    start_time_n = O_t_start_inverted[n]
                    end_time_n = O_t_end_inverted[n]
                    start_time_i = O_t_start_inverted[i]
                    end_time_i = O_t_end_inverted[i]

                    if start_time_n >= end_time_i + P_time:
                        P_wn[w,n].append(i)

                    if start_time_i >= end_time_n + P_time:
                        S_wn[w,n].append(i)
            



    day_difference = end_date - start_date
    T_range = list(range(day_difference.days + 1))


    # 2b. Parameter

    T = day_difference.days + 1

    # T anpassen wenn Instanz nicht über den gesamten Zeitraum geht
    end_date_adjusted = start_date
    for orderItem in data.order_items:
        if end_date_adjusted < orderItem.start_time:
            end_date_adjusted = orderItem.start_time
    T = (end_date_adjusted - start_date).days + 1




    t_o = list()
    for orderItem in data.order_items:
        t_o.append(orderItem.duration)


    return data, M, W, W_m, N_m, N_w, N, C, N_c, P_mn, S_mn, P_wn, S_wn, d_ij, d_wj, start, end, T_range,  T,t_o, D_r, N_r, A_r


def DefineModel(M, W, W_m, N_m, N_w, N, C, N_c, P_mn, S_mn, P_wn, S_wn, d_ij, d_wj, start, end, T_range, T, t_o, D_r, N_r, A_r):

    model = gp.Model("MIP_Flow_Formulation")


    # 1. Variablen erstellen
    # Variablen-Indizes definieren
    indices_1 = [(m, i, j) for m in M for i in N_m[m] for j in N_m[m]]  # (m, i, j)
    indices_2 = [(m, start, j) for m in M for j in N_m[m]]  # (m, start, j)
    indices_3 = [(m, i, end) for m in M for i in N_m[m]]  # (m, i, end)
    indices_4 = [(m, start, end) for m in M]  # (m, start, end)
    all_indices = indices_1 + indices_2 + indices_3 + indices_4
    # Maschinenfluss Variablen erstellen
    x = model.addVars(all_indices, vtype=GRB.BINARY, name="x")
    
    # Variablen-Indizes definieren
    indices_1 = [(w, i, j) for w in W for i in N_w[w] for j in N_w[w]]  # (w, i, j)
    indices_2 = [(w, start, j) for w in W for j in N_w[w]]  # (w, start, j)
    indices_3 = [(w, i, end) for w in W for i in N_w[w]]  # (w, i, end)
    indices_4 = [(w, start, end) for w in W]  # (w, start, end)
    all_indices = indices_1 + indices_2 + indices_3 + indices_4
    # Arbeiterfluss Variablen erstellen
    y = model.addVars(all_indices, vtype=GRB.BINARY, name="y")

    # Non-regular driver Nutzung
    r = model.addVars(N,vtype=GRB.BINARY,name="r")

    # (Komplette) Baustellen-Erfüllung True/False
    u = model.addVars(C, vtype=GRB.BINARY, name="u")


    # 2. Zielfunktion setzen
    model.setObjective(
        gp.quicksum(100000 * u[c] for c in C) -  # Baustellen-Erfüllung --> Fällt bspw. 100x ins Gewicht
        gp.quicksum(0.5 * d_ij[i][j] * x[m, i, j] for m in M for i in N_m[m] for j in N_m[m]) - # Transportaufwand Maschinen
        gp.quicksum(0.5 * d_wj[w][j] * y[w, i, j] for w in W for i in N_w[w] for j in N_w[w]) - # Arbeitswegeaufwand Arbeiter        
        gp.quicksum(100 * x[m, start, j] for m in M for j in N_m[m]) - # Fixkosten für Maschinen
        gp.quicksum(100 * y[w, start, j] for w in W for j in N_w[w]) - # Fixkosten für Arbeiter   
        gp.quicksum(10 * r[i] for i in N), # Strafkosten für Non-regular driver Nutzung
        GRB.MAXIMIZE
    )

    # 3. Nebenbedingungen
    # Maschinenfluss-Balance
    for m in M:
        for i in N_m[m]:
            model.addConstr(
                gp.quicksum(x[m, j, i] for j in P_mn[m,i]) == gp.quicksum(x[m, i, j] for j in S_mn[m, i]),
                name=f"machine_flow_balance_{m}_{i}"
            )

    
    # Arbeiterfluss-Balance
    for w in W:
        for i in N_w[w]:
            model.addConstr(
                gp.quicksum(y[w, j, i] for j in P_wn[w,i]) == gp.quicksum(y[w, i, j] for j in S_wn[w,i]),
                name=f"worker_flow_balance_{w}_{i}"
            )


    # Start- und Endknoten-Bedingungen
    for m in M:
        if (m,start) in S_mn:
            model.addConstr(
                gp.quicksum(x[m, start, j] for j in S_mn[m,start]) == 1,
                name=f"machine_start_constraint_{m}"
            )
    for w in W:
        if (w,start) in S_wn:
            model.addConstr(
                gp.quicksum(y[w, start, j] for j in S_wn[w,start]) == 1,
                name=f"worker_start_constraint_{w}"
        )


    # Source Sink Balance für Maschinen --> nicht mehr benötigt, da Start- und Endknoten-Bedingungen
    '''
    for m in M:
        if (m,start) in S_mn and (m,end) in P_mn:
            left_sum = gp.quicksum(x[m, start, j] for j in S_mn[m,start] if j != end)
            right_sum = gp.quicksum(x[m, i, end] for i in P_mn[m,end] if i != start)
            model.addConstr(left_sum == right_sum, name=f"machine_balance_{m}_start_end")
    '''

    # Source Sink Balance für Arbeiter --> nicht mehr benötigt, da Start- und Endknoten-Bedingungen
    '''
    for w in W:
        if (w,start) in S_wn and (w,end) in P_wn:
            left_sum = gp.quicksum(y[w, start, j] for j in S_wn[w,start] if j != end)
            right_sum = gp.quicksum(y[w, i, end] for i in P_wn[w,end] if i != start)
            model.addConstr(left_sum == right_sum, name=f"worker_balance_{w}_start_end")
    '''



    # Regelmäßige Fahrer - Nebenbedingung
    for m in M:
        for i in N_m[m]:
                model.addConstr(
                    gp.quicksum(x[m, i, j] for j in S_mn[m, i]) <= gp.quicksum(y[w, i, j] for w in W_m[m] if (w,i) in S_wn for j in S_wn[w, i]) + r[i],
                    name=f"regular_driver_constraint_{m}_{i}")

    
    # Baustellen-Erfüllung
    for c in C:
        for i in N_c[c]:
            model.addConstr(
                gp.quicksum(x[m, i, j] for m in M if (m,i) in S_mn for j in S_mn[m,i]) == u[c],
                name=f"machine_site_fulfillment_site{c}_order{i}"
            )
            model.addConstr(
                gp.quicksum(y[w, i, j] for w in W if (w,i) in S_wn for j in S_wn[w,i]) == u[c],
                name=f"worker_site_fulfillment_site{c}_order{i}"
            )


    # Nachschicht-Beschränkung --> Alte Variante der Nachtschicht-Beschränkung (eine andere Schicht muss innerhalb der nächsten X Tage folgen)
    '''
    for w in W:
        for t in T_range:
            if t <= T - S_Nmax:
                model.addConstr(
                    gp.quicksum(y[w, i ,j] for r in range(t, t + S_Nmax + 1) if r in D_r for j in D_r[r] if (w,j) in P_wn for i in P_wn[w, j]) >= 1,
                    name=f"night_shift_constraint_{w}_t{t}"
                )
    '''

    # Nachtschicht-Beschränkung --> Neue Variante der Nachtschicht-Beschränkung (maximal X Nachtschichten hintereinander, danach kann eine Pause folgen oder eine Tagesschicht)
    for w in W:
        for t in T_range:
            if t <= T - S_Nmax:
                model.addConstr(
                    gp.quicksum(y[w, i ,j] for t_ in range(t, t + S_Nmax + 1) if t_ in N_r for j in N_r[t_] if (w,j) in P_wn for i in P_wn[w, j]) <= S_Nmax,
                    name=f"night_shift_constraint_{w}_t{t}"
                )



    # Schichtanzahl-Beschränkung
    for w in W:
        for t in T_range:
            if t <= T - T_Smax:
                model.addConstr(
                    gp.quicksum(y[w, i, j] for t_ in range(t, t + T_Smax) if t_ in A_r for j in A_r[t_] if (w,j) in P_wn for i in P_wn[w, j]) <= S_max,
                    name=f"shift_number_constraint_{w}_t{t}"
                )

    # Arbeitszeit-Beschränkung
    for w in W:
        model.addConstr(
            gp.quicksum(t_o[i]*y[w, i, j] for i in N_w[w] for j in S_wn[w,i]) <= T_Wmax,
            name=f"work_time_constraint_{w}"
        )

    return model, x, y, r, u








if __name__ == "__main__":
    Run_MIP()