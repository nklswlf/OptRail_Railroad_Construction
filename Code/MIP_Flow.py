import gurobipy as gp
from gurobipy import GRB
import json
from pathlib import Path
import pandas as pd
from InputData import *
from OutputData import GanttDiagramGenerator
from time import time


class FlowFormulation:
    
    def __init__(self, instance_filename):
        self.instance_filename = instance_filename
        self.instance = instance_filename.split('Construction_')[1].split('.json')[0]
        self.data = None
        self.model = None
        #self.objective_strategy = objective_strategy

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
        self.d_wj = []  # Distance matrix for workers (work routes)

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
        self.S_Nmax = 5 # Max consecutive night shifts
        self.S_max = 10 # Max shifts in a time period
        self.T_Smax = 14 # Time period for max shifts
        self.T_Wmax = 160 # Max working hours in the full planning horizon
        

        # ========================
        # 6. Other Constants
        # ========================
        self.SECONDS_IN_A_DAY = 86400  # Number of seconds in a day
        self.TRANSPORT_SPEED = 1680  # Machine transport speed (km/day)
        self.TIME_BETWEEN_SHIFTS = 9 / 24  # Rest period between shifts (in days)


    def load_instance(self):
        """Load the instance data from a JSON file."""
        print("\nLoading instance data...")
        current_time = time()
        self.data = InputData(self.instance_filename)
        elapsed_time = time() - current_time
        print("Instance data loaded successfully.")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")

        
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
                if not orderItem.worker_qualifications:
                    self.N_w[worker.personal_number].append(orderItem.id)
                elif orderItem.worker_qualifications == worker.qualifications:
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
            if orderItem.start_time.hour <= 12:
                self.D_r[t_start_int].append(orderID)

            # N_r: Night shifts grouped by day
            if t_start_int not in self.N_r:
                self.N_r[t_start_int] = []
            if orderItem.start_time.hour > 12:
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
            self.d_wj.append(row)

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

        self.objective_strategy = "weighted"
        
        if self.objective_strategy == "weighted":
            self.model.setObjective(
                gp.quicksum(100000 * u[c] for c in self.C) -
                gp.quicksum(0.5 * self.d_ij[i][j] * x[m, i, j] for m in self.M for i in self.N_m[m] for j in self.N_m[m]) -
                gp.quicksum(0.5 * self.d_wj[w][j] * y[w, i, j] for w in self.W for i in self.N_w[w] for j in self.N_w[w]) -
                gp.quicksum(100 * x[m, self.start, j] for m in self.M for j in self.N_m[m]) -
                gp.quicksum(100 * y[w, self.start, j] for w in self.W for j in self.N_w[w]) -
                gp.quicksum(10 * r[i] for i in self.N),
                GRB.MAXIMIZE
            )
        elif self.objective_strategy == "hierarchical":
            self.model.setObjective(
                gp.quicksum(u[c] for c in self.C),
                GRB.MAXIMIZE
            )

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


    def postprocess_results(self):
        """Extract and display results after model optimization."""
        print("\nPostprocessing results...")

        # ========================
        # 1. Machine Flow Results
        # ========================
        machine_flows = []
        for m in self.M:
            for i in self.N_m[m]:
                for j in self.N_m[m]:
                    machine_flow_var = self.model.getVarByName(f"x[{m},{self.start},{j}]")
                    if machine_flow_var and machine_flow_var.x > 0.5 and [m, self.start, j] not in machine_flows:
                        machine_flows.append([m, self.start, j])
                    machine_flow_var = self.model.getVarByName(f"x[{m},{i},{j}]")
                    if machine_flow_var and machine_flow_var.x > 0.5:
                        machine_flows.append([m, i, j])
                machine_flow_var = self.model.getVarByName(f"x[{m},{i},{self.end}]")
                if machine_flow_var and machine_flow_var.x > 0.5 and [m, i, self.end] not in machine_flows:
                    machine_flows.append([m, i, self.end])
            machine_flow_var = self.model.getVarByName(f"x[{m},{self.start},{self.end}]")
            if machine_flow_var and machine_flow_var.x > 0.5 and [m, self.start, self.end] not in machine_flows:
                machine_flows.append([m, self.start, self.end])

        # ========================
        # 2. Worker Flow Results
        # ========================
        worker_flows = []
        for w in self.W:
            for i in self.N_w[w]:
                for j in self.N_w[w]:
                    worker_flow_var = self.model.getVarByName(f"y[{w},{self.start},{j}]")
                    if worker_flow_var and worker_flow_var.x > 0.5 and [w, self.start, j] not in worker_flows:
                        worker_flows.append([w, self.start, j])
                    worker_flow_var = self.model.getVarByName(f"y[{w},{i},{j}]")
                    if worker_flow_var and worker_flow_var.x > 0.5:
                        worker_flows.append([w, i, j])
                worker_flow_var = self.model.getVarByName(f"y[{w},{i},{self.end}]")
                if worker_flow_var and worker_flow_var.x > 0.5 and [w, i, self.end] not in worker_flows:
                    worker_flows.append([w, i, self.end])
            worker_flow_var = self.model.getVarByName(f"y[{w},{self.start},{self.end}]")
            if worker_flow_var and worker_flow_var.x > 0.5 and [w, self.start, self.end] not in worker_flows:
                worker_flows.append([w, self.start, self.end])

        # ========================
        # 3. Site Fulfillment Results
        # ========================
        self.site_fulfillment = {}
        for c in self.C:
            self.site_fulfillment[c] = False
            if self.model.getVarByName(f"u[{c}]").x > 0.5:
                self.site_fulfillment[c] = True

        self.sum_finished_sites = sum(self.model.getVarByName(f"u[{c}]").x for c in self.C)
        self.sum_total_sites = len(self.C)
        self.sum_finished_order_items = sum(self.model.getVarByName(f"x[{m},{i},{j}]").x for m in self.M for i in self.N_m[m] for j in self.N_m[m]) + sum(self.model.getVarByName(f"x[{m},{i},{self.end}]").x for m in self.M for i in self.N_m[m])
        self.sum_order_items = len(self.N)


        # ========================
        # 3. Worker and Machine Utilization
        # ========================
        
        number_of_machines = len(self.M)
        number_of_workers = len(self.W)
        self.number_of_used_worker = sum(self.model.getVarByName(f"y[{w},{self.start},{j}]").x for w in self.W for j in self.N_w[w])
        self.number_of_used_machines = sum(self.model.getVarByName(f"x[{m},{self.start},{j}]").x for m in self.M for j in self.N_m[m])
        self.non_regular_driver_count = sum(self.model.getVarByName(f"r[{i}]").x for i in self.N)

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
                        self.distance_worker[w] += self.d_wj[w][j]

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

        self.total_working_hours = sum(self.working_hours.values())



        # ========================
        # 5. Create DataFrames
        # ========================
        df_machine = pd.DataFrame(machine_flows, columns=["Machine", "From Order", "To Order"])
        df_worker = pd.DataFrame(worker_flows, columns=["Worker", "From Order", "To Order"])
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
        print(f"Number of used workers: {int(self.number_of_used_worker)} / {number_of_workers}")


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
        solution_data["Zielfunktionswert"] = self.model.objVal

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
        solution_path = Path.cwd().parent / "Data" / "Solution" / parent_folder / self.instance
        solution_path.mkdir(parents=True, exist_ok=True)
        output_filename = solution_path / f"Solution_{self.instance_filename}"
        with open(output_filename, "w") as output_file:
            json.dump(solution_data, output_file, indent=4)

        print(f"Solution saved to: {output_filename} \n")


    def execute(self):
        """Run the full optimization workflow."""
        self.load_instance()
        self.preprocess_data()
        self.create_optimization_model()
        self.solve_model()
        self.postprocess_results()
        self.save_solution_to_file()
        GanttDiagramGenerator(self.instance_filename, self.data._parent_folder).create_gantt_diagrams()


if __name__ == "__main__":

    # Reduced
    #instance_filename = "Construction_a1_o12_m3_an5_ar3_reduced.json"
    #instance_filename = "Construction_a3_o80_m10_an10_ar9_reduced.json"
    #instance_filename = "Construction_a5_o96_m10_an10_ar10_reduced.json"

    # 10 Sites --> "Construction_a10_o118_m6_an53_ar13.json": Instance not duable since one order has no order items
    instance_filename = "Construction_a10_o107_m5_an57_ar12.json"
    #instance_filename = "Construction_a10_o114_m6_an57_ar11.json"
    #instance_filename = "Construction_a10_o119_m5_an54_ar13.json"
    #instance_filename = "Construction_a10_o144_m6_an53_ar12.json"

    # 15 Sites
    #instance_filename = "Construction_a15_o191_m8_an74_ar18.json"

    # 20 Sites
    #instance_filename = "Construction_a20_o259_m11_an101_ar26.json"

    # 50 Sites
    #instance_filename = "Construction_a50_o578_m28_an276_ar66.json"



    # Initialize and run the optimization
    optimizer = FlowFormulation(instance_filename)
    optimizer.execute()