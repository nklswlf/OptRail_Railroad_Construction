import gurobipy as gp
from gurobipy import GRB
import json
from pathlib import Path
import pandas as pd
from InputData import *
from OutputData import *
from time import time
from itertools import groupby


class UpperBound:
    
    def __init__(self, data, upper_bound):
        self.data = data
        self.model = None
        self.upper_bound = upper_bound

        # ========================
        # 1. Sets
        # ========================
        if self.upper_bound == 'machine' or self.upper_bound == "both":
            self.M = []  # List of machine IDs
            self.N_m = {}  # Dictionary: Machine -> Order items
        if self.upper_bound == 'worker' or self.upper_bound == "both":
            self.W = []  # List of worker IDs
            self.N_w = {}  # Dictionary: Worker -> Order items
        
        self.N = []  # List of order item IDs
        self.C = []  # List of site IDs
        self.N_c = {}  # Dictionary: Site -> Order items

        # ========================
        # 2. Parameters
        # ========================
        self.start_date = None  # Start date of the planning horizon
        self.end_date = None # End date of the planning horizon
        self.O_t = {}  # Dictionary: Day -> Order items (start)
        self.D_r = {}  # Dictionary: Day -> Day shifts
        self.N_r = {}  # Dictionary: Day -> Night shifts
        self.A_r = {}  # Dictionary: Day -> All shifts
        self.O_t_start = {}  # Dictionary: Start times of order items
        self.O_t_end = {}  # Dictionary: End times of order items
        self.O_t_start_inverted = {}  # Dictionary: Order item -> Start time
        self.O_t_end_inverted = {}  # Dictionary: Order item -> End time

        # ========================
        # 3. Predecessors, Successors and Distances
        # ========================
        self.P_mn = {}  # Predecessors for machine order items
        self.S_mn = {}  # Successors for machine order items
        self.P_wn = {}  # Predecessors for worker order items
        self.S_wn = {}  # Successors for worker order items
        self.d_ij = []  # Distance matrix for machines (transport routes)
        self.d_wi = []  # Distance matrix for workers (work routes)

        # ========================
        # 4. Time and Range
        # ========================
        self.T_range = []  # List of all days in the planning horizon
        self.T = 0  # Planning horizon (number of days)
        self.start = "start" # Start node which is indexed as len(N)
        self.end = "end" # End node which is indexed as len(N) + 1

        # ========================
        # 5. Occupational Safety Constants
        # ========================
        self.S_Nmax = data._max_consecutive_night_shifts
        self.S_max = data._max_shifts_in_time_period
        self.T_Smax = data._time_period_for_max_shifts.days
        self.T_Wmax = data._max_working_hours

        # ========================
        # 6. Other Constants
        # ========================
        self.SECONDS_IN_A_DAY = data._seconds_a_day
        self.TRANSPORT_SPEED = data._transport_speed_kmh * 24  # Machine transport speed (km/day)
        self.TIME_BETWEEN_SHIFTS = data._hours_between_shifts / 24  # Rest period between shifts (in days)

        
    def preprocess_data(self):
        """Preprocess the input data for optimization."""
        print("\nPreprocessing data...")
        current_time = time()
        
        # ========================
        # 1. Process Machines
        # ========================
        if self.upper_bound == 'machine' or self.upper_bound == "both":

            for machine in self.data.machines:
                self.M.append(machine.name)
                self.N_m[machine.name] = []
                for orderItem in self.data.order_items:
                    if orderItem.machine_type == machine.type:
                        self.N_m[machine.name].append(orderItem.id)

        # ========================
        # 2. Process Workers
        # ========================

        if self.upper_bound == 'worker' or self.upper_bound == "both":

            for worker in self.data.workers:
                self.W.append(worker.personal_number)
                self.N_w[worker.personal_number] = []
                for orderItem in self.data.order_items:
                    if not orderItem.worker_qualifications:  # Keine Qualifikationen erforderlich
                        self.N_w[worker.personal_number].append(orderItem.id)
                    elif set(orderItem.worker_qualifications).issubset(set(worker.qualifications)):  # Qualifikationen sind abgedeckt
                        self.N_w[worker.personal_number].append(orderItem.id)

        # ========================
        # 3. Process Orders
        # ========================
        for order in self.data.orders:
            self.C.append(order.site_number)
            self.N_c[order.site_number] = [int(item_id) for item_id in order.order_item_ids]

        # ========================
        # 4. Process Order Items
        # ========================
        self.N = [orderItem.id for orderItem in self.data.order_items]
        self.start_date = self.data.start_date
        self.end_date = self.data.end_date

        for orderItem in self.data.order_items:

            orderID = orderItem.id
            delta_start = (orderItem.start_time - self.start_date)
            t_start = delta_start.total_seconds() / self.SECONDS_IN_A_DAY
            t_start_int = int(t_start)


            # Start times
            if t_start not in self.O_t_start:
                self.O_t_start[t_start] = []
            self.O_t_start[t_start].append(orderID)
            self.O_t_start_inverted[orderID] = t_start

            # End times
            delta_end = (orderItem.end_time - self.start_date)
            t_end = delta_end.total_seconds() / self.SECONDS_IN_A_DAY
            if t_end not in self.O_t_end:
                self.O_t_end[t_end] = []
            self.O_t_end[t_end].append(orderID)
            self.O_t_end_inverted[orderID] = t_end


        if self.upper_bound == 'worker' or self.upper_bound == "both":

            for orderItem in self.data.order_items:

                # O_t: Order items grouped by day
                if t_start_int not in self.O_t:
                    self.O_t[t_start_int] = []
                self.O_t[t_start_int].append(orderID)

                # D_r: Day shifts grouped by day
                if t_start_int not in self.D_r:
                    self.D_r[t_start_int] = []
                if orderItem.start_time.hour <= self.data._day_and_night_shift_boundary:
                    self.D_r[t_start_int].append(orderID)

                # N_r: Night shifts grouped by day
                if t_start_int not in self.N_r:
                    self.N_r[t_start_int] = []
                if orderItem.start_time.hour > self.data._day_and_night_shift_boundary:
                    self.N_r[t_start_int].append(orderID)

                # A_r: All shifts grouped by day
                if t_start_int not in self.A_r:
                    self.A_r[t_start_int] = []
                self.A_r[t_start_int].append(orderID)

                

        # ========================
        # 5. Process Transport Routes
        # ========================

        if self.upper_bound == 'machine' or self.upper_bound == "both":
            for i in self.data.order_items:
                row = []
                for j in self.data.order_items:
                    a = next((k for k, v in self.N_c.items() if i.id in v))
                    b = next((k for k, v in self.N_c.items() if j.id in v))
                    row.append(self.data.transport_routes[a][b])
                self.d_ij.append(row)

        if self.upper_bound == 'worker' or self.upper_bound == "both":
            for i in self.data.workers:
                row = []
                for j in self.data.order_items:
                    a = next((k for k, v in self.N_c.items() if j.id in v))
                    row.append(self.data.work_routes[i.personal_number][a])
                self.d_wi.append(row)




        # ========================
        # 6. Calculate Predecessors and Successors
        # ========================

        if self.upper_bound == 'machine' or self.upper_bound == "both":
            for m in self.M:
                for n in self.N_m[m]:
                    if (m, self.start) not in self.P_mn:
                        self.P_mn[m, self.start] = []
                        self.S_mn[m, self.start] = [self.end]
                    if (m, self.end) not in self.P_mn:
                        self.P_mn[m, self.end] = []
                        self.S_mn[m, self.end] = [self.start]

                    self.P_mn[m, n] = [self.start]
                    self.S_mn[m, self.start].append(n)
                    self.P_mn[m, self.end].append(n)
                    self.S_mn[m, n] = [self.end]

                    for i in self.N_m[m]:
                        if n != i:
                            start_time_n = self.O_t_start_inverted[n]
                            end_time_n = self.O_t_end_inverted[n]
                            start_time_i = self.O_t_start_inverted[i]
                            end_time_i = self.O_t_end_inverted[i]

                            if start_time_n >= end_time_i + self.d_ij[i][n] / self.TRANSPORT_SPEED:
                                self.P_mn[m, n].append(i)

                            if start_time_i > end_time_n + self.d_ij[n][i] / self.TRANSPORT_SPEED:
                                self.S_mn[m, n].append(i)

        if self.upper_bound == 'worker' or self.upper_bound == "both":
            for w in self.W:
                for n in self.N_w[w]:
                    if (w, self.start) not in self.P_wn:
                        self.P_wn[w, self.start] = []
                        self.S_wn[w, self.start] = [self.end]
                    if (w, self.end) not in self.P_wn:
                        self.P_wn[w, self.end] = []
                        self.S_wn[w, self.end] = [self.start]

                    self.P_wn[w, n] = [self.start]
                    self.S_wn[w, self.start].append(n)
                    self.P_wn[w, self.end].append(n)
                    self.S_wn[w, n] = [self.end]

                    for i in self.N_w[w]:
                        if n != i:
                            start_time_n = self.O_t_start_inverted[n]
                            end_time_n = self.O_t_end_inverted[n]
                            start_time_i = self.O_t_start_inverted[i]
                            end_time_i = self.O_t_end_inverted[i]

                            if start_time_n >= end_time_i + self.TIME_BETWEEN_SHIFTS:
                                self.P_wn[w, n].append(i)

                            if start_time_i >= end_time_n + self.TIME_BETWEEN_SHIFTS:
                                self.S_wn[w, n].append(i)

        # ========================
        # 7. Time Range and Planning Horizon
        # ========================
        day_difference = self.end_date - self.start_date
        self.T_range = list(range(day_difference.days + 1))
        self.T = day_difference.days + 1
        
        '''
        end_date_adjusted = self.start_date
        for orderItem in self.data.order_items:
            if end_date_adjusted < orderItem.start_time:
                end_date_adjusted = orderItem.start_time
        self.T = (end_date_adjusted - self.start_date).days + 1
        '''

        # ========================
        # 8. Order Item Durations
        # ========================
        self.t_o = [orderItem.duration for orderItem in self.data.order_items]

        elapsed_time = time() - current_time
        print("Data preprocessed successfully.")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")


    def create_optimization_model(self):
        """Create and configure the Gurobi optimization model."""

        self.time_limit = 10800
        thread_limit = 16


        current_time = time()
        print("\nCreating optimization model...")
        self.model = gp.Model("Flow_Formulation")

        
        #self.model.setParam('NodefileStart', 0)  # Nutze die Festplatte, wenn mehr als 0.5 GB Speicher benötigt werden
        #self.model.setParam('NodefileDir', '//Volumes/Daten/Gurobi')  # Verzeichnis für temporäre Dateien
        #self.model.setParam('Threads', 1)  # Reduziere die Anzahl der Threads, um Speicheranforderungen zu minimieren
        #self.model.setParam('MIPFocus', 1)  # Beispiel für zusätzlichen Parameter
        #self.model.setParam('TimeLimit', 300)  # Maximale Rechenzeit auf 300 Sekunden begrenzen
        

        parent_folder = self.data._parent_folder
        solution_path = Path.cwd().parent / "Data" / "Upper_Bound" / parent_folder / self.data.instance / self.upper_bound
        solution_path.mkdir(parents=True, exist_ok=True)
        

        self.model.setParam("Threads", thread_limit)





        # ========================
        # 1. Create Variables
        # ========================

        if self.upper_bound == 'machine' or self.upper_bound == "both":

            # Machine flow variabless
            indices_1 = [(m, i, j) for m in self.M for i in self.N_m[m] for j in self.N_m[m]]  # (m, i, j)
            indices_2 = [(m, self.start, j) for m in self.M for j in self.N_m[m]]  # (m, start, j)
            indices_3 = [(m, i, self.end) for m in self.M for i in self.N_m[m]]  # (m, i, end)
            indices_4 = [(m, self.start, self.end) for m in self.M]  # (m, start, end)
            all_indices = indices_1 + indices_2 + indices_3 + indices_4
            x = self.model.addVars(all_indices, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="x")

        if self.upper_bound == 'worker' or self.upper_bound == "both":

            # Worker flow variables
            indices_1 = [(w, i, j) for w in self.W for i in self.N_w[w] for j in self.N_w[w]]  # (w, i, j)
            indices_2 = [(w, self.start, j) for w in self.W for j in self.N_w[w]]  # (w, start, j)
            indices_3 = [(w, i, self.end) for w in self.W for i in self.N_w[w]]  # (w, i, end)
            indices_4 = [(w, self.start, self.end) for w in self.W]  # (w, start, end)
            all_indices = indices_1 + indices_2 + indices_3 + indices_4
            y = self.model.addVars(all_indices, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="y")


        # Site completion variables
        u = self.model.addVars(self.C, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="u")

        # ========================
        # 2. Set Objective Function
        # ========================


        # Definition of the objective criteria/functions
        self.construction_fulfillment = gp.quicksum(u[c] for c in self.C)


        self.model.setObjective(self.construction_fulfillment, GRB.MAXIMIZE)




        # ========================
        # 3. Add Constraints
        # ========================
        if self.upper_bound == 'machine' or self.upper_bound == "both":
            # Machine flow balance constraints
            for m in self.M:
                for i in self.N_m[m]:
                    self.model.addConstr(
                        gp.quicksum(x[m, j, i] for j in self.P_mn[m, i]) ==
                        gp.quicksum(x[m, i, j] for j in self.S_mn[m, i]),
                        name=f"machine_flow_balance_{m}_{i}"
                    )


            # Start and end node constraints for machines
            for m in self.M:
                if (m, self.start) in self.S_mn:
                    self.model.addConstr(
                        gp.quicksum(x[m, self.start, j] for j in self.S_mn[m, self.start]) == 1,
                        name=f"machine_start_constraint_{m}"
                    )


        if self.upper_bound == 'worker' or self.upper_bound == "both":
   
            # Worker flow balance constraints
            for w in self.W:
                for i in self.N_w[w]:
                    self.model.addConstr(
                        gp.quicksum(y[w, j, i] for j in self.P_wn[w, i]) ==
                        gp.quicksum(y[w, i, j] for j in self.S_wn[w, i]),
                        name=f"worker_flow_balance_{w}_{i}"
                    )

            # Start and end node constraints for workers
            for w in self.W:
                if (w, self.start) in self.S_wn:
                    self.model.addConstr(
                        gp.quicksum(y[w, self.start, j] for j in self.S_wn[w, self.start]) == 1,
                        name=f"worker_start_constraint_{w}"
                    )



            # Total working time constraints
            for w in self.W:
                self.model.addConstr(
                    gp.quicksum(self.t_o[i] * y[w, i, j] for i in self.N_w[w] for j in self.S_wn[w, i]) <= self.T_Wmax,
                    name=f"work_time_constraint_{w}"
                )

            # Night shift constraints
            for w in self.W:
                for t in self.T_range:
                    if t <= self.T - self.S_Nmax:
                        self.model.addConstr(
                            gp.quicksum(
                                y[w, i, j] for t_ in range(t, t + self.S_Nmax + 1) if t_ in self.N_r for j in self.N_r[t_]
                                if (w, j) in self.P_wn for i in self.P_wn[w, j]
                            ) <= self.S_Nmax,
                            name=f"night_shift_constraint_{w}_t{t}"
                        )

            # Shift count constraints
            for w in self.W:
                for t in self.T_range:
                    if t <= self.T - self.T_Smax:
                        self.model.addConstr(
                            gp.quicksum(
                                y[w, i, j] for t_ in range(t, t + self.T_Smax) if t_ in self.A_r for j in self.A_r[t_]
                                if (w, j) in self.P_wn for i in self.P_wn[w, j]
                            ) <= self.S_max,
                            name=f"shift_number_constraint_{w}_t{t}"
                        )





        # Site completion constraints
        if self.upper_bound == 'machine':
            for c in self.C:
                for i in self.N_c[c]:
                    self.model.addConstr(
                        gp.quicksum(x[m, i, j] for m in self.M if (m, i) in self.S_mn for j in self.S_mn[m, i]) == u[c],
                        name=f"machine_site_fulfillment_site{c}_order{i}"
                    )

        if self.upper_bound == 'worker':         
            for c in self.C:
                for i in self.N_c[c]:
                    self.model.addConstr(
                        gp.quicksum(y[w, i, j] for w in self.W if (w, i) in self.S_wn for j in self.S_wn[w, i]) == u[c],
                        name=f"worker_site_fulfillment_site{c}_order{i}"
                    )

        if self.upper_bound == 'both':
            for c in self.C:
                for i in self.N_c[c]:
                    self.model.addConstr(
                        gp.quicksum(x[m, i, j] for m in self.M if (m, i) in self.S_mn for j in self.S_mn[m, i]) == u[c],
                        name=f"machine_site_fulfillment_site{c}_order{i}"
                    )
                    self.model.addConstr(
                        gp.quicksum(y[w, i, j] for w in self.W if (w, i) in self.S_wn for j in self.S_wn[w, i]) == u[c],
                        name=f"worker_site_fulfillment_site{c}_order{i}"
                    )

        
        
        elapsed_time = time() - current_time
        print("Optimization model created successfully.")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")


    def solve_model(self):
        """Solve the optimization model."""
        print("\nSolving the model...")
        self.model.optimize()

        print("Time elapsed: {:.2f} seconds".format(self.model.Runtime))


        if self.model.status == GRB.INFEASIBLE:
            return False
        elif self.model.status == GRB.OPTIMAL:
            return True
        elif self.model.status == GRB.TIME_LIMIT:
            if self.model.SolCount > 0:
                return "solution_with_gap"
            else:
                return "time_limit_exceeded"
   
            


    def postprocess_results(self):
        """Extract and display results after model optimization."""
        print("\nPostprocessing results...")



        # ========================
        # 1. Site Fulfillment Results
        # ========================
        self.site_fulfillment = {}
        for c in self.C:
            self.site_fulfillment[c] = False
            if self.model.getVarByName(f"u[{c}]").x > 0.5:
                self.site_fulfillment[c] = True

        self.sum_finished_sites = round(sum(self.model.getVarByName(f"u[{c}]").x for c in self.C))
        self.sum_total_sites = len(self.C)
        if self.upper_bound == 'machine' or self.upper_bound == "both":
            self.sum_finished_order_items = round(sum(self.model.getVarByName(f"x[{m},{i},{j}]").x for m in self.M for i in self.N_m[m] for j in self.N_m[m]) + sum(self.model.getVarByName(f"x[{m},{i},{self.end}]").x for m in self.M for i in self.N_m[m]))
        if self.upper_bound == 'worker' or self.upper_bound == "both":
            self.sum_finished_order_items = round(sum(self.model.getVarByName(f"y[{w},{i},{j}]").x for w in self.W for i in self.N_w[w] for j in self.N_w[w]) + sum(self.model.getVarByName(f"y[{w},{i},end]").x for w in self.W for i in self.N_w[w]))
        
        self.sum_order_items = len(self.N)


        # ========================
        # 3. Worker and Machine Utilization
        # ========================
        
        if self.upper_bound == 'machine' or self.upper_bound == "both":


            number_of_machines = len(self.M)

            self.number_of_used_machines = round(sum(self.model.getVarByName(f"x[{m},{self.start},{j}]").x for m in self.M for j in self.N_m[m]))

            self.distance_machine = {}
            for m in self.M:
                self.distance_machine[m] = {"Distance": 0, "Utilization": False}
                for i in self.N_m[m]:
                    for j in self.N_m[m]:
                        if i != j and self.model.getVarByName(f"x[{m},{i},{j}]").x > 0.5:
                            self.distance_machine[m]["Distance"] += self.d_ij[i][j]
                            self.distance_machine[m]["Utilization"] = True


            self.total_distance_machine = sum(self.distance_machine[m]["Distance"] for m in self.M)
        

        if self.upper_bound == 'worker' or self.upper_bound == "both":

            number_of_workers = len(self.W)
            self.number_of_used_worker = round(sum(self.model.getVarByName(f"y[{w},{self.start},{j}]").x for w in self.W for j in self.N_w[w]))
            
            self.distance_worker = {}
            for w in self.W:
                self.distance_worker[w] = 0
                for i in self.N_w[w]:
                    for j in self.N_w[w]:
                        if i != j and self.model.getVarByName(f"y[{w},{i},{j}]").x > 0.5:
                            self.distance_worker[w] += 2 * self.d_wi[w][i]
                    if self.model.getVarByName(f"y[{w},{i},end]").x > 0.5:
                        self.distance_worker[w] += 2 * self.d_wi[w][i]

            self.total_distance_worker = sum(self.distance_worker.values())


        # ========================
        # 4. Working Hours of Workers
        # ========================

            self.working_hours = {}
            for w in self.W:
                self.working_hours[w] = 0
                for i in self.N_w[w]:
                    for j in self.N_w[w]:
                        if i != j and self.model.getVarByName(f"y[{w},{i},{j}]").x > 0.5:
                            self.working_hours[w] += self.t_o[i]

                    if self.model.getVarByName(f"y[{w},{i},end]").x > 0.5:
                        self.working_hours[w] += self.t_o[i]
                        

            self.total_working_hours = sum(self.working_hours.values())



        # ========================
        # 5. Create DataFrames
        # ========================
        df_site = pd.DataFrame.from_dict(self.site_fulfillment, columns=["Fulfilled"], orient="index")

        if self.upper_bound == 'machine' or self.upper_bound == "both":
            df_transport = pd.DataFrame.from_dict(self.distance_machine, orient="index")
        
        if self.upper_bound == 'worker' or self.upper_bound == "both":
            df_worker_transport = pd.DataFrame.from_dict(self.distance_worker, columns=["Distance"], orient="index")
            df_working_hours = pd.DataFrame.from_dict(self.working_hours, columns=["Working Hours"], orient="index")

        # ========================
        # 6. Display Results
        # ========================

        if self.upper_bound == 'machine' or self.upper_bound == "both":

            print("\nTransport Distance:")
            print(df_transport)
            print(f"Total Transport Distance: {self.total_distance_machine}")
            print(f"\nNumber of used machines: {int(self.number_of_used_machines)} / {number_of_machines}")
        if self.upper_bound == 'worker' or self.upper_bound == "both":
            print("\nWork Distance:")
            print(df_worker_transport)
            print(f"Total Work Distance: {self.total_distance_worker}")
            print("\nWorking Hours:")
            print(df_working_hours)
            print(f"Total Working Hours: {self.total_working_hours}")
            print(f"Number of used workers: {int(self.number_of_used_worker)} / {number_of_workers}\n")
        
        print("\nSite Fulfillment:")
        print(df_site)
        print(f"\nNumber of fulfilled sites: {int(self.sum_finished_sites)} / {self.sum_total_sites}")
        print(f"Number of fulfilled order items: {int(self.sum_finished_order_items)} / {self.sum_order_items}")


        
        



    def time_limit_exceeded(self, reason):
        # ========================
        # 1. Save a file that indicates that the time limit was exceeded
        # ========================

        parent_folder = self.data._parent_folder
        solution_path = Path.cwd().parent / "Data" / "Solution_math_model" / parent_folder / self.data.instance / f"{self.number_of_objectives}_Objectives" / self.objective_strategy
        solution_path.mkdir(parents=True, exist_ok=True)
        
        if reason == "time_limit_exceeded":
            output_filename = solution_path / f"TIME_{self.data.instance_filename}"
            with open(output_filename, "w") as output_file:
                output_file.write(f"No solution found within the time limit of {self.time_limit} seconds.")

        elif reason == "solution_with_gap":           
            output_filename = solution_path / f"GAP_{self.data.instance_filename}"
            with open(output_filename, "w") as output_file:
                output_file.write(f"Solution found within the time limit of {self.time_limit} seconds, but with a gap.")


    def execute(self):
        """Run the full optimization workflow."""
        

        self.preprocess_data()
        self.create_optimization_model()
        feasible = self.solve_model()

        if not feasible:
            print("Model is infeasible.")
            return None, None
        
        #self.postprocess_results()

        objective_value = self.model.objVal
        return objective_value



        