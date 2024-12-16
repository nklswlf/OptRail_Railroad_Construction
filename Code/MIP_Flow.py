import gurobipy as gp
from gurobipy import GRB
import json
from pathlib import Path
import pandas as pd
from InputData import *
from OutputData import *
from time import time
from itertools import groupby


class FlowFormulation:
    
    def __init__(self, data, objective_strategy, paretto_attribute = None, pareto_construction = None):
        self.data = data
        self.model = None
        self.objective_strategy = objective_strategy
        self.pareto_attribut = paretto_attribute
        self.pareto_construction = pareto_construction

        # ========================
        # 1. Sets
        # ========================
        self.M = []  # List of machine IDs
        self.W_m = {}  # Dictionary: Regular drivers for machines
        self.N_m = {}  # Dictionary: Machine -> Order items
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
        self.S_Nmax = data._consecutive_night_shifts
        self.S_max = data._max_shifts_in_time_period
        self.T_Smax = data._time_period_for_max_shifts
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
        for machine in self.data.machines:
            self.M.append(machine.name)
            self.W_m[machine.name] = [int(driver) for driver in machine.default_drivers]
            self.N_m[machine.name] = []
            for orderItem in self.data.order_items:
                if orderItem.machine_type == machine.type:
                    self.N_m[machine.name].append(orderItem.id)

        # ========================
        # 2. Process Workers
        # ========================
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

        # ========================
        # 5. Process Transport Routes
        # ========================
        for i in self.data.order_items:
            row = []
            for j in self.data.order_items:
                a = next((k for k, v in self.N_c.items() if i.id in v))
                b = next((k for k, v in self.N_c.items() if j.id in v))
                row.append(self.data.transport_routes[a][b])
            self.d_ij.append(row)

        for i in self.data.workers:
            row = []
            for j in self.data.order_items:
                a = next((k for k, v in self.N_c.items() if j.id in v))
                row.append(self.data.work_routes[i.personal_number][a])
            self.d_wi.append(row)

        # ========================
        # 6. Calculate Predecessors and Successors
        # ========================

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

        current_time = time()
        print("\nCreating optimization model...")
        self.model = gp.Model("Flow_Formulation")

        
        #self.model.setParam('NodefileStart', 0)  # Nutze die Festplatte, wenn mehr als 0.5 GB Speicher benötigt werden
        #self.model.setParam('NodefileDir', '//Volumes/Daten/Gurobi')  # Verzeichnis für temporäre Dateien
        #self.model.setParam('Threads', 1)  # Reduziere die Anzahl der Threads, um Speicheranforderungen zu minimieren
        #self.model.setParam('MIPFocus', 1)  # Beispiel für zusätzlichen Parameter
        #self.model.setParam('TimeLimit', 300)  # Maximale Rechenzeit auf 300 Sekunden begrenzen



        # ========================
        # 1. Create Variables
        # ========================
        # Machine flow variables
        indices_1 = [(m, i, j) for m in self.M for i in self.N_m[m] for j in self.N_m[m]]  # (m, i, j)
        indices_2 = [(m, self.start, j) for m in self.M for j in self.N_m[m]]  # (m, start, j)
        indices_3 = [(m, i, self.end) for m in self.M for i in self.N_m[m]]  # (m, i, end)
        indices_4 = [(m, self.start, self.end) for m in self.M]  # (m, start, end)
        all_indices = indices_1 + indices_2 + indices_3 + indices_4
        x = self.model.addVars(all_indices, vtype=GRB.BINARY, name="x")

        # Worker flow variables
        indices_1 = [(w, i, j) for w in self.W for i in self.N_w[w] for j in self.N_w[w]]  # (w, i, j)
        indices_2 = [(w, self.start, j) for w in self.W for j in self.N_w[w]]  # (w, start, j)
        indices_3 = [(w, i, self.end) for w in self.W for i in self.N_w[w]]  # (w, i, end)
        indices_4 = [(w, self.start, self.end) for w in self.W]  # (w, start, end)
        all_indices = indices_1 + indices_2 + indices_3 + indices_4
        y = self.model.addVars(all_indices, vtype=GRB.BINARY, name="y")

        # Non-regular driver utilization variables
        r = self.model.addVars(self.N, vtype=GRB.BINARY, name="r")

        # Site completion variables
        u = self.model.addVars(self.C, vtype=GRB.BINARY, name="u")

        # ========================
        # 2. Set Objective Function
        # ========================


        # Definition of the objective criteria/functions
        self.construction_fulfillment = gp.quicksum(u[c] for c in self.C)
        self.machine_transport_distance = gp.quicksum(self.d_ij[i][j] * x[m, i, j] for m in self.M for i in self.N_m[m] for j in self.N_m[m])
        self.worker_work_distance = gp.quicksum(2 * self.d_wi[w][i] * y[w, i, j] for w in self.W for i in self.N_w[w] for j in (self.N_w[w] + [self.end]))
        self.machine_usage = gp.quicksum(x[m, self.start, j] for m in self.M for j in self.N_m[m])
        self.worker_usage = gp.quicksum(y[w, self.start, j] for w in self.W for j in self.N_w[w])
        self.non_regular_driver_usage = gp.quicksum(r[i] for i in self.N)


        if self.objective_strategy == "single":
            
            self.model.setObjectiveN(-self.construction_fulfillment, index=0, weight = self.data._construction_revenue)
            
            self.model.setObjectiveN(self.machine_transport_distance, index=1, weight = self.data._machine_transport_cost_per_km)
            self.model.setObjectiveN(self.worker_work_distance, index=2, weight = self.data._worker_travel_cost_per_km)
            self.model.setObjectiveN(self.machine_usage, index=3, weight = self.data._machine_fixed_cost)
            self.model.setObjectiveN(self.worker_usage, index=4, weight = self.data._worker_fixed_cost)
            self.model.setObjectiveN(self.non_regular_driver_usage, index=5, weight = self.data._penalty_cost_non_regular_driver)
            


        elif self.objective_strategy == "weighted":
            
            # Predefining elements for the weights
            len_unique_machine_types = list()
            
            for order in self.data.orders:
                machine_types = []
                for orderItemID in order.order_item_ids:
                    orderItemID = int(orderItemID)
                    orderItem = next((orderItem for orderItem in self.data.order_items if orderItem.id == orderItemID))

                    machine_types.append(orderItem.machine_type)

                unique_machine_types = list(set(machine_types))
                len_unique_machine_types.append(len(unique_machine_types))

            average_order_duration = sum(item.duration for item in self.data.order_items) / len(self.C)
            average_machine_types_per_site = sum(len_unique_machine_types) / len(self.C)
            average_transport_distance = sum(item for row in self.data.transport_routes for item in row if item != 0) / sum(1 for row in self.data.transport_routes for item in row if item != 0) 
            average_order_items_per_site = len(self.N) / len(self.C)
            target_max_share_of_non_regular_drivers = 0.3
            average_work_distance = sum(item for row in self.d_wi for item in row if item != 0) / sum(1 for row in self.d_wi for item in row if item != 0)
            

            # Defining relative factors for the weights
            prio_vector = [0.55864892, 0.14151739, 0.14151739, 0.0635508,  0.0635508,  0.03121471]

            factor_construction_fulfillment = prio_vector[0]
            factor_transport_distance = prio_vector[1]
            factor_work_distance = prio_vector[2]
            factor_machine_usage = prio_vector[3]
            factor_worker_usage = prio_vector[4]
            factor_non_regular_driver = prio_vector[5]
            
            


            # Calculating the absolute weights
            non_regular_driver_usage_weight = average_order_items_per_site * target_max_share_of_non_regular_drivers
            transport_distance_weight = average_machine_types_per_site * 2 * average_transport_distance
            work_distance_weight = average_order_items_per_site * 2 * average_work_distance
            machine_usage_weight = average_machine_types_per_site
            worker_usage_weight = (average_order_duration / self.T_Wmax)



            # Setting the objective function
            self.model.setObjectiveN(-self.construction_fulfillment, index=0, weight = 1 * factor_construction_fulfillment)
            
            self.model.setObjectiveN(self.machine_transport_distance, index=1, weight = (1/transport_distance_weight) * factor_transport_distance)
            self.model.setObjectiveN(self.worker_work_distance, index=2, weight = (1/work_distance_weight) * factor_work_distance)
            self.model.setObjectiveN(self.machine_usage, index=3, weight = (1/machine_usage_weight) * factor_machine_usage)
            self.model.setObjectiveN(self.worker_usage, index=4, weight = (1/worker_usage_weight) * factor_worker_usage)
            self.model.setObjectiveN(self.non_regular_driver_usage, index=5, weight = (1/non_regular_driver_usage_weight) * factor_non_regular_driver)


        elif self.objective_strategy == "hierarchical":

            self.model.setObjectiveN(-self.construction_fulfillment, index=0, priority = 6, reltol = 0, abstol = 0)


            self.model.setObjectiveN(self.non_regular_driver_usage, index=5, priority = 5, reltol = 0, abstol = 0)

            self.model.setObjectiveN(self.worker_work_distance, index=2, priority = 4, reltol = 0, abstol = 0)
            
            self.model.setObjectiveN(self.machine_transport_distance, index=1, priority = 3, reltol = 0, abstol = 0)

            self.model.setObjectiveN(self.machine_usage, index=3, priority = 2, reltol = 0, abstol = 0)
                    
            self.model.setObjectiveN(self.worker_usage, index=4, priority = 1, reltol = 0, abstol = 0)



        elif self.objective_strategy == "hierarchical_tolerance":


            if self.first_round == True:
                self.model.setObjectiveN(-self.construction_fulfillment, index=0, priority = 6, reltol = 0, abstol = 0)

            elif self.first_round == False:
                self.model.addConstr(self.construction_fulfillment == self.first_round_construction, name="ConstructionFulfillmentConstraint")

                self.model.setObjectiveN(self.non_regular_driver_usage, index=5, priority = 5, reltol = 0, abstol = 0)

                self.model.setObjectiveN(self.worker_work_distance, index=2, priority = 4, reltol = 0, abstol = 0)
                
                self.model.setObjectiveN(self.machine_transport_distance, index=1, priority = 3, reltol = 0, abstol = 0)
            
                self.model.setObjectiveN(self.machine_usage, index=3, priority = 2, reltol = 0, abstol = 0)
                            
                self.model.setObjectiveN(self.worker_usage, index=4, priority = 1, reltol = 0, abstol = 0)
            
            



        elif self.objective_strategy == "epsilon_constraint":

            # Main objective function: Construction fulfillment
            self.model.setObjective(self.construction_fulfillment,GRB.MAXIMIZE)

            # ε-Values
            self.epsilon_machine_use = round(len(self.M) * 0.7)
            self.epsilon_worker_use = round(len(self.W) * 0.7)
            
            self.epsilon_machine_distance = round((len(self.C)/self.epsilon_machine_use) * 500 * 0.7)
            self.epsilon_worker_distance = round((len(self.N)/self.epsilon_worker_use) * 200 * 0.7)
            
            self.epsilon_non_regular_driver_use = round(len(self.N) * 0.2)

            # ε-Constraints
            self.model.addConstr(self.machine_transport_distance <= self.epsilon_machine_distance,name= "EpsilonMachineDistanceConstraint")
            self.model.addConstr(self.worker_work_distance <= self.epsilon_worker_distance, name="EpsilonWorkerDistanceConstraint")
            self.model.addConstr(self.machine_usage <= self.epsilon_machine_use, name="EpsilonMachineUsageConstraint")
            self.model.addConstr(self.worker_usage <= self.epsilon_worker_use, name="EpsilonWorkerUsageConstraint")
            self.model.addConstr(self.non_regular_driver_usage <= self.epsilon_non_regular_driver_use, name="EpsilonPenaltyCostConstraint")


        elif self.objective_strategy == "pareto":
            
            self.model.addConstr(self.construction_fulfillment == self.pareto_construction, name="ConstructionFulfillmentConstraint")
            
            if self.pareto_attribut == "MachineTransportDistance":
                self.model.setObjectiveN(self.machine_transport_distance, index=0, priority = 2, weight = 1)
                self.model.setObjectiveN(self.worker_work_distance, index=1, priority = 1 , weight = 1)
            elif self.pareto_attribut == "WorkerWorkDistance":                
                self.model.setObjectiveN(self.worker_work_distance, index=0, weight = 1)            
            elif self.pareto_attribut == "MachineUsage":
                self.model.setObjectiveN(self.machine_usage, index=0, weight = 1)
            elif self.pareto_attribut == "WorkerUsage":    
                self.model.setObjectiveN(self.worker_usage, index=0, weight = 1)
            elif self.pareto_attribut == "NonRegularDriverUsage":    
                self.model.setObjectiveN(self.non_regular_driver_usage, index=0, weight = 1)




        # ========================
        # 3. Add Constraints
        # ========================
        # Machine flow balance constraints
        for m in self.M:
            for i in self.N_m[m]:
                self.model.addConstr(
                    gp.quicksum(x[m, j, i] for j in self.P_mn[m, i]) ==
                    gp.quicksum(x[m, i, j] for j in self.S_mn[m, i]),
                    name=f"machine_flow_balance_{m}_{i}"
                )

        # Worker flow balance constraints
        for w in self.W:
            for i in self.N_w[w]:
                self.model.addConstr(
                    gp.quicksum(y[w, j, i] for j in self.P_wn[w, i]) ==
                    gp.quicksum(y[w, i, j] for j in self.S_wn[w, i]),
                    name=f"worker_flow_balance_{w}_{i}"
                )

        # Start and end node constraints for machines
        for m in self.M:
            if (m, self.start) in self.S_mn:
                self.model.addConstr(
                    gp.quicksum(x[m, self.start, j] for j in self.S_mn[m, self.start]) == 1,
                    name=f"machine_start_constraint_{m}"
                )
        # Start and end node constraints for workers
        for w in self.W:
            if (w, self.start) in self.S_wn:
                self.model.addConstr(
                    gp.quicksum(y[w, self.start, j] for j in self.S_wn[w, self.start]) == 1,
                    name=f"worker_start_constraint_{w}"
                )

        # Regular driver constraints
        for m in self.M:
            for i in self.N_m[m]:
                self.model.addConstr(
                    gp.quicksum(x[m, i, j] for j in self.S_mn[m, i]) <=
                    gp.quicksum(y[w, i, j] for w in self.W_m[m] if (w, i) in self.S_wn for j in self.S_wn[w, i]) + r[i],
                    name=f"regular_driver_constraint_{m}_{i}"
                )

        # Site completion constraints
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

        # Total working time constraints
        for w in self.W:
            self.model.addConstr(
                gp.quicksum(self.t_o[i] * y[w, i, j] for i in self.N_w[w] for j in self.S_wn[w, i]) <= self.T_Wmax,
                name=f"work_time_constraint_{w}"
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
        
        return True
            


    def postprocess_results(self):
        """Extract and display results after model optimization."""
        print("\nPostprocessing results...")


        # ========================
        # 0. Objective Values
        # ========================

        self.objectives = []
        objective_names = [
            "Construction Fulfillment",
            "Machine Transport Distance",
            "Worker Work Distance",
            "Machine Usage",
            "Worker Usage",
            "Non-Regular Driver Usage"
        ]

        if self.objective_strategy in ["weighted", "hierarchical", "single"]:
            for i, name in enumerate(objective_names):
                value = self.model.getObjective(index=i).getValue()
                if value < 0:
                    value = value * -1              
                if name == "Construction Fulfillment" or name == "Non-Regular Driver Usage" or name == "Machine Usage" or name == "Worker Usage":
                    value = round(value)
                self.objectives.append({"Objective": name, "Value": value})


        elif self.objective_strategy == "hierarchical_tolerance":
            self.objectives.append({"Objective": "Construction Fulfillment", "Value": self.first_round_construction})
            
            for i, name in enumerate(objective_names):
                if i == 0:
                    continue
                value = self.model.getObjective(index=i).getValue()         
                if name == "Non-Regular Driver Usage" or name == "Machine Usage" or name == "Worker Usage":
                    value = round(value)
                self.objectives.append({"Objective": name, "Value": value})



        elif self.objective_strategy == "pareto":
            self.objectives.append({"Objective": "Construction Fulfillment", "Value": self.pareto_construction})
            self.objectives.append({"Objective": self.pareto_attribut, "Value": self.model.getObjective(index=0).getValue()})
            
        

        elif self.objective_strategy == "epsilon_constraint":
       
            construction_fulfillment_value = self.model.getObjective().getValue()
            self.objectives.append({"Objective": "Construction Fulfillment", "Value": construction_fulfillment_value})

            epsilon_constraints = [
                ("Machine Transport Distance", "EpsilonMachineDistanceConstraint", self.epsilon_machine_distance),
                ("Worker Work Distance", "EpsilonWorkerDistanceConstraint", self.epsilon_worker_distance),
                ("Machine Usage", "EpsilonMachineUsageConstraint", self.epsilon_machine_use),
                ("Worker Usage", "EpsilonWorkerUsageConstraint", self.epsilon_worker_use),
                ("Non-Regular Driver Usage", "EpsilonPenaltyCostConstraint", self.epsilon_non_regular_driver_use),
            ]

            for name, constraint_name, epsilon_value in epsilon_constraints:
                constr = self.model.getConstrByName(constraint_name)
                if constr is None:
                    print(f"Warning: Constraint '{constraint_name}' not found in the model.")
                    actual_value = None
                else:
                    slack = constr.getAttr(GRB.Attr.Slack)
                    actual_value = epsilon_value - slack
                self.objectives.append({"Objective": name, "Value": actual_value})



        # ========================
        # 1. Machine Flow Results
        # ========================

        # Direclty for terminal output
        machine_flows = []
        for m in self.M:
            for i in self.N_m[m]:
                for j in self.N_m[m]:
                    for flow in [
                        (self.start, j),
                        (i, j),
                        (i, self.end),
                        (self.start, self.end)
                    ]:
                        machine_flow_var = self.model.getVarByName(f"x[{m},{flow[0]},{flow[1]}]")
                        if machine_flow_var and machine_flow_var.x > 0.5:
                            flow_entry = [m, flow[0], flow[1]]
                            if flow_entry not in machine_flows:
                                machine_flows.append(flow_entry)

        sorted_machine_flows = []
        for machine, group in groupby(sorted(machine_flows, key=lambda x: x[0]), key=lambda x: x[0]):
            sorted_group = sorted(
                list(group),
                key=lambda x: (
                    0 if x[1] == 'start' else
                    2 if x[2] == 'end' else
                    1,
                    self.O_t_start_inverted.get(x[2], float('inf'))
                )
            )
            sorted_machine_flows.extend(sorted_group)


        # Route plan for Solution object
        self.route_plan_machine = {m: [] for m in self.M}
        for m in self.M:
            for i in self.N_m[m]:
                for j in self.N_m[m]:
                    machine_flow_var = self.model.getVarByName(f"x[{m},{i},{j}]")
                    if machine_flow_var and machine_flow_var.x > 0.5 and i not in self.route_plan_machine[m]:
                        self.route_plan_machine[m].append(i)
                machine_flow_var = self.model.getVarByName(f"x[{m},{i},{self.end}]")
                if machine_flow_var and machine_flow_var.x > 0.5 and i not in self.route_plan_machine[m]:
                    self.route_plan_machine[m].append(i)
        for m in self.M:
            self.route_plan_machine[m] = sorted(self.route_plan_machine[m], key=lambda x: self.O_t_start_inverted[x])



        # ========================
        # 2. Worker Flow Results
        # ========================

        # Direclty for terminal output
        worker_flows = []
        for w in self.W:
            for i in self.N_w[w]:
                for j in self.N_w[w]:

                    for flow in [
                        (self.start, j),
                        (i, j),
                        (i, self.end),
                        (self.start, self.end)
                    ]:
                        worker_flow_var = self.model.getVarByName(f"y[{w},{flow[0]},{flow[1]}]")
                        if worker_flow_var and worker_flow_var.x > 0.5:
                            flow_entry = [w, flow[0], flow[1]]
                            if flow_entry not in worker_flows:
                                worker_flows.append(flow_entry)

        sorted_worker_flows = []
        for worker, group in groupby(sorted(worker_flows, key=lambda x: x[0]), key=lambda x: x[0]):
            sorted_group = sorted(
                list(group),
                key=lambda x: (
                    0 if x[1] == 'start' else  
                    2 if x[2] == 'end' else  
                    1,  
                    self.O_t_start_inverted.get(x[2], float('inf'))  
                )
            )
            sorted_worker_flows.extend(sorted_group)


        # Route plan for Solution object
        self.route_plan_worker = {w: [] for w in self.W}
        for w in self.W:
            for i in self.N_w[w]:
                for j in self.N_w[w]:
                    worker_flow_var = self.model.getVarByName(f"y[{w},{i},{j}]")
                    if worker_flow_var and worker_flow_var.x > 0.5 and i not in self.route_plan_worker[w]:
                        self.route_plan_worker[w].append(i)
                worker_flow_var = self.model.getVarByName(f"y[{w},{i},{self.end}]")
                if worker_flow_var and worker_flow_var.x > 0.5 and i not in self.route_plan_worker[w]:
                    self.route_plan_worker[w].append(i)
        for w in self.W:
            self.route_plan_worker[w] = sorted(self.route_plan_worker[w], key=lambda x: self.O_t_start_inverted[x])


        # ========================
        # 3. Site Fulfillment Results
        # ========================
        self.site_fulfillment = {}
        for c in self.C:
            self.site_fulfillment[c] = False
            if self.model.getVarByName(f"u[{c}]").x > 0.5:
                self.site_fulfillment[c] = True

        self.sum_finished_sites = round(sum(self.model.getVarByName(f"u[{c}]").x for c in self.C))
        self.sum_total_sites = len(self.C)
        self.sum_finished_order_items = round(sum(self.model.getVarByName(f"x[{m},{i},{j}]").x for m in self.M for i in self.N_m[m] for j in self.N_m[m]) + sum(self.model.getVarByName(f"x[{m},{i},{self.end}]").x for m in self.M for i in self.N_m[m]))
        self.sum_order_items = len(self.N)


        # ========================
        # 3. Worker and Machine Utilization
        # ========================
        
        number_of_machines = len(self.M)
        number_of_workers = len(self.W)
        self.number_of_used_worker = round(sum(self.model.getVarByName(f"y[{w},{self.start},{j}]").x for w in self.W for j in self.N_w[w]))
        self.number_of_used_machines = round(sum(self.model.getVarByName(f"x[{m},{self.start},{j}]").x for m in self.M for j in self.N_m[m]))
        self.non_regular_driver_count = round(sum(self.model.getVarByName(f"r[{i}]").x for i in self.N))

        self.distance_machine = {}
        for m in self.M:
            self.distance_machine[m] = {"Distance": 0, "Utilization": False}
            for i in self.N_m[m]:
                for j in self.N_m[m]:
                    if i != j and self.model.getVarByName(f"x[{m},{i},{j}]").x > 0.5:
                        self.distance_machine[m]["Distance"] += self.d_ij[i][j]
                        self.distance_machine[m]["Utilization"] = True


        self.total_distance_machine = sum(self.distance_machine[m]["Distance"] for m in self.M)
        
        
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
        df_machine = pd.DataFrame(sorted_machine_flows, columns=["Machine", "From Order", "To Order"])
        df_worker = pd.DataFrame(sorted_worker_flows, columns=["Worker", "From Order", "To Order"])
        df_site = pd.DataFrame.from_dict(self.site_fulfillment, columns=["Fulfilled"], orient="index")
        df_transport = pd.DataFrame.from_dict(self.distance_machine, orient="index")
        df_worker_transport = pd.DataFrame.from_dict(self.distance_worker, columns=["Distance"], orient="index")
        df_working_hours = pd.DataFrame.from_dict(self.working_hours, columns=["Working Hours"], orient="index")

        # ========================
        # 6. Display Results
        # ========================
        print("\nMachine Flows:")
        print(df_machine)
        print("\nWorker Flows:")
        print(df_worker)
        print("\nTransport Distance:")
        print(df_transport)
        print(f"Total Transport Distance: {self.total_distance_machine}")
        print("\nWork Distance:")
        print(df_worker_transport)
        print(f"Total Work Distance: {self.total_distance_worker}")
        print("\nWorking Hours:")
        print(df_working_hours)
        print(f"Total Working Hours: {self.total_working_hours}")
        print("\nSite Fulfillment:")
        print(df_site)
        print(f"\nNumber of fulfilled sites: {int(self.sum_finished_sites)} / {self.sum_total_sites}")
        print(f"Number of fulfilled order items: {int(self.sum_finished_order_items)} / {self.sum_order_items}")
        print(f"Number of non-regular drivers used: {int(self.non_regular_driver_count)} / {int(self.sum_finished_order_items)}")
        print(f"\nNumber of used machines: {int(self.number_of_used_machines)} / {number_of_machines}")
        print(f"Number of used workers: {int(self.number_of_used_worker)} / {number_of_workers}\n")


    def save_solution_to_file(self):
        """Save the optimization results to an output file."""
        print("\nSaving solution to output file...")

        # ========================
        # 1. Worker Assignments
        # ========================
        solution_data = {"Arbeiterzuweisung": {}}

        for w in self.W:
            current_worker = next(worker for worker in self.data.workers if worker.personal_number == w)
            for i in self.N_w[w]:
                current_order_item = next(orderItem for orderItem in self.data.order_items if orderItem.id == i)
                for j in self.N_w[w]:
                    if i != j and self.model.getVarByName(f"y[{w},{i},{j}]").x > 0.5:
                        if current_worker.name not in solution_data["Arbeiterzuweisung"]:
                            solution_data["Arbeiterzuweisung"][current_worker.name] = []
                        assignment = {
                            "ID": current_order_item.id,
                            "Start": current_order_item.start_time.isoformat(),
                            "Ende": current_order_item.end_time.isoformat(),
                            "Dauer": current_order_item.duration,
                            "Auftragsnummer": current_order_item.order_number,
                            "MaschinenTyp": current_order_item.machine_type,
                            "AnbaugeraeteTypen": current_order_item.equipment_types,
                            "Arbeiterqualifikationen": current_order_item.worker_qualifications,
                            "zugewieseneMaschine": current_order_item.assigned_machine,
                            "Typ": current_order_item.type,
                        }
                        solution_data["Arbeiterzuweisung"][current_worker.name].append(assignment)
                if self.model.getVarByName(f"y[{w},{i},end]").x > 0.5:
                    if current_worker.name not in solution_data["Arbeiterzuweisung"]:
                        solution_data["Arbeiterzuweisung"][current_worker.name] = []
                    assignment = {
                        "ID": current_order_item.id,
                        "Start": current_order_item.start_time.isoformat(),
                        "Ende": current_order_item.end_time.isoformat(),
                        "Dauer": current_order_item.duration,
                        "Auftragsnummer": current_order_item.order_number,
                        "MaschinenTyp": current_order_item.machine_type,
                        "AnbaugeraeteTypen": current_order_item.equipment_types,
                        "Arbeiterqualifikationen": current_order_item.worker_qualifications,
                        "zugewieseneMaschine": current_order_item.assigned_machine,
                        "Typ": current_order_item.type,
                    }
                    solution_data["Arbeiterzuweisung"][current_worker.name].append(assignment)

        # ========================
        # 2. Machine Assignments
        # ========================
        solution_data["Maschinenzuweisung"] = {}

        for m in self.M:
            current_machine = next(machine for machine in self.data.machines if machine.name == m)
            for i in self.N_m[m]:
                current_order_item = next(orderItem for orderItem in self.data.order_items if orderItem.id == i)
                for j in self.N_m[m]:
                    if i != j and self.model.getVarByName(f"x[{m},{i},{j}]").x > 0.5:
                        if current_machine.name not in solution_data["Maschinenzuweisung"]:
                            solution_data["Maschinenzuweisung"][current_machine.name] = []
                        assignment = {
                            "ID": current_order_item.id,
                            "Start": current_order_item.start_time.isoformat(),
                            "Ende": current_order_item.end_time.isoformat(),
                            "Dauer": current_order_item.duration,
                            "Auftragsnummer": current_order_item.order_number,
                            "MaschinenTyp": current_order_item.machine_type,
                            "AnbaugeraeteTypen": current_order_item.equipment_types,
                            "Arbeiterqualifikationen": current_order_item.worker_qualifications,
                            "zugewieseneMaschine": current_order_item.assigned_machine,
                            "Typ": current_order_item.type,
                        }
                        solution_data["Maschinenzuweisung"][current_machine.name].append(assignment)
                if self.model.getVarByName(f"x[{m},{i},end]").x > 0.5:
                    if current_machine.name not in solution_data["Maschinenzuweisung"]:
                        solution_data["Maschinenzuweisung"][current_machine.name] = []
                    assignment = {
                        "ID": current_order_item.id,
                        "Start": current_order_item.start_time.isoformat(),
                        "Ende": current_order_item.end_time.isoformat(),
                        "Dauer": current_order_item.duration,
                        "Auftragsnummer": current_order_item.order_number,
                        "MaschinenTyp": current_order_item.machine_type,
                        "AnbaugeraeteTypen": current_order_item.equipment_types,
                        "Arbeiterqualifikationen": current_order_item.worker_qualifications,
                        "zugewieseneMaschine": current_order_item.assigned_machine,
                        "Typ": current_order_item.type,
                    }
                    solution_data["Maschinenzuweisung"][current_machine.name].append(assignment)

        solution_data["RechenzeitInSekunden"] = self.model.Runtime

        solution_data["Baustellenanzahl"] = self.sum_total_sites
        solution_data["Baustellenfertig"] = self.sum_finished_sites

        solution_data["Baustellebearbeitet"] = self.site_fulfillment
        
        solution_data["OrderItemsanzahl"] = self.sum_order_items
        solution_data["OrderItemsfertig"] = self.sum_finished_order_items
        solution_data["NichtregulaereFahrer"] = self.non_regular_driver_count

        solution_data["MaschinenanzahlGesamt"] = len(self.M)
        solution_data["MaschinenGenutzt"] = self.number_of_used_machines
        solution_data["MaschinenGenutztDetails"] = {key: value["Utilization"] for key, value in self.distance_machine.items()}
        
        solution_data["TransportdistanzGesamt"] = self.total_distance_machine
        solution_data["Transportdistanz"] = {key: value["Distance"] for key, value in self.distance_machine.items()}

        solution_data["ArbeiteranzahlGesamt"] = len(self.W)
        solution_data["ArbeiterGenutzt"] = self.number_of_used_worker

        solution_data["ArbeitswegGesamt"] = self.total_distance_worker
        solution_data["Arbeitsweg"] = self.distance_worker

        solution_data["ArbeitszeitGesamt"] = self.total_working_hours
        solution_data["Arbeitszeit"] = self.working_hours


        # ========================
        # 3. Save Solution Data to File
        # ========================
        parent_folder = self.data._parent_folder
        solution_path = Path.cwd().parent / "Data" / "Solution" / parent_folder / self.data.instance / self.objective_strategy
        solution_path.mkdir(parents=True, exist_ok=True)
        output_filename = solution_path / f"Solution_{self.data.instance_filename}"
        with open(output_filename, "w") as output_file:
            json.dump(solution_data, output_file, indent=4)

        print(f"Solution saved to: {output_filename} \n")


        # ========================
        # 4. Save Objective Values to File
        # ========================


        output_data = {"instance": self.data.instance, "computational_time": self.model.Runtime, "strategy": self.objective_strategy, "results": self.objectives}

        output_file = solution_path / f"{self.objective_strategy}_strategy_results_{self.data.instance}.json"
        with open(output_file, mode="w") as file:
            json.dump(output_data, file, indent=4)


        # ========================
        # 5. Extra File with Variables
        # ========================

        on = False

        if on:
            solution = {}
            for var in self.model.getVars():
                #if round(var.X) > 0:
                    solution[var.VarName] = round(var.X)

            output_filename = solution_path / f"Variables_{self.data.instance_filename}"
            with open(output_filename, "w") as output_file:
                json.dump(solution, output_file, indent=4)


    def execute(self):
        """Run the full optimization workflow."""
        
        self.first_round = True

        self.preprocess_data()
        self.create_optimization_model()
        feasible = self.solve_model()
        self.first_round_construction = round(self.model.getObjective(index=0).getValue() * -1)

        if self.objective_strategy == "hierarchical_tolerance":
            self.first_round = False
            self.create_optimization_model()
            feasible = self.solve_model()


        if not feasible:
            print("Model is infeasible.")
            return None, None
        
        self.postprocess_results()

        MIP_solution = Solution(self.route_plan_worker, self.route_plan_machine, self.data)

        return MIP_solution, self.objectives

        