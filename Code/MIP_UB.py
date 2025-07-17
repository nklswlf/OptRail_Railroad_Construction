"""
Mixed Integer Programming Upper Bound Formulation for Railroad Construction Optimization

This module implements various upper bound calculation techniques for the railroad construction
scheduling problem. It provides different bounding strategies (machine-only, worker-only, 
attachment-only, combined) to estimate the theoretical maximum achievable site completion
under relaxed constraints.

The module supports both Linear Programming (LP) relaxation and Binary Integer Programming (BIP)
formulations to compute upper bounds that can guide optimization algorithms and provide
benchmarks for solution quality assessment.

Key Features:
- Multiple upper bound calculation strategies
- Flow-based mathematical formulation
- Resource-specific constraint relaxation
- Gurobi optimization solver integration
- Occupational safety compliance
- Transportation and working time modeling

Dependencies:
- gurobipy: Mathematical optimization solver
- Code.InputData: Data structure definitions
- Code.OutputData: Solution representation classes
- pandas: Data manipulation and analysis
- pathlib: File system path operations
"""

import gurobipy as gp
from gurobipy import GRB
import json
from pathlib import Path
import pandas as pd
from Code.InputData import *
from Code.OutputData import *
import time
from itertools import groupby
from collections import defaultdict
import re


