import gurobipy as gp
from gurobipy import GRB
import json
from pathlib import Path
import pandas as pd
from InputData import *
from OutputData import *
import time
from itertools import groupby


class UpperBound:
    
    def __init__(self, data, upper_bound):
        self.data = data
        self.model = None
        self.upper_bound = upper_bound

        # ========================
        # 1. Sets
        # ========================
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':
            self.M = []  # List of machine IDs
            self.N_m = {}  # Dictionary: Machine -> Order items
        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':
            self.W = []  # List of worker IDs
            self.N_w = {}  # Dictionary: Worker -> Order items
        if self.upper_bound == 'attachment' or self.upper_bound == "all":
            self.A = [] # List of attachment IDs
            self.N_a = {} # Dictionary: Attachment -> Order items
            self.K = set() # Set of all attachment types
        
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
        self.P_an = {}  # Predecessors for attachment order items
        self.S_an = {}  # Successors for attachment order items
        self.d_ij = []  # Distance matrix for machines (transport routes)
        self.d_wi = []  # Distance matrix for workers (work routes)
        self.q_ok = {}  # Dictionary: Order item -> Attachment types

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
        print("\n Preprocessing data for LP-Relaxation...")
        current_time = time.time()
        
        # ========================
        # 1. Process Machines
        # ========================
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':

            for machine in self.data.machines:
                self.M.append(machine.name)
                self.N_m[machine.name] = []
                for orderItem in self.data.order_items:
                    if orderItem.machine_type == machine.type:
                        self.N_m[machine.name].append(orderItem.id)

        # ========================
        # 2. Process Workers
        # ========================

        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':

            for worker in self.data.workers:
                self.W.append(worker.personal_number)
                self.N_w[worker.personal_number] = []
                for orderItem in self.data.order_items:
                    if not orderItem.worker_qualifications:  # Keine Qualifikationen erforderlich
                        self.N_w[worker.personal_number].append(orderItem.id)
                    elif set(orderItem.worker_qualifications).issubset(set(worker.qualifications)):  # Qualifikationen sind abgedeckt
                        self.N_w[worker.personal_number].append(orderItem.id)

        # ========================
        # 3. Process Attachments
        # ========================
        
        if self.upper_bound == 'attachment' or self.upper_bound == 'all':
            
            for attachment in self.data.attachments:
                self.A.append(attachment.id)
                self.N_a[attachment.id] = []
                for orderItem in self.data.order_items:
                    if attachment.type in orderItem.equipment_types:
                        self.N_a[attachment.id].append(orderItem.id)

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


            if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':

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
        
        # Order items and attachment types
        if self.upper_bound == 'attachment' or self.upper_bound == 'all':
            for order_item in self.data.order_items:
                self.q_ok[order_item.id] = dict()
                for equipment in order_item.equipment_types:
                    if equipment not in self.q_ok[order_item.id]:
                        self.q_ok[order_item.id][equipment] = 0
                    self.q_ok[order_item.id][equipment] += 1

                    
                    self.K.add(equipment)
            
                
                
        # ========================
        # 5. Process Transport Routes
        # ========================

        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':
            for i in self.data.order_items:
                row = []
                for j in self.data.order_items:
                    a = next((k for k, v in self.N_c.items() if i.id in v))
                    b = next((k for k, v in self.N_c.items() if j.id in v))
                    row.append(self.data.transport_routes[a][b])
                self.d_ij.append(row)

        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':
            for i in self.data.workers:
                row = []
                for j in self.data.order_items:
                    a = next((k for k, v in self.N_c.items() if j.id in v))
                    row.append(self.data.work_routes[i.personal_number][a])
                self.d_wi.append(row)




        # ========================
        # 6. Calculate Predecessors and Successors
        # ========================

        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':
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

        if self.upper_bound == 'attachment' or self.upper_bound == "all":
            for a in self.A:
                for n in self.N_a[a]:
                    if (a, self.start) not in self.P_an:
                        self.P_an[a, self.start] = []
                        self.S_an[a, self.start] = [self.end]
                    if (a, self.end) not in self.P_an:
                        self.P_an[a, self.end] = []
                        self.S_an[a, self.end] = [self.start]

                    self.P_an[a, n] = [self.start]
                    self.S_an[a, self.start].append(n)
                    self.P_an[a, self.end].append(n)
                    self.S_an[a, n] = [self.end]

                    for i in self.N_a[a]:
                        if n != i:
                            start_time_n = self.O_t_start_inverted[n]
                            end_time_n = self.O_t_end_inverted[n]
                            start_time_i = self.O_t_start_inverted[i]
                            end_time_i = self.O_t_end_inverted[i]

                            if start_time_n >= end_time_i + self.d_ij[i][n] / self.TRANSPORT_SPEED:
                                self.P_an[a, n].append(i)

                            if start_time_i > end_time_n + self.d_ij[n][i] / self.TRANSPORT_SPEED:
                                self.S_an[a, n].append(i)
        

        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':
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
        


        # ========================
        # 8. Order Item Durations
        # ========================
        self.t_o = [orderItem.duration for orderItem in self.data.order_items]

        elapsed_time = time.time() - current_time
        print(f" Data preprocessed successfully after {elapsed_time:.2f} seconds")


    def create_optimization_model(self):
        """Create and configure the Gurobi optimization model."""


        current_time = time.time()
        print("\n Creating LP-Relaxation...")
        self.model = gp.Model("Flow_Formulation")

        
    
        self.model.setParam('OutputFlag', 0)



        self.model.setParam('TimeLimit', 3600)

        # ========================
        # 1. Create Variables
        # ========================

        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':

            # Machine flow variabless
            indices_1 = [(m, i, j) for m in self.M for i in self.N_m[m] for j in self.N_m[m]]  # (m, i, j)
            indices_2 = [(m, self.start, j) for m in self.M for j in self.N_m[m]]  # (m, start, j)
            indices_3 = [(m, i, self.end) for m in self.M for i in self.N_m[m]]  # (m, i, end)
            indices_4 = [(m, self.start, self.end) for m in self.M]  # (m, start, end)
            all_indices = indices_1 + indices_2 + indices_3 + indices_4
            x = self.model.addVars(all_indices, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="x")

        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':

            # Worker flow variables
            indices_1 = [(w, i, j) for w in self.W for i in self.N_w[w] for j in self.N_w[w]]  # (w, i, j)
            indices_2 = [(w, self.start, j) for w in self.W for j in self.N_w[w]]  # (w, start, j)
            indices_3 = [(w, i, self.end) for w in self.W for i in self.N_w[w]]  # (w, i, end)
            indices_4 = [(w, self.start, self.end) for w in self.W]  # (w, start, end)
            all_indices = indices_1 + indices_2 + indices_3 + indices_4
            y = self.model.addVars(all_indices, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="y")

        if self.upper_bound == 'attachment' or self.upper_bound == "all":

            # Attachment flow variables
            indices_1 = [(a, i, j) for a in self.A for i in self.N_a[a] for j in self.N_a[a]]
            indices_2 = [(a, self.start, j) for a in self.A for j in self.N_a[a]]
            indices_3 = [(a, i, self.end) for a in self.A for i in self.N_a[a]]
            indices_4 = [(a, self.start, self.end) for a in self.A]
            all_indices = indices_1 + indices_2 + indices_3 + indices_4
            z = self.model.addVars(all_indices, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="z")

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
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':
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


        if self.upper_bound == 'attachment' or self.upper_bound == "all":
            # Attachment flow balance constraints
            for a in self.A:
                for i in self.N_a[a]:
                    self.model.addConstr(
                        gp.quicksum(z[a, j, i] for j in self.P_an[a, i]) ==
                        gp.quicksum(z[a, i, j] for j in self.S_an[a, i]),
                        name=f"attachment_flow_balance_{a}_{i}"
                    )

            # Start and end node constraints for attachments
            for a in self.A:
                if (a, self.start) in self.S_an:
                    self.model.addConstr(
                        gp.quicksum(z[a, self.start, j] for j in self.S_an[a, self.start]) == 1,
                        name=f"attachment_start_constraint_{a}"
                    )


        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':
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

        if self.upper_bound == 'attachment':
            for c in self.C:
                for i in self.N_c[c]:
                    for k in self.K:
                        if k in self.q_ok[i]:
                            self.model.addConstr(
                                gp.quicksum(z[a, i, j] for a in self.A if (a, i) in self.S_an for j in self.S_an[a, i]) == self.q_ok[i][k] * u[c],
                                name=f"attachment_site_fulfillment_site{c}_order{i}_type{k}"
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


        if self.upper_bound == 'all':
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
                    for k in self.K:
                        if k in self.q_ok[i]:
                            self.model.addConstr(
                                gp.quicksum(z[a, i, j] for a in self.A if (a, i) in self.S_an for j in self.S_an[a, i]) == self.q_ok[i][k] * u[c],
                                name=f"attachment_site_fulfillment_site{c}_order{i}_type{k}"
                            )
            
        
        
        elapsed_time = time.time() - current_time
        print(f" Model created successfully after {elapsed_time:.2f} seconds")


    def solve_model(self):
        """Solve the optimization model."""
        print("\n Solving LP-Relaxation...")
        self.model.optimize()

        print(" LP-Relaxation solved after {:.2f} seconds".format(self.model.Runtime))
   
            
        


    def execute(self):
        """Run the full optimization workflow."""

        self.preprocess_data()
        self.create_optimization_model()
        self.solve_model()

        if self.model.SolCount > 0:
            objective_value = self.model.objVal
            gap = self.model.MIPGap if self.model.status == GRB.TIME_LIMIT else 0
        else:
            objective_value = None
            gap = None

        return objective_value, self.model.Runtime, self.model.status, gap



        