class UpperBound:
    """
    Upper bound calculation for railroad construction optimization problems.
    
    This class implements various upper bound computation techniques by relaxing different
    constraint sets in the mixed integer programming formulation. It can calculate bounds
    for individual resource types (machines, workers, attachments) or combinations thereof.
    
    The upper bound provides a theoretical maximum for site completion that serves as a
    benchmark for evaluating the quality of feasible solutions and guiding optimization
    algorithms toward better solutions.
    
    Supported Bound Types:
    - 'machine': Consider only machine availability constraints
    - 'worker': Consider only worker availability and safety constraints  
    - 'attachment': Consider only attachment equipment constraints
    - 'both': Consider both machine and worker constraints
    - 'all': Consider all resource type constraints
    
    Bound Techniques:
    - 'LP': Linear programming relaxation (continuous variables)
    - 'BIP': Binary integer programming (binary variables)
    """
    
    def __init__(self, data, bound_technique = "LP", upper_bound = 'all', testing = False, experiment = None):
        """
        Initialize the upper bound calculation with configuration parameters.
        
        Args:
            data: InputData object containing problem instance information
            bound_technique (str): Optimization technique - 'LP' for linear programming
                                 relaxation or 'BIP' for binary integer programming
            upper_bound (str): Type of upper bound calculation:
                             - 'machine': Machine-only constraints
                             - 'worker': Worker-only constraints  
                             - 'attachment': Attachment-only constraints
                             - 'both': Machine and worker constraints
                             - 'all': All resource constraints
            testing (bool): Enable experimental multi-objective testing mode
            experiment (int): Specific experiment configuration (2 or 3) for testing mode
        """
        # Core problem data and configuration
        self.data = data                        # Input data containing all problem information
        self.model = None                       # Gurobi optimization model (initialized later)
        self.upper_bound = upper_bound          # Type of upper bound to calculate
        self.bound_technique = bound_technique  # LP relaxation or BIP formulation
        self.testing = testing                  # Enable multi-objective testing
        self.experiment = experiment            # Experiment number for testing mode

        # ========================
        # 1. Sets - Resource and Order Collections
        # ========================
        
        # Machine-related sets (enabled for machine, both, or all bounds)
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':
            self.M = []         # List of machine IDs (machine names)
            self.N_m = {}       # Dictionary: Machine -> Compatible order items
            self.W_m = {}       # Dictionary: Machine -> Regular driver IDs
            
        # Worker-related sets (enabled for worker, both, or all bounds)
        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':
            self.W = []         # List of worker IDs (personal numbers)
            self.N_w = {}       # Dictionary: Worker -> Qualified order items
            
        # Attachment-related sets (enabled for attachment or all bounds)
        if self.upper_bound == 'attachment' or self.upper_bound == "all":
            self.A = []         # List of attachment IDs
            self.N_a = {}       # Dictionary: Attachment -> Compatible order items
            self.K = set()      # Set of all attachment types required
            self.A_k = {}       # Dictionary: Attachment type -> Available attachments
        
        # Universal sets (always required)
        self.N = []             # List of all order item IDs
        self.C = []             # List of construction site IDs
        self.N_c = {}           # Dictionary: Site -> Order items at that site
        self.q_c = {}           # Dictionary: Site -> Complexity score

        # ========================
        # 2. Temporal Parameters - Time-based Data Structures
        # ========================
        self.start_date = None              # Planning horizon start date
        self.end_date = None                # Planning horizon end date
        self.O_t = {}                       # Dictionary: Day -> Order items starting that day
        self.D_r = {}                       # Dictionary: Day -> Day shift order items
        self.N_r = {}                       # Dictionary: Day -> Night shift order items  
        self.A_r = {}                       # Dictionary: Day -> All shift order items
        self.O_t_start = {}                 # Dictionary: Start time -> Order items
        self.O_t_end = {}                   # Dictionary: End time -> Order items
        self.O_t_start_inverted = {}        # Dictionary: Order item -> Start time
        self.O_t_end_inverted = {}          # Dictionary: Order item -> End time

        # ========================
        # 3. Scheduling Dependencies - Predecessor/Successor Relationships
        # ========================
        self.P_mn = {}          # Dictionary: (Machine, Order) -> Predecessor order items
        self.S_mn = {}          # Dictionary: (Machine, Order) -> Successor order items
        self.P_wn = {}          # Dictionary: (Worker, Order) -> Predecessor order items
        self.S_wn = {}          # Dictionary: (Worker, Order) -> Successor order items
        self.P_an = {}          # Dictionary: (Attachment, Order) -> Predecessor order items
        self.S_an = {}          # Dictionary: (Attachment, Order) -> Successor order items
        self.d_ij = []          # Distance matrix: [Order i][Order j] -> Transport distance
        self.d_wi = []          # Distance matrix: [Worker][Order] -> Work travel distance
        self.a_ok = {}          # Dictionary: Order item -> {Attachment type: Quantity needed}

        # ========================
        # 4. Time Management - Planning Horizon and Durations
        # ========================
        self.T_range = []       # List of all days in planning horizon [0, 1, 2, ...]
        self.T = 0              # Total planning horizon length (number of days)
        self.start = "start"    # Virtual start node for flow formulation
        self.end = "end"        # Virtual end node for flow formulation

        # ========================
        # 5. Occupational Safety Parameters - Worker Protection Constraints
        # ========================
        self.S_Nmax = data._max_consecutive_night_shifts    # Maximum consecutive night shifts
        self.S_max = data._max_shifts_in_time_period        # Maximum shifts in time period
        self.T_Smax = data._time_period_for_max_shifts.days # Time period for shift limits (days)
        self.T_Wmax = data._max_working_hours               # Maximum working hours per worker

        # ========================
        # 6. Physical Constants - Time and Speed Parameters
        # ========================
        self.SECONDS_IN_A_DAY = data._seconds_a_day                         # Seconds per day (86400)
        self.TRANSPORT_SPEED = data._transport_speed_kmh * 24               # Machine transport speed (km/day)
        self.TIME_BETWEEN_SHIFTS = data._hours_between_shifts / 24          # Required rest between shifts (days)

        
    def preprocess_data(self):
        """
        Preprocess the input data to create optimization-ready data structures.
        
        This method transforms the raw input data into mathematical programming formats,
        including resource compatibility matrices, temporal relationships, scheduling
        dependencies, and safety constraint parameters. The preprocessing is selective
        based on the upper bound type being calculated.
        """
        print("\n Preprocessing data for Model...")
        current_time = time.time()
        
        # ========================
        # 1. Machine Data Processing - Extract machine capabilities and assignments
        # ========================
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':

            for machine in self.data.machines:
                # Register machine identifier
                self.M.append(machine.name)
                
                # Map machine to its regular drivers (for safety constraints)
                self.W_m[machine.name] = [int(driver) for driver in machine.default_drivers]
                
                # Find all order items compatible with this machine type
                self.N_m[machine.name] = []
                for orderItem in self.data.order_items:
                    if orderItem.machine_type == machine.type:
                        self.N_m[machine.name].append(orderItem.id)

        # ========================
        # 2. Worker Data Processing - Extract worker qualifications and capabilities
        # ========================

        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':

            for worker in self.data.workers:
                # Register worker identifier
                self.W.append(worker.personal_number)
                
                # Find all order items this worker can perform based on qualifications
                self.N_w[worker.personal_number] = []
                for orderItem in self.data.order_items:
                    # Worker can handle orders with no qualification requirements
                    if not orderItem.worker_qualifications:
                        self.N_w[worker.personal_number].append(orderItem.id)
                    # Worker can handle orders if they have all required qualifications
                    elif set(orderItem.worker_qualifications).issubset(set(worker.qualifications)):
                        self.N_w[worker.personal_number].append(orderItem.id)

        # ========================
        # 3. Attachment Equipment Processing - Extract equipment compatibility
        # ========================
        
        if self.upper_bound == 'attachment' or self.upper_bound == 'all':
            
            for attachment in self.data.attachments:
                # Register attachment identifier
                self.A.append(attachment.id)
                
                # Find all order items that require this attachment type
                self.N_a[attachment.id] = []
                for orderItem in self.data.order_items:
                    if attachment.type in orderItem.equipment_types:
                        self.N_a[attachment.id].append(orderItem.id)

        # ========================
        # 4. Construction Site Processing - Group orders by location
        # ========================
        for order in self.data.orders:
            # Register site identifier
            self.C.append(order.site_number)
            
            # Map site to its constituent order items
            self.N_c[order.site_number] = [int(item_id) for item_id in order.order_item_ids]
            
            # Store site complexity score (for objective weighting)
            self.q_c[order.site_number] = order.complexity_score

        # ========================
        # 5. Order Item Temporal Processing - Extract timing and scheduling data
        # ========================
        self.N = [orderItem.id for orderItem in self.data.order_items]
        self.start_date = self.data.start_date
        self.end_date = self.data.end_date

        for orderItem in self.data.order_items:

            orderID = orderItem.id
            
            # Calculate start time as days from planning horizon start
            delta_start = (orderItem.start_time - self.start_date)
            t_start = delta_start.total_seconds() / self.SECONDS_IN_A_DAY
            t_start_int = int(t_start)  # Integer day for shift categorization

            # Group order items by start time (for temporal constraints)
            if t_start not in self.O_t_start:
                self.O_t_start[t_start] = []
            self.O_t_start[t_start].append(orderID)
            self.O_t_start_inverted[orderID] = t_start

            # Calculate end time as days from planning horizon start
            delta_end = (orderItem.end_time - self.start_date)
            t_end = delta_end.total_seconds() / self.SECONDS_IN_A_DAY
            
            # Group order items by end time (for scheduling dependencies)
            if t_end not in self.O_t_end:
                self.O_t_end[t_end] = []
            self.O_t_end[t_end].append(orderID)
            self.O_t_end_inverted[orderID] = t_end

            # Process shift categorization for worker safety constraints
            if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':

                # Group order items by day (for daily shift limits)
                if t_start_int not in self.O_t:
                    self.O_t[t_start_int] = []
                self.O_t[t_start_int].append(orderID)

                # Categorize as day shift (early hours)
                if t_start_int not in self.D_r:
                    self.D_r[t_start_int] = []
                if orderItem.start_time.hour <= self.data._day_and_night_shift_boundary:
                    self.D_r[t_start_int].append(orderID)

                # Categorize as night shift (late hours)
                if t_start_int not in self.N_r:
                    self.N_r[t_start_int] = []
                if orderItem.start_time.hour > self.data._day_and_night_shift_boundary:
                    self.N_r[t_start_int].append(orderID)

                # Group all shifts by day (for total shift counting)
                if t_start_int not in self.A_r:
                    self.A_r[t_start_int] = []
                self.A_r[t_start_int].append(orderID)
        
        # ========================
        # 6. Attachment Type Mapping - Process equipment requirements
        # ========================
        if self.upper_bound == 'attachment' or self.upper_bound == 'all':
            for order_item in self.data.order_items:
                # Initialize attachment requirements dictionary for this order
                self.a_ok[order_item.id] = dict()
                
                for equipment in order_item.equipment_types:
                    # Count quantity of each equipment type needed
                    if equipment not in self.a_ok[order_item.id]:
                        self.a_ok[order_item.id][equipment] = 0
                    self.a_ok[order_item.id][equipment] += 1
                    
                    # Register equipment type globally
                    self.K.add(equipment)

                    # Map equipment type to available attachments
                    if equipment not in self.A_k:
                        self.A_k[equipment] = []
                    for attachment in self.data.attachments:
                        if attachment.type == equipment:
                            if attachment.id not in self.A_k[equipment]:
                                self.A_k[equipment].append(attachment.id)

                
        # ========================
        # 7. Transportation Distance Matrices - Calculate travel costs
        # ========================

        # Machine transportation distances (site-to-site transport costs)
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':
            for i in self.data.order_items:
                row = []
                for j in self.data.order_items:
                    # Find sites containing order items i and j
                    site_i = next((k for k, v in self.N_c.items() if i.id in v))
                    site_j = next((k for k, v in self.N_c.items() if j.id in v))
                    
                    # Use transport route distance between sites
                    row.append(self.data.transport_routes[site_i][site_j])
                self.d_ij.append(row)

        # Worker travel distances (worker-to-site travel costs)
        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':
            for i in self.data.workers:
                row = []
                for j in self.data.order_items:
                    # Find site containing order item j
                    site_j = next((k for k, v in self.N_c.items() if j.id in v))
                    
                    # Use work route distance from worker to site
                    row.append(self.data.work_routes[i.personal_number][site_j])
                self.d_wi.append(row)

        # ========================
        # 8. Scheduling Dependencies - Calculate predecessor/successor relationships
        # ========================

        # Machine scheduling dependencies (based on transport time)
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':
            for m in self.M:
                for n in self.N_m[m]:
                    # Initialize virtual start and end nodes
                    if (m, self.start) not in self.P_mn:
                        self.P_mn[m, self.start] = []
                        self.S_mn[m, self.start] = [self.end]
                    if (m, self.end) not in self.P_mn:
                        self.P_mn[m, self.end] = []
                        self.S_mn[m, self.end] = [self.start]

                    # Every order can start from virtual start and end at virtual end
                    self.P_mn[m, n] = [self.start]
                    self.S_mn[m, self.start].append(n)
                    self.P_mn[m, self.end].append(n)
                    self.S_mn[m, n] = [self.end]

                    # Calculate feasible order sequences based on transport time
                    for i in self.N_m[m]:
                        if n != i:
                            start_time_n = self.O_t_start_inverted[n]
                            end_time_n = self.O_t_end_inverted[n]
                            start_time_i = self.O_t_start_inverted[i]
                            end_time_i = self.O_t_end_inverted[i]

                            # Order i can precede order n if there's sufficient transport time
                            if start_time_n >= end_time_i + self.d_ij[i][n] / self.TRANSPORT_SPEED:
                                self.P_mn[m, n].append(i)

                            # Order n can precede order i if there's sufficient transport time
                            if start_time_i > end_time_n + self.d_ij[n][i] / self.TRANSPORT_SPEED:
                                self.S_mn[m, n].append(i)

        # Attachment scheduling dependencies (same logic as machines)
        if self.upper_bound == 'attachment' or self.upper_bound == "all":
            for a in self.A:
                for n in self.N_a[a]:
                    # Initialize virtual start and end nodes
                    if (a, self.start) not in self.P_an:
                        self.P_an[a, self.start] = []
                        self.S_an[a, self.start] = [self.end]
                    if (a, self.end) not in self.P_an:
                        self.P_an[a, self.end] = []
                        self.S_an[a, self.end] = [self.start]

                    # Every order can start from virtual start and end at virtual end
                    self.P_an[a, n] = [self.start]
                    self.S_an[a, self.start].append(n)
                    self.P_an[a, self.end].append(n)
                    self.S_an[a, n] = [self.end]

                    # Calculate feasible order sequences based on transport time
                    for i in self.N_a[a]:
                        if n != i:
                            start_time_n = self.O_t_start_inverted[n]
                            end_time_n = self.O_t_end_inverted[n]
                            start_time_i = self.O_t_start_inverted[i]
                            end_time_i = self.O_t_end_inverted[i]

                            # Order i can precede order n if there's sufficient transport time
                            if start_time_n >= end_time_i + self.d_ij[i][n] / self.TRANSPORT_SPEED:
                                self.P_an[a, n].append(i)

                            # Order n can precede order i if there's sufficient transport time
                            if start_time_i > end_time_n + self.d_ij[n][i] / self.TRANSPORT_SPEED:
                                self.S_an[a, n].append(i)
        
        # Worker scheduling dependencies (based on rest time requirements)
        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':
            for w in self.W:
                for n in self.N_w[w]:
                    # Initialize virtual start and end nodes
                    if (w, self.start) not in self.P_wn:
                        self.P_wn[w, self.start] = []
                        self.S_wn[w, self.start] = [self.end]
                    if (w, self.end) not in self.P_wn:
                        self.P_wn[w, self.end] = []
                        self.S_wn[w, self.end] = [self.start]

                    # Every order can start from virtual start and end at virtual end
                    self.P_wn[w, n] = [self.start]
                    self.S_wn[w, self.start].append(n)
                    self.P_wn[w, self.end].append(n)
                    self.S_wn[w, n] = [self.end]

                    # Calculate feasible order sequences based on rest time requirements
                    for i in self.N_w[w]:
                        if n != i:
                            start_time_n = self.O_t_start_inverted[n]
                            end_time_n = self.O_t_end_inverted[n]
                            start_time_i = self.O_t_start_inverted[i]
                            end_time_i = self.O_t_end_inverted[i]

                            # Order i can precede order n if there's sufficient rest time
                            if start_time_n >= end_time_i + self.TIME_BETWEEN_SHIFTS:
                                self.P_wn[w, n].append(i)

                            # Order n can precede order i if there's sufficient rest time
                            if start_time_i >= end_time_n + self.TIME_BETWEEN_SHIFTS:
                                self.S_wn[w, n].append(i)

        # ========================
        # 9. Planning Horizon Setup - Calculate time range and durations
        # ========================
        
        # Calculate total planning horizon length
        day_difference = self.end_date - self.start_date
        self.T_range = list(range(day_difference.days + 1))
        self.T = day_difference.days + 1
        
        # Extract order item durations for working time calculations
        self.t_o = [orderItem.duration for orderItem in self.data.order_items]

        elapsed_time = time.time() - current_time
        print(f" Data preprocessed successfully after {elapsed_time:.2f} seconds")


    def create_optimization_model(self):
        """
        Create and configure the Gurobi optimization model for upper bound calculation.
        
        This method builds the mathematical programming formulation by creating decision
        variables and configuring solver parameters. The model structure varies based
        on the upper bound type and whether LP relaxation or BIP formulation is used.
        
        The model uses flow-based formulation with virtual start/end nodes to represent
        resource scheduling and site completion decisions.
        """

        current_time = time.time()
        print("\n Creating Model...")
        
        # Initialize Gurobi optimization model
        self.model = gp.Model("Flow_Formulation")

        # ========================
        # 1. Solver Configuration - Set parameters based on bound technique
        # ========================

        if self.bound_technique == 'BIP':
            # Binary Integer Programming settings (for exact solutions)
            save_path = Path.cwd().parent / "Data" / "ModelFiles" / self.bound_technique / self.data.instance
            save_path.mkdir(parents=True, exist_ok=True)
            log_file = save_path / "gurobi.log"
            
            # Configure BIP solver parameters
            self.model.setParam("LogFile", str(log_file))      # Enable detailed logging
            self.model.setParam('TimeLimit', 10800)            # 3-hour time limit
            self.model.setParam("Threads", 8)                  # Use 8 CPU threads
        else:
            # Linear Programming settings (for fast upper bounds)
            self.model.setParam('OutputFlag', 0)               # Suppress solver output
            self.model.setParam("Threads", 8)                  # Use 8 CPU threads
            # Note: LP typically solves very quickly, no time limit needed

        # ========================
        # 2. Decision Variables Creation - Define optimization variables
        # ========================

        # Machine flow variables (if machine constraints are considered)
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':

            # Define all possible machine flow arcs in the network
            indices_1 = [(m, i, j) for m in self.M for i in self.N_m[m] for j in self.N_m[m]]  # Order-to-order flows
            indices_2 = [(m, self.start, j) for m in self.M for j in self.N_m[m]]             # Start-to-order flows
            indices_3 = [(m, i, self.end) for m in self.M for i in self.N_m[m]]               # Order-to-end flows
            indices_4 = [(m, self.start, self.end) for m in self.M]                           # Direct start-to-end (unused)
            all_indices = indices_1 + indices_2 + indices_3 + indices_4

            # Create variables based on bound technique
            if self.bound_technique == 'BIP':
                # Binary variables for exact integer solution
                x = self.model.addVars(all_indices, vtype=GRB.BINARY, name="x")
            elif self.bound_technique == 'LP':
                # Continuous variables for LP relaxation upper bound
                x = {}
                for idx in all_indices:
                    x[idx] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=1, name=f"x^{idx[0]}_{idx[1]}_{idx[2]}")

            self.model.update()  # Update model to reflect new variables

        # Worker flow variables (if worker constraints are considered)
        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':

            # Define all possible worker flow arcs in the network
            indices_1 = [(w, i, j) for w in self.W for i in self.N_w[w] for j in self.N_w[w]]  # Order-to-order flows
            indices_2 = [(w, self.start, j) for w in self.W for j in self.N_w[w]]             # Start-to-order flows
            indices_3 = [(w, i, self.end) for w in self.W for i in self.N_w[w]]               # Order-to-end flows
            indices_4 = [(w, self.start, self.end) for w in self.W]                           # Direct start-to-end (unused)
            all_indices = indices_1 + indices_2 + indices_3 + indices_4
            
            # Create variables based on bound technique
            if self.bound_technique == 'BIP':
                # Binary variables for exact integer solution
                y = self.model.addVars(all_indices, vtype=GRB.BINARY, name="y")
            elif self.bound_technique == 'LP':
                # Continuous variables for LP relaxation upper bound
                y = {}
                for idx in all_indices:
                    y[idx] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=1, name=f"y^{idx[0]}_{idx[1]}_{idx[2]}")

            self.model.update()  # Update model to reflect new variables

        # Attachment flow variables (if attachment constraints are considered)
        if self.upper_bound == 'attachment' or self.upper_bound == "all":

            # Define all possible attachment flow arcs in the network
            indices_1 = [(a, i, j) for a in self.A for i in self.N_a[a] for j in self.N_a[a]]  # Order-to-order flows
            indices_2 = [(a, self.start, j) for a in self.A for j in self.N_a[a]]             # Start-to-order flows
            indices_3 = [(a, i, self.end) for a in self.A for i in self.N_a[a]]               # Order-to-end flows
            indices_4 = [(a, self.start, self.end) for a in self.A]                           # Direct start-to-end (unused)
            all_indices = indices_1 + indices_2 + indices_3 + indices_4
            
            # Create variables based on bound technique
            if self.bound_technique == 'BIP':
                # Binary variables for exact integer solution
                z = self.model.addVars(all_indices, vtype=GRB.BINARY, name="z")
            elif self.bound_technique == 'LP':
                # Continuous variables for LP relaxation upper bound
                z = {}
                for idx in all_indices:
                    z[idx] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=1, name=f"z^{idx[0]}_{idx[1]}_{idx[2]}")

            self.model.update()  # Update model to reflect new variables

        # Site completion variables (always required)
        if self.bound_technique == 'BIP':
            # Binary variables indicating if each site is completed
            u = self.model.addVars(self.C, vtype=GRB.BINARY, name="u")
        elif self.bound_technique == 'LP':
            # Continuous variables for LP relaxation (0 <= u[c] <= 1)
            u = self.model.addVars(self.C, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="u")

        self.model.update()  # Update model to reflect new variables

        # ========================
        # 3. Objective Function Configuration - Set optimization goal
        # ========================

        # Primary objective: Maximize total number of completed construction sites
        self.construction_fulfillment = gp.quicksum(u[c] for c in self.C)

        if self.testing == False:
            # Standard upper bound calculation: maximize site completion only
            self.model.setObjective(self.construction_fulfillment, GRB.MAXIMIZE)
        else:
            # Experimental multi-objective testing mode
            
            # Additional variables for multi-objective experiments
            r = self.model.addVars(self.N, vtype=GRB.BINARY, name="r")  # Emergency driver usage indicators
            
            # Secondary objectives for comprehensive evaluation
            
            # Transportation distance minimization (machines moving between sites)
            self.machine_transport_distance = gp.quicksum(self.d_ij[i][j] * x[m, i, j] for m in self.M for i in self.N_m[m] for j in self.N_m[m])
            
            # Worker travel distance minimization (round-trip distances)
            self.worker_work_distance = gp.quicksum(2 * self.d_wi[w][i] * y[w, i, j] for w in self.W for i in self.N_w[w] for j in (self.N_w[w] + [self.end]))
            
            # Attachment transport distance minimization
            self.attachment_transport_distance = gp.quicksum(self.d_ij[i][j] * z[a, i, j] for a in self.A for i in self.N_a[a] for j in self.N_a[a])
            
            # Total distance across all resource types
            self.distances = self.machine_transport_distance + self.worker_work_distance + self.attachment_transport_distance
            
            # Emergency workforce usage minimization
            self.non_regular_driver_usage = gp.quicksum(r[i] for i in self.N)

            # Configure hierarchical multi-objective optimization
            if self.experiment == 2:
                # Three-level hierarchy: Sites > Emergency drivers > Distance
                self.model.setObjectiveN(-self.construction_fulfillment, index=0, priority=3, reltol=0, abstol=0)  # Maximize sites (highest priority)
                self.model.setObjectiveN(self.non_regular_driver_usage, index=1, priority=2, reltol=0, abstol=0)    # Minimize emergency drivers
                self.model.setObjectiveN(self.distances, index=2, priority=1, reltol=0, abstol=0)                  # Minimize distances (lowest priority)

            elif self.experiment == 3:
                # Four-level hierarchy: Sites > Emergency drivers > Distance > Resource usage
                
                # Resource usage minimization (total number of resources activated)
                self.machine_usage = gp.quicksum(x[m, self.start, j] for m in self.M for j in self.N_m[m])
                self.worker_usage = gp.quicksum(y[w, self.start, j] for w in self.W for j in self.N_w[w])
                self.attachment_usage = gp.quicksum(z[a, self.start, j] for a in self.A for j in self.N_a[a])
                self.resource_usage = self.machine_usage + self.worker_usage + self.attachment_usage

                # Four-level hierarchical optimization
                self.model.setObjectiveN(-self.construction_fulfillment, index=0, priority=4, reltol=0, abstol=0)  # Maximize sites (highest priority)
                self.model.setObjectiveN(self.non_regular_driver_usage, index=1, priority=3, reltol=0, abstol=0)    # Minimize emergency drivers
                self.model.setObjectiveN(self.distances, index=2, priority=2, reltol=0, abstol=0)                  # Minimize distances
                self.model.setObjectiveN(self.resource_usage, index=3, priority=1, reltol=0, abstol=0)             # Minimize resource usage (lowest priority)
            
            elif self.experiment == None:
                raise Exception("Experiment not defined. Please set the experiment parameter to 2 or 3.")

            # Regular driver availability constraints (ensure sufficient qualified drivers)
            for m in self.M:
                for i in self.N_m[m]:
                    # Machine can only operate if regular driver is available or emergency driver is used
                    self.model.addConstr(
                        gp.quicksum(x[m, i, j] for j in self.S_mn[m, i]) <=
                        gp.quicksum(y[w, i, j] for w in self.W_m[m] if (w, i) in self.S_wn for j in self.S_wn[w, i]) + r[i],
                        name=f"regular_driver_constraint_{m}_{i}"
                    )


        # ========================
        # 4. Flow Balance Constraints - Ensure proper resource routing
        # ========================
        
        # Machine flow balance constraints (if machine bounds are calculated)
        if self.upper_bound == 'machine' or self.upper_bound == "both" or self.upper_bound == 'all':
            
            # Flow conservation: flow into node equals flow out of node
            for m in self.M:
                for i in self.N_m[m]:
                    self.model.addConstr(
                        gp.quicksum(x[m, j, i] for j in self.P_mn[m, i]) ==
                        gp.quicksum(x[m, i, j] for j in self.S_mn[m, i]),
                        name=f"machine_flow_balance_{m}_{i}"
                    )

            # Machine activation constraints: each machine used exactly once from start
            for m in self.M:
                if (m, self.start) in self.S_mn:
                    self.model.addConstr(
                        gp.quicksum(x[m, self.start, j] for j in self.S_mn[m, self.start]) == 1,
                        name=f"machine_start_constraint_{m}"
                    )

        self.model.update()  # Update model to reflect new constraints

        # Attachment flow balance constraints (if attachment bounds are calculated)
        if self.upper_bound == 'attachment' or self.upper_bound == "all":
            
            # Flow conservation: flow into node equals flow out of node
            for a in self.A:
                for i in self.N_a[a]:
                    self.model.addConstr(
                        gp.quicksum(z[a, j, i] for j in self.P_an[a, i]) ==
                        gp.quicksum(z[a, i, j] for j in self.S_an[a, i]),
                        name=f"attachment_flow_balance_{a}_{i}"
                    )

            # Attachment activation constraints: each attachment used exactly once from start
            for a in self.A:
                if (a, self.start) in self.S_an:
                    self.model.addConstr(
                        gp.quicksum(z[a, self.start, j] for j in self.S_an[a, self.start]) == 1,
                        name=f"attachment_start_constraint_{a}"
                    )

        self.model.update()  # Update model to reflect new constraints

        # Worker flow balance constraints (if worker bounds are calculated)
        if self.upper_bound == 'worker' or self.upper_bound == "both" or self.upper_bound == 'all':

            # Flow conservation: flow into node equals flow out of node
            for w in self.W:
                for i in self.N_w[w]:
                    self.model.addConstr(
                        gp.quicksum(y[w, j, i] for j in self.P_wn[w, i]) ==
                        gp.quicksum(y[w, i, j] for j in self.S_wn[w, i]),
                        name=f"worker_flow_balance_{w}_{i}"
                    )

            # Worker activation constraints: each worker used exactly once from start
            for w in self.W:
                if (w, self.start) in self.S_wn:
                    self.model.addConstr(
                        gp.quicksum(y[w, self.start, j] for j in self.S_wn[w, self.start]) == 1,
                        name=f"worker_start_constraint_{w}"
                    )

            # ========================
            # 5. Worker Safety Constraints - Enforce occupational health regulations
            # ========================

            # Maximum consecutive night shifts constraint
            for w in self.W:
                for t in self.T_range:
                    if t <= self.T - self.S_Nmax:
                        # Count night shifts in rolling window of consecutive days
                        self.model.addConstr(
                            gp.quicksum(
                                y[w, i, j] for t_ in range(t, t + self.S_Nmax + 1) if t_ in self.N_r for j in self.N_r[t_]
                                if (w, j) in self.P_wn for i in self.P_wn[w, j]
                            ) <= self.S_Nmax,
                            name=f"night_shift_constraint_{w}_t{t}"
                        )

            # Maximum total shifts in time period constraint
            for w in self.W:
                for t in self.T_range:
                    if t <= self.T - self.T_Smax:
                        # Count all shifts in rolling time window
                        self.model.addConstr(
                            gp.quicksum(
                                y[w, i, j] for t_ in range(t, t + self.T_Smax) if t_ in self.A_r for j in self.A_r[t_]
                                if (w, j) in self.P_wn for i in self.P_wn[w, j]
                            ) <= self.S_max,
                            name=f"shift_number_constraint_{w}_t{t}"
                        )

            # Maximum total working hours constraint
            for w in self.W:
                # Sum of all working hours cannot exceed legal limit
                self.model.addConstr(
                    gp.quicksum(self.t_o[i] * y[w, i, j] for i in self.N_w[w] for j in self.S_wn[w, i]) <= self.T_Wmax,
                    name=f"work_time_constraint_{w}"
                )

        self.model.update()  # Update model to reflect new constraints

        # ========================
        # 6. Site Completion Constraints - Link resource allocation to site fulfillment
        # ========================

        # Machine-only upper bound: sites completed when machines process all orders
        if self.upper_bound == 'machine':
            for c in self.C:
                for i in self.N_c[c]:
                    # Site c is completed if all its order items i are processed by machines
                    self.model.addConstr(
                        gp.quicksum(x[m, i, j] for m in self.M if (m, i) in self.S_mn for j in self.S_mn[m, i]) == u[c],
                        name=f"machine_site_fulfillment_site{c}_order{i}"
                    )

        # Worker-only upper bound: sites completed when workers process all orders
        if self.upper_bound == 'worker':         
            for c in self.C:
                for i in self.N_c[c]:
                    # Site c is completed if all its order items i are processed by workers
                    self.model.addConstr(
                        gp.quicksum(y[w, i, j] for w in self.W if (w, i) in self.S_wn for j in self.S_wn[w, i]) == u[c],
                        name=f"worker_site_fulfillment_site{c}_order{i}"
                    )

        # Attachment-only upper bound: sites completed when attachments process all orders
        if self.upper_bound == 'attachment':
            for c in self.C:
                for i in self.N_c[c]:
                    # For each attachment type required by order item i
                    for k in self.K:
                        if k in self.a_ok[i]:
                            # Required quantity of attachment type k must be allocated to order i
                            self.model.addConstr(
                                gp.quicksum(z[a, i, j] for a in self.A_k[k] if (a, i) in self.S_an for j in self.S_an[a, i]) == self.a_ok[i][k] * u[c],
                                name=f"attachment_site_fulfillment_site{c}_order{i}_type{k}"
                            )

        # Combined machine and worker upper bound: both resources must process orders
        if self.upper_bound == 'both':
            for c in self.C:
                for i in self.N_c[c]:
                    # Site c completed only if both machines and workers process order i
                    self.model.addConstr(
                        gp.quicksum(x[m, i, j] for m in self.M if (m, i) in self.S_mn for j in self.S_mn[m, i]) == u[c],
                        name=f"machine_site_fulfillment_site{c}_order{i}"
                    )
                    self.model.addConstr(
                        gp.quicksum(y[w, i, j] for w in self.W if (w, i) in self.S_wn for j in self.S_wn[w, i]) == u[c],
                        name=f"worker_site_fulfillment_site{c}_order{i}"
                    )

        # All resources upper bound: machines, workers, and attachments must all process orders
        if self.upper_bound == 'all':
            for c in self.C:
                for i in self.N_c[c]:
                    # Site c completed only if machines process order i
                    self.model.addConstr(
                        gp.quicksum(x[m, i, j] for m in self.M if (m, i) in self.S_mn for j in self.S_mn[m, i]) == u[c],
                        name=f"machine_site_fulfillment_site{c}_order{i}"
                    )
                    # Site c completed only if workers process order i
                    self.model.addConstr(
                        gp.quicksum(y[w, i, j] for w in self.W if (w, i) in self.S_wn for j in self.S_wn[w, i]) == u[c],
                        name=f"worker_site_fulfillment_site{c}_order{i}"
                    )
                    # Site c completed only if all required attachments process order i
                    for k in self.K:
                        if k in self.a_ok[i]:
                            self.model.addConstr(
                                gp.quicksum(z[a, i, j] for a in self.A_k[k] if (a, i) in self.S_an for j in self.S_an[a, i]) == self.a_ok[i][k] * u[c],
                                name=f"attachment_site_fulfillment_site{c}_order{i}_type{k}"
                            )

        self.model.update()  # Update model to reflect new constraints
        
        # ========================
        # 7. Model Creation Summary - Display model statistics
        # ========================

        elapsed_time = time.time() - current_time
        print(f" Number of Variables: {self.model.NumVars}")
        print(f" Number of Constraints: {self.model.NumConstrs}")
        print(f" Model created successfully after {elapsed_time:.2f} seconds")


    def solve_model(self):
        """
        Solve the upper bound optimization model using Gurobi.
        
        This method executes the mathematical optimization and reports the
        computation time. The solving process varies between LP relaxation
        (typically very fast) and BIP formulation (potentially time-intensive).
        """
        print("\n Solving...")
        self.model.optimize()

        print(" Solved after {:.2f} seconds".format(self.model.Runtime))
   
    def extract_routes_from_solution(self):
        """
        Extract resource routing information from the optimization solution.
        
        This method processes the binary flow variables to reconstruct the
        scheduling routes for machines, workers, and attachments. It builds
        coherent paths through the flow network representing the order in
        which resources process different order items.
        
        Returns:
            dict: Dictionary containing routing information for each resource type:
                 - 'x': Machine routes {machine_id: [ordered_list_of_order_items]}
                 - 'y': Worker routes {worker_id: [ordered_list_of_order_items]}  
                 - 'z': Attachment routes {attachment_id: [ordered_list_of_order_items]}
        """
        def build_path(transitions):
            """
            Construct a sequential path from flow transitions.
            
            Args:
                transitions: List of (from_node, to_node) tuples representing active flows
                
            Returns:
                list: Ordered sequence of nodes representing the complete route
            """
            # Build adjacency structure from flow transitions
            adj = defaultdict(list)
            incoming = defaultdict(int)

            # Process only integer order item nodes (ignore virtual start/end)
            for f, t in transitions:
                if isinstance(f, int) and isinstance(t, int):
                    adj[f].append(t)
                    incoming[t] += 1

            # Find starting nodes (no incoming flows from other order items)
            all_nodes = set(n for pair in transitions for n in pair if isinstance(n, int))
            start_nodes = [n for n in all_nodes if incoming[n] == 0]

            # Build complete path by following flow transitions
            full_path = []
            visited = set()
            for start in start_nodes:
                current = start
                while current in adj and adj[current]:
                    next_node = adj[current].pop(0)
                    if (current, next_node) not in visited:
                        full_path.append((current, next_node))
                        visited.add((current, next_node))
                        current = next_node
                    else:
                        break

            # Convert transitions to node sequence
            path = [full_path[0][0]] + [t for _, t in full_path] if full_path else []

            # Handle connections to virtual start/end nodes
            for f, t in transitions:
                if f == 'start' and isinstance(t, int) and t not in path:
                    path.insert(0, t)
                elif t == 'end' and isinstance(f, int) and f not in path:
                    path.append(f)

            return path

        # Initialize route storage for all resource types
        routes = {'x': defaultdict(list), 'y': defaultdict(list), 'z': defaultdict(list)}

        # Extract active flow variables from optimization solution
        for var in self.model.getVars():
            if var.VarName.startswith(("x[", "y[", "z[")) and round(var.X) == 1:
                var_type = var.VarName[0]  # x, y, or z
                key = var.VarName.split('[')[1].split(']')[0]
                ent, f, t = key.split(',')

                # Extract resource ID from variable name
                try:
                    ent_id = int(re.search(r'\d+$', ent).group())
                except:
                    continue

                # Parse node identifiers (handle virtual start/end nodes)
                try:
                    f_node = int(f)
                except:
                    f_node = 'start' if f == 'start' else None
                try:
                    t_node = int(t)
                except:
                    t_node = 'end' if t == 'end' else None

                # Store valid flow transitions
                if f_node is not None and t_node is not None:
                    routes[var_type][ent_id].append((f_node, t_node))

        # Build complete routes for each resource
        final_routes = {}
        for k in ['x', 'y', 'z']:
            max_id = max(routes[k].keys()) if routes[k] else -1
            filled = {}
            for i in range(max_id + 1):
                transitions = routes[k].get(i, [])
                filled[i] = build_path(transitions) if transitions else []
            final_routes[k] = dict(sorted(filled.items()))

        return final_routes 


    def execute(self):
        """
        Execute the complete upper bound calculation workflow.
        
        This method orchestrates the full upper bound computation process including
        data preprocessing, model creation, optimization, and result extraction.
        The method returns different outputs based on the bound technique used.
        
        Returns:
            For LP relaxation (standard upper bound):
                list: Site IDs that can be completed (ordered by priority)
                
            For BIP formulation (experimental):
                tuple: (solution_object, objective_value, order_count, runtime, status, gap)
                       where solution_object contains detailed routing information
        """

        # ========================
        # 1. Core Optimization Workflow - Execute main computational steps
        # ========================
        
        self.preprocess_data()           # Transform input data into optimization format
        self.create_optimization_model() # Build mathematical programming model
        self.solve_model()               # Execute optimization with Gurobi

        # ========================
        # 2. Solution Analysis and Output Generation
        # ========================

        if self.model.SolCount > 0:
            # Extract variable names and values from optimization solution
            var_names = self.model.getAttr("VarName", self.model.getVars())
            var_values = self.model.getAttr("X", self.model.getVars())
            print(f" Model objective value: {self.model.objVal}")
            
            # Extract site completion information from u[c] variables
            u_vars = [
                (int(name.split("[")[1].split("]")[0]), val, len(self.N_c[int(name.split("[")[1].split("]")[0])]))
                for name, val in zip(var_names, var_values)
                if name.startswith("u[")
            ]
            
            # Sort sites by completion value (highest first), then by order count, then by site ID
            u_vars_sorted = sorted(u_vars, key=lambda x: (-x[1], x[2], x[0]))
            
            # Calculate total number of completed sites
            order_count = sum(val for name, val in zip(var_names, var_values) if name.startswith("u["))
            int_order_count = int(order_count)
            
            # Extract list of sites that can be completed (top sites up to completion count)
            order_list = [c for c, _, _ in u_vars_sorted[:int_order_count]]

            # ========================
            # 3. Binary Integer Programming Results (Experimental Mode)
            # ========================
            
            if self.bound_technique == 'BIP':
                # Extract detailed solution information for BIP formulation
                objective_value = self.model.objVal
                gap = 0  # Gap calculation (currently disabled)

                # Save model and solution files for analysis
                filename = f"model_{self.data.instance}.lp"
                solution_filename = f"solution_{self.data.instance}.sol"
                save_path = Path.cwd().parent / "Data" / "ModelFiles"/ self.bound_technique / self.data.instance
                save_path.mkdir(parents=True, exist_ok=True)
                self.model.write(str(save_path / solution_filename))
                self.model.write(str(save_path / filename))
                
                # Process solution based on solver status
                if self.model.status == GRB.OPTIMAL or self.model.status == GRB.TIME_LIMIT:
                    # Extract detailed routing information from flow variables
                    routes = self.extract_routes_from_solution()
                    
                    # Create Solution object with worker, machine, and attachment routes
                    solution = Solution(routes['y'], routes['x'], routes['z'], self.data)
                elif self.model.status == GRB.INFEASIBLE:
                    # No feasible solution exists
                    solution = None

                # Return comprehensive BIP results
                return solution, objective_value, order_count, self.model.Runtime, self.model.status, gap
        else:
            # No solution found - return empty list
            order_list = []

        # ========================
        # 4. Standard Upper Bound Results (LP Relaxation)
        # ========================
        
        # Return list of sites that can theoretically be completed
        return order_list
