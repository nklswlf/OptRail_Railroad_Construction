"""
Mathematical optimization module for railroad construction scheduling using Mixed Integer Programming (MIP).

This module implements a flow-based formulation for optimizing the allocation and scheduling of machines
and workers for railroad construction projects. It uses the Gurobi optimizer to solve complex multi-objective
optimization problems with various constraints including resource availability, temporal dependencies,
safety regulations, and operational requirements.

Key Features:
- Multi-objective optimization strategies (weighted, hierarchical, pareto, epsilon-constraint)
- Machine and worker flow modeling with precedence constraints
- Transport and work distance minimization
- Safety constraint enforcement (night shifts, working hours)
- Site completion tracking and fulfillment optimization
"""

import gurobipy as gp  # Gurobi optimization library for MIP solving
from gurobipy import GRB  # Gurobi constants and enumerations
import json  # JSON handling for solution data export
from pathlib import Path  # Cross-platform path handling
import pandas as pd  # Data manipulation and display
from InputData import *  # Input data classes and preprocessing
from OutputData import *  # Output data structures and solution management
from time import time  # Performance timing measurements
from itertools import groupby  # Grouping utilities for result processing


class FlowFormulation:
    """
    Flow-based Mixed Integer Programming formulation for railroad construction optimization.
    
    This class implements a comprehensive optimization model that schedules machines and workers
    for railroad construction projects while minimizing costs, distances, and resource usage.
    The formulation uses network flow concepts to model the movement of resources between
    construction tasks over time.
    
    The optimization considers multiple objectives:
    - Construction site fulfillment maximization
    - Machine transport distance minimization  
    - Worker travel distance minimization
    - Resource utilization optimization
    - Non-regular driver usage minimization
    
    Attributes:
        data: InputData object containing project information
        model: Gurobi optimization model instance
        objective_strategy: Strategy for handling multiple objectives
        number_of_objectives: Number of objectives to optimize
        pareto_attribut: Specific attribute for Pareto optimization
        pareto_construction: Construction level for Pareto analysis
    """
    
    def __init__(self, data, objective_strategy, number_of_objectives = None, paretto_attribute = None, pareto_construction = None):
        """
        Initialize the FlowFormulation optimization model.
        
        Sets up the optimization framework with input data and objective configuration.
        Initializes all data structures needed for the mathematical formulation including
        sets, parameters, and constraint matrices.
        
        Args:
            data: InputData object containing all project information
            objective_strategy: Strategy for multi-objective optimization
                ('construction_fulfillment', 'costs', 'weighted', 'hierarchical', 
                 'hierarchical_tolerance', 'pareto', 'epsilon_constraint')
            number_of_objectives: Number of objectives to consider (3-6)
            paretto_attribute: Specific attribute for Pareto frontier analysis
            pareto_construction: Construction level constraint for Pareto optimization
        """
        # Core data and model references
        self.data = data  # InputData object with all project information
        self.model = None  # Gurobi model instance (initialized later)
        self.objective_strategy = objective_strategy  # Multi-objective strategy
        self.number_of_objectives = number_of_objectives  # Number of objectives (3-6)
        self.pareto_attribut = paretto_attribute  # Pareto analysis attribute
        self.pareto_construction = pareto_construction  # Pareto construction constraint

        # ========================
        # 1. Sets - Core entities and their relationships
        # ========================
        self.M = []  # Machine identifiers (strings) - all available machines
        self.W_m = {}  # Regular drivers per machine: {machine_id: [driver_ids]}
        self.N_m = {}  # Order items assignable to each machine: {machine_id: [order_item_ids]}
        self.W = []  # Worker identifiers (integers) - all available workers  
        self.N_w = {}  # Order items assignable to each worker: {worker_id: [order_item_ids]}
        self.N = []  # Order item identifiers (integers) - all construction tasks
        self.C = []  # Construction site identifiers (integers) - all project sites
        self.N_c = {}  # Order items per construction site: {site_id: [order_item_ids]}

        # ========================
        # 2. Temporal Parameters - Time-based data structures
        # ========================
        self.start_date = None  # Project start date (datetime object)
        self.end_date = None  # Project end date (datetime object)
        self.O_t = {}  # Order items grouped by start day: {day: [order_item_ids]}
        self.D_r = {}  # Day shift order items by day: {day: [order_item_ids]}
        self.N_r = {}  # Night shift order items by day: {day: [order_item_ids]}
        self.A_r = {}  # All shift order items by day: {day: [order_item_ids]}
        self.O_t_start = {}  # Order items by exact start time: {time: [order_item_ids]}
        self.O_t_end = {}  # Order items by exact end time: {time: [order_item_ids]}
        self.O_t_start_inverted = {}  # Start time lookup: {order_item_id: start_time}
        self.O_t_end_inverted = {}  # End time lookup: {order_item_id: end_time}

        # ========================
        # 3. Flow Network Structure - Precedence and distance relationships
        # ========================
        self.P_mn = {}  # Machine flow predecessors: {(machine, order_item): [predecessor_items]}
        self.S_mn = {}  # Machine flow successors: {(machine, order_item): [successor_items]}
        self.P_wn = {}  # Worker flow predecessors: {(worker, order_item): [predecessor_items]}
        self.S_wn = {}  # Worker flow successors: {(worker, order_item): [successor_items]}
        self.d_ij = []  # Machine transport distance matrix between order items [km]
        self.d_wi = []  # Worker travel distance matrix to order items [km]

        # ========================
        # 4. Time Horizon and Network Nodes - Planning period structure
        # ========================
        self.T_range = []  # List of all planning days: [0, 1, 2, ..., T-1]
        self.T = 0  # Total planning horizon length in days
        self.start = "start"  # Virtual start node for flow networks
        self.end = "end"  # Virtual end node for flow networks

        # ========================
        # 5. Safety and Regulatory Constants - Legal and operational constraints
        # ========================
        self.S_Nmax = data._max_consecutive_night_shifts  # Maximum consecutive night shifts
        self.S_max = data._max_shifts_in_time_period  # Maximum shifts in monitoring period
        self.T_Smax = data._time_period_for_max_shifts.days  # Time period for shift monitoring [days]
        self.T_Wmax = data._max_working_hours  # Maximum working hours per worker [hours]

        # ========================
        # 6. Operational Constants - Physical and temporal parameters
        # ========================
        self.SECONDS_IN_A_DAY = data._seconds_a_day  # Seconds per day conversion factor
        self.TRANSPORT_SPEED = data._transport_speed_kmh * 24  # Machine transport speed [km/day]
        self.TIME_BETWEEN_SHIFTS = data._hours_between_shifts / 24  # Rest period between shifts [days]

        
    def preprocess_data(self):
        """
        Transform raw input data into optimization-ready data structures.
        
        This method processes all input data to create the sets, parameters, and relationships
        needed for the mathematical optimization model. It handles machine-worker assignments,
        temporal scheduling, distance calculations, and precedence relationships.
        
        The preprocessing includes:
        - Machine and worker capability mapping
        - Temporal aggregation by days and shifts
        - Distance matrix computation for transport and travel
        - Precedence constraint generation based on timing and logistics
        - Time horizon calculation and safety parameter setup
        """
        print("\nPreprocessing data...")
        current_time = time()
        
        # ========================
        # 1. Machine Processing - Extract machine capabilities and assignments
        # ========================
        for machine in self.data.machines:
            self.M.append(machine.name)  # Add machine identifier to set
            # Convert driver IDs to integers for optimization model
            self.W_m[machine.name] = [int(driver) for driver in machine.default_drivers]
            self.N_m[machine.name] = []  # Initialize order items list for this machine
            # Find all order items that can be handled by this machine type
            # Find all order items that can be handled by this machine type
            for orderItem in self.data.order_items:
                if orderItem.machine_type == machine.type:
                    self.N_m[machine.name].append(orderItem.id)

        # ========================
        # 2. Worker Processing - Map worker qualifications to compatible order items
        # ========================
        for worker in self.data.workers:
            self.W.append(worker.personal_number)  # Add worker identifier to set
            self.N_w[worker.personal_number] = []  # Initialize order items list for this worker
            # Check each order item for worker qualification compatibility
            for orderItem in self.data.order_items:
                if not orderItem.worker_qualifications:  # No specific qualifications required
                    self.N_w[worker.personal_number].append(orderItem.id)
                # Check if worker has all required qualifications
                elif set(orderItem.worker_qualifications).issubset(set(worker.qualifications)):
                    self.N_w[worker.personal_number].append(orderItem.id)

        # ========================
        # 3. Order Processing - Map construction sites to their order items
        # ========================
        for order in self.data.orders:
            self.C.append(order.site_number)  # Add construction site to set
            # Convert order item IDs to integers and map to site
            self.N_c[order.site_number] = [int(item_id) for item_id in order.order_item_ids]

        # ========================
        # 4. Order Item Temporal Processing - Time-based aggregation and scheduling
        # ========================
        self.N = [orderItem.id for orderItem in self.data.order_items]  # Complete order item set
        self.start_date = self.data.start_date  # Project start reference
        self.end_date = self.data.end_date  # Project end reference

        for orderItem in self.data.order_items:
            orderID = orderItem.id
            # Calculate start time in days from project start
            delta_start = (orderItem.start_time - self.start_date)
            t_start = delta_start.total_seconds() / self.SECONDS_IN_A_DAY
            t_start_int = int(t_start)  # Day index for discrete time modeling

            # Group order items by their start day for temporal constraints
            if t_start_int not in self.O_t:
                self.O_t[t_start_int] = []
            self.O_t[t_start_int].append(orderID)

            # Classify shifts as day or night for safety constraints
            if t_start_int not in self.D_r:
                self.D_r[t_start_int] = []
            if orderItem.start_time.hour <= self.data._day_and_night_shift_boundary:
                self.D_r[t_start_int].append(orderID)  # Day shift classification

            # Night shift classification for consecutive night shift limits
            if t_start_int not in self.N_r:
                self.N_r[t_start_int] = []
            if orderItem.start_time.hour > self.data._day_and_night_shift_boundary:
                self.N_r[t_start_int].append(orderID)  # Night shift classification

            # Aggregate all shifts by day for general shift counting constraints
            if t_start_int not in self.A_r:
                self.A_r[t_start_int] = []
            self.A_r[t_start_int].append(orderID)  # All shifts regardless of time

            # Create exact timing mappings for precedence calculations
            if t_start not in self.O_t_start:
                self.O_t_start[t_start] = []
            self.O_t_start[t_start].append(orderID)
            self.O_t_start_inverted[orderID] = t_start  # Fast lookup: order -> start time

            # Calculate and store end times for completion tracking
            delta_end = (orderItem.end_time - self.start_date)
            t_end = delta_end.total_seconds() / self.SECONDS_IN_A_DAY
            if t_end not in self.O_t_end:
                self.O_t_end[t_end] = []
            self.O_t_end[t_end].append(orderID)
            self.O_t_end_inverted[orderID] = t_end  # Fast lookup: order -> end time

        # ========================
        # 5. Distance Matrix Construction - Calculate transport and travel costs
        # ========================
        # Build machine transport distance matrix between all order item pairs
        for i in self.data.order_items:
            row = []
            for j in self.data.order_items:
                # Find construction sites for both order items
                a = next((k for k, v in self.N_c.items() if i.id in v))
                b = next((k for k, v in self.N_c.items() if j.id in v))
                # Use pre-calculated transport distances between sites
                row.append(self.data.transport_routes[a][b])
            self.d_ij.append(row)

        # Build worker travel distance matrix from workers to order items
        for i in self.data.workers:
            row = []
            for j in self.data.order_items:
                # Find construction site for the order item
                a = next((k for k, v in self.N_c.items() if j.id in v))
                # Use pre-calculated work routes from worker to site
                row.append(self.data.work_routes[i.personal_number][a])
            self.d_wi.append(row)

        # ========================
        # 6. Flow Network Precedence Construction - Build temporal flow relationships
        # ========================

        # Build machine flow precedence relationships
        for m in self.M:
            for n in self.N_m[m]:
                # Initialize virtual start and end nodes for each machine
                if (m, self.start) not in self.P_mn:
                    self.P_mn[m, self.start] = []  # Start has no predecessors
                    self.S_mn[m, self.start] = [self.end]  # Start can go to end (no work)
                if (m, self.end) not in self.P_mn:
                    self.P_mn[m, self.end] = []  # End predecessors added below
                    self.S_mn[m, self.end] = [self.start]  # End connects back to start

                # Every order item can be first (from start) or last (to end)
                self.P_mn[m, n] = [self.start]  # All items can be first
                self.S_mn[m, self.start].append(n)  # Start can flow to this item
                self.P_mn[m, self.end].append(n)  # This item can be last
                self.S_mn[m, n] = [self.end]  # All items can flow to end

                # Calculate temporal precedence based on completion and transport time
                for i in self.N_m[m]:
                    if n != i:  # Don't compare item to itself
                        # Get timing information for both order items
                        start_time_n = self.O_t_start_inverted[n]
                        end_time_n = self.O_t_end_inverted[n]
                        start_time_i = self.O_t_start_inverted[i]
                        end_time_i = self.O_t_end_inverted[i]

                        # Check if item i can precede item n (including transport time)
                        if start_time_n >= end_time_i + self.d_ij[i][n] / self.TRANSPORT_SPEED:
                            self.P_mn[m, n].append(i)  # i can precede n

                        # Check if item n can precede item i (including transport time)
                        if start_time_i > end_time_n + self.d_ij[n][i] / self.TRANSPORT_SPEED:
                            self.S_mn[m, n].append(i)  # n can precede i

        # Build worker flow precedence relationships (similar logic but with rest time)
        for w in self.W:
            for n in self.N_w[w]:
                # Initialize virtual start and end nodes for each worker
                if (w, self.start) not in self.P_wn:
                    self.P_wn[w, self.start] = []  # Start has no predecessors
                    self.S_wn[w, self.start] = [self.end]  # Start can go to end (no work)
                if (w, self.end) not in self.P_wn:
                    self.P_wn[w, self.end] = []  # End predecessors added below
                    self.S_wn[w, self.end] = [self.start]  # End connects back to start

                # Every order item can be first (from start) or last (to end)
                self.P_wn[w, n] = [self.start]  # All items can be first
                self.S_wn[w, self.start].append(n)  # Start can flow to this item
                self.P_wn[w, self.end].append(n)  # This item can be last
                self.S_wn[w, n] = [self.end]  # All items can flow to end

                # Calculate temporal precedence based on completion and rest time
                for i in self.N_w[w]:
                    if n != i:  # Don't compare item to itself
                        # Get timing information for both order items
                        start_time_n = self.O_t_start_inverted[n]
                        end_time_n = self.O_t_end_inverted[n]
                        start_time_i = self.O_t_start_inverted[i]
                        end_time_i = self.O_t_end_inverted[i]

                        # Check if item i can precede item n (including rest time)
                        if start_time_n >= end_time_i + self.TIME_BETWEEN_SHIFTS:
                            self.P_wn[w, n].append(i)  # i can precede n

                        # Check if item n can precede item i (including rest time)
                        if start_time_i >= end_time_n + self.TIME_BETWEEN_SHIFTS:
                            self.S_wn[w, n].append(i)  # n can precede i

        # ========================
        # 7. Time Horizon Calculation - Set up planning period
        # ========================
        day_difference = self.end_date - self.start_date
        self.T_range = list(range(day_difference.days + 1))  # [0, 1, 2, ..., T-1]
        self.T = day_difference.days + 1  # Total planning days
        
        # Alternative calculation based on latest order item (commented out)
        # This would extend horizon only to cover actual work
        '''
        end_date_adjusted = self.start_date
        for orderItem in self.data.order_items:
            if end_date_adjusted < orderItem.start_time:
                end_date_adjusted = orderItem.start_time
        self.T = (end_date_adjusted - self.start_date).days + 1
        '''

        # ========================
        # 8. Order Item Duration Extraction - Store work durations for constraints
        # ========================
        # Extract order item durations for working time constraints
        self.t_o = [orderItem.duration for orderItem in self.data.order_items]

        elapsed_time = time() - current_time
        print("Data preprocessed successfully.")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")


    def create_optimization_model(self):
        """
        Create and configure the Gurobi Mixed Integer Programming model.
        
        This method builds the complete mathematical optimization model including:
        - Decision variables for machine and worker flows
        - Multi-objective function configuration
        - All operational and safety constraints
        - Solver parameter settings
        
        The model uses flow-based formulation where resources move through
        a network of order items with precedence and capacity constraints.
        """
        # Solver configuration parameters
        self.time_limit = 10800  # Maximum solving time in seconds (3 hours)
        thread_limit = 16  # Maximum parallel threads for solving

        # Adjust time limit for multi-round optimization strategies
        if self.first_round == False:
            new_time_limit = self.time_limit - self.first_round_time

        current_time = time()
        print("\nCreating optimization model...")
        self.model = gp.Model("Flow_Formulation")  # Initialize Gurobi model

        # Memory and performance optimization settings (commented out)
        #self.model.setParam('NodefileStart', 0)  # Use disk when >0.5GB memory needed
        #self.model.setParam('NodefileDir', '//Volumes/Daten/Gurobi')  # Temp file directory
        #self.model.setParam('Threads', 1)  # Reduce threads to minimize memory requirements
        #self.model.setParam('MIPFocus', 1)  # Focus on finding feasible solutions quickly
        #self.model.setParam('TimeLimit', 300)  # Shorter time limit for testing
        

        # Create solution output directory structure
        parent_folder = self.data._parent_folder
        solution_path = Path.cwd().parent / "Data" / "Solution_math_model" / parent_folder / self.data.instance / f"{self.number_of_objectives}_Objectives" / self.objective_strategy
        solution_path.mkdir(parents=True, exist_ok=True)
        

        # Configure solver parameters
        self.model.setParam("Threads", thread_limit)  # Set parallel processing threads

        # Set time limits and logging based on optimization round
        if self.first_round == True:
            self.model.setParam("TimeLimit", self.time_limit)  # Full time limit for first round
            self.model.setParam("LogFile", str(solution_path / f"gurobi_{self.data.instance}_{self.objective_strategy}.log"))
        elif self.first_round == False:
            self.model.setParam("TimeLimit", new_time_limit)  # Reduced time for second round
            self.model.setParam("LogFile", str(solution_path / f"gurobi_{self.data.instance}_{self.objective_strategy}_round_2.log"))

        # ========================
        # 1. Decision Variable Creation - Define optimization variables
        # ========================
        # Machine flow variables: x[m,i,j] = 1 if machine m goes from order i to order j
        indices_1 = [(m, i, j) for m in self.M for i in self.N_m[m] for j in self.N_m[m]]  # Order-to-order flows
        indices_2 = [(m, self.start, j) for m in self.M for j in self.N_m[m]]  # Start-to-order flows
        indices_3 = [(m, i, self.end) for m in self.M for i in self.N_m[m]]  # Order-to-end flows
        indices_4 = [(m, self.start, self.end) for m in self.M]  # Direct start-to-end flows (unused machines)
        all_indices = indices_1 + indices_2 + indices_3 + indices_4
        x = self.model.addVars(all_indices, vtype=GRB.BINARY, name="x")  # Binary flow variables

        # Worker flow variables: y[w,i,j] = 1 if worker w goes from order i to order j
        indices_1 = [(w, i, j) for w in self.W for i in self.N_w[w] for j in self.N_w[w]]  # Order-to-order flows
        indices_2 = [(w, self.start, j) for w in self.W for j in self.N_w[w]]  # Start-to-order flows
        indices_3 = [(w, i, self.end) for w in self.W for i in self.N_w[w]]  # Order-to-end flows
        indices_4 = [(w, self.start, self.end) for w in self.W]  # Direct start-to-end flows (unused workers)
        all_indices = indices_1 + indices_2 + indices_3 + indices_4
        y = self.model.addVars(all_indices, vtype=GRB.BINARY, name="y")  # Binary flow variables

        # Non-regular driver utilization: r[i] = 1 if order i uses non-regular driver
        r = self.model.addVars(self.N, vtype=GRB.BINARY, name="r")

        # Site completion tracking: u[c] = 1 if construction site c is completed
        u = self.model.addVars(self.C, vtype=GRB.BINARY, name="u")

        # ========================
        # 2. Objective Function Definition - Configure optimization goals
        # ========================

        # Define individual objective components for multi-objective optimization
        self.construction_fulfillment = gp.quicksum(u[c] for c in self.C)  # Maximize completed sites
        self.machine_transport_distance = gp.quicksum(self.d_ij[i][j] * x[m, i, j] for m in self.M for i in self.N_m[m] for j in self.N_m[m])  # Minimize transport
        self.worker_work_distance = gp.quicksum(2 * self.d_wi[w][i] * y[w, i, j] for w in self.W for i in self.N_w[w] for j in (self.N_w[w] + [self.end]))  # Minimize round-trip travel
        self.machine_usage = gp.quicksum(x[m, self.start, j] for m in self.M for j in self.N_m[m])  # Count used machines
        self.worker_usage = gp.quicksum(y[w, self.start, j] for w in self.W for j in self.N_w[w])  # Count used workers
        self.non_regular_driver_usage = gp.quicksum(r[i] for i in self.N)  # Count non-regular driver usage

        # Configure objective function based on optimization strategy
        if self.objective_strategy == "construction_fulfillment":
            # Single objective: maximize completed construction sites
            self.model.setObjective(self.construction_fulfillment, GRB.MAXIMIZE)

        elif self.objective_strategy == "costs":
            # Cost-based multi-objective optimization with economic weights
            if self.number_of_objectives >= 3:           
                # Primary: Revenue from completed construction (negative for minimization)
                self.model.setObjectiveN(-self.construction_fulfillment, index=0, weight = self.data._construction_revenue)
                # Secondary: Penalty costs for non-regular drivers
                self.model.setObjectiveN(self.non_regular_driver_usage, index=1, weight = self.data._penalty_cost_non_regular_driver)
                # Tertiary: Worker travel costs
                self.model.setObjectiveN(self.worker_work_distance, index=2, weight = self.data._worker_travel_cost_per_km)

            if self.number_of_objectives >= 4:            
                # Quaternary: Machine transport costs
                self.model.setObjectiveN(self.machine_transport_distance, index=3, weight = self.data._machine_transport_cost_per_km)
            
            if self.number_of_objectives >= 5:
                # Quinary: Fixed machine costs
                self.model.setObjectiveN(self.machine_usage, index=4, weight = self.data._machine_fixed_cost)
            
            if self.number_of_objectives == 6:
                # Senary: Fixed worker costs
                self.model.setObjectiveN(self.worker_usage, index=5, weight = self.data._worker_fixed_cost)
            
            


        elif self.objective_strategy == "weighted":
            # Weighted multi-objective optimization with normalized priority-based weights
            
            # Calculate instance-specific characteristics for weight normalization
            len_unique_machine_types = list()
            
            # Analyze machine type diversity per construction site
            for order in self.data.orders:
                machine_types = []
                for orderItemID in order.order_item_ids:
                    orderItemID = int(orderItemID)
                    orderItem = next((orderItem for orderItem in self.data.order_items if orderItem.id == orderItemID))
                    machine_types.append(orderItem.machine_type)

                unique_machine_types = list(set(machine_types))
                len_unique_machine_types.append(len(unique_machine_types))

            # Calculate statistical parameters for weight normalization
            average_order_duration = sum(item.duration for item in self.data.order_items) / len(self.C)
            average_machine_types_per_site = sum(len_unique_machine_types) / len(self.C)
            average_transport_distance = sum(item for row in self.data.transport_routes for item in row if item != 0) / sum(1 for row in self.data.transport_routes for item in row if item != 0) 
            average_order_items_per_site = len(self.N) / len(self.C)
            target_max_share_of_non_regular_drivers = 0.3  # 30% maximum non-regular driver usage
            average_work_distance = sum(item for row in self.d_wi for item in row if item != 0) / sum(1 for row in self.d_wi for item in row if item != 0)
            

            # Define relative priority factors based on AHP (Analytic Hierarchy Process) analysis
            if self.number_of_objectives == 3:
                # Priority weights for 3-objective optimization
                prio_vector = [0.73888889, 0.16018519, 0.10092593, 0, 0, 0]
            elif self.number_of_objectives == 6:
                # Priority weights for 6-objective optimization
                prio_vector = [0.54437184, 0.1707523,  0.12839376, 0.07315951, 0.04935076, 0.03397183]
            
            # Extract individual priority factors for each objective
            factor_construction_fulfillment = prio_vector[0]  # Highest priority
            factor_non_regular_driver = prio_vector[1]  # Second priority
            factor_work_distance = prio_vector[2]  # Third priority
            factor_transport_distance = prio_vector[3]  # Fourth priority           
            factor_machine_usage = prio_vector[4]  # Fifth priority
            factor_worker_usage = prio_vector[5]  # Sixth priority

            # Calculate absolute weight normalization factors based on instance characteristics
            # These weights ensure comparable scaling across different objective magnitudes
            non_regular_driver_usage_weight = average_order_items_per_site * target_max_share_of_non_regular_drivers
            transport_distance_weight = average_machine_types_per_site * 2 * average_transport_distance
            work_distance_weight = average_order_items_per_site * 2 * average_work_distance
            machine_usage_weight = average_machine_types_per_site
            worker_usage_weight = (average_order_duration / self.T_Wmax)

            # Configure multi-objective function with normalized weighted approach
            if self.number_of_objectives >= 3:
                # Primary: Construction fulfillment (maximize, hence negative)
                self.model.setObjectiveN(-self.construction_fulfillment, index=0, weight = 1 * factor_construction_fulfillment)
                # Secondary: Non-regular driver usage (minimize)
                self.model.setObjectiveN(self.non_regular_driver_usage, index=1, weight = (1/non_regular_driver_usage_weight) * factor_non_regular_driver)
                # Tertiary: Worker work distance (minimize)
                self.model.setObjectiveN(self.worker_work_distance, index=2, weight = (1/work_distance_weight) * factor_work_distance)
            
            if self.number_of_objectives >= 4:
                # Quaternary: Machine transport distance (minimize)
                self.model.setObjectiveN(self.machine_transport_distance, index=3, weight = (1/transport_distance_weight) * factor_transport_distance)
            
            if self.number_of_objectives >= 5:
                # Quinary: Machine usage (minimize)
                self.model.setObjectiveN(self.machine_usage, index=4, weight = (1/machine_usage_weight) * factor_machine_usage)
            
            if self.number_of_objectives == 6:
                # Senary: Worker usage (minimize)
                self.model.setObjectiveN(self.worker_usage, index=5, weight = (1/worker_usage_weight) * factor_worker_usage)


        elif self.objective_strategy == "hierarchical":
            # Hierarchical optimization with strict priority ordering (lexicographic)
            if self.number_of_objectives >= 3:
                # Highest priority: Construction fulfillment (no tolerance for deviation)
                self.model.setObjectiveN(-self.construction_fulfillment, index=0, priority = 6, reltol = 0, abstol = 0)
                # Second priority: Non-regular driver usage minimization
                self.model.setObjectiveN(self.non_regular_driver_usage, index=1, priority = 5, reltol = 0, abstol = 0)
                # Third priority: Worker work distance minimization
                self.model.setObjectiveN(self.worker_work_distance, index=2, priority = 4, reltol = 0, abstol = 0)

            if self.number_of_objectives >= 4:           
                # Fourth priority: Machine transport distance minimization
                self.model.setObjectiveN(self.machine_transport_distance, index=3, priority = 3, reltol = 0, abstol = 0)

            if self.number_of_objectives >= 5:
                # Fifth priority: Machine usage minimization
                self.model.setObjectiveN(self.machine_usage, index=4, priority = 2, reltol = 0, abstol = 0)

            if self.number_of_objectives == 6:                   
                # Lowest priority: Worker usage minimization
                self.model.setObjectiveN(self.worker_usage, index=5, priority = 1, reltol = 0, abstol = 0)

        elif self.objective_strategy == "hierarchical_tolerance":
            # Two-round hierarchical optimization with tolerance for lower-priority objectives
            
            if self.first_round == True:
                # First round: Optimize only construction fulfillment
                self.model.setObjectiveN(-self.construction_fulfillment, index=0, priority = 6, reltol = 0, abstol = 0)

            elif self.first_round == False:
                # Second round: Fix construction fulfillment and optimize other objectives with tolerance
                
                # Calculate tolerance parameters based on first round results
                len_unique_machine_types = list()
                for order in self.data.orders:
                    machine_types = []
                    for orderItemID in order.order_item_ids:
                        orderItemID = int(orderItemID)
                        orderItem = next((orderItem for orderItem in self.data.order_items if orderItem.id == orderItemID))
                        machine_types.append(orderItem.machine_type)

                    unique_machine_types = list(set(machine_types))
                    len_unique_machine_types.append(len(unique_machine_types))

                # Calculate average values for tolerance setting
                average_machine_types_per_site = sum(len_unique_machine_types) / len(self.C)
                average_order_items_per_site = len(self.N) / len(self.C)


                # Configure second round objectives with constraints and tolerances
                if self.number_of_objectives >= 3:
                    # Fix construction fulfillment to first round optimal value
                    self.model.addConstr(self.construction_fulfillment == self.first_round_construction, name="ConstructionFulfillmentConstraint")
                    # Non-regular driver usage with absolute tolerance
                    self.model.setObjectiveN(self.non_regular_driver_usage, index=1, priority = 5, reltol = 0, abstol = round(self.first_round_construction * average_order_items_per_site * 0.1))
                    # Worker work distance with relative tolerance (10%)
                    self.model.setObjectiveN(self.worker_work_distance, index=2, priority = 4, reltol = 0.1, abstol = 0)
                
                if self.number_of_objectives >= 4:
                    # Machine transport distance with relative tolerance (10%)
                    self.model.setObjectiveN(self.machine_transport_distance, index=3, priority = 3, reltol = 0.1, abstol = 0)

                if self.number_of_objectives >= 5:           
                    # Machine usage with absolute tolerance
                    self.model.setObjectiveN(self.machine_usage, index=4, priority = 2, reltol = 0, abstol = round(self.first_round_construction * average_machine_types_per_site * 0.1))

                if self.number_of_objectives == 6:                            
                    # Worker usage with no tolerance (strict minimization)
                    self.model.setObjectiveN(self.worker_usage, index=5, priority = 1, reltol = 0, abstol = 0)

        elif self.objective_strategy == "pareto":
            # Pareto frontier analysis - optimize single attribute while fixing construction level
            
            # Fix construction fulfillment to specified level for Pareto analysis
            self.model.addConstr(self.construction_fulfillment == self.pareto_construction, name="ConstructionFulfillmentConstraint")
            
            # Optimize the specified Pareto attribute
            if self.pareto_attribut == "MachineTransportDistance":
                # Primary: Machine transport distance minimization
                self.model.setObjectiveN(self.machine_transport_distance, index=0, priority = 2, weight = 1)
                # Secondary: Worker work distance (for feasibility, data not used)
                self.model.setObjectiveN(self.worker_work_distance, index=1, priority = 1 , weight = 1)
            elif self.pareto_attribut == "WorkerWorkDistance":                
                # Optimize worker work distance
                self.model.setObjectiveN(self.worker_work_distance, index=0, weight = 1)            
            elif self.pareto_attribut == "MachineUsage":
                # Optimize machine usage
                self.model.setObjectiveN(self.machine_usage, index=0, weight = 1)
            elif self.pareto_attribut == "WorkerUsage":    
                # Optimize worker usage
                self.model.setObjectiveN(self.worker_usage, index=0, weight = 1)
            elif self.pareto_attribut == "NonRegularDriverUsage":    
                # Optimize non-regular driver usage
                self.model.setObjectiveN(self.non_regular_driver_usage, index=0, weight = 1)



        elif self.objective_strategy == "epsilon_constraint":
            # Epsilon-constraint method: optimize primary objective subject to constraint bounds
            
            # Primary objective: maximize construction site fulfillment
            self.model.setObjective(self.construction_fulfillment, GRB.MAXIMIZE)

            # Calculate epsilon values (constraint bounds) based on problem instance size
            self.epsilon_machine_use = round(len(self.M) * 0.7)  # Allow up to 70% of machines
            self.epsilon_worker_use = round(len(self.W) * 0.7)  # Allow up to 70% of workers
            
            # Distance constraints based on estimated travel requirements
            self.epsilon_machine_distance = round((len(self.C)/self.epsilon_machine_use) * 500 * 0.7)  # ~70% of estimated distance
            self.epsilon_worker_distance = round((len(self.N)/self.epsilon_worker_use) * 200 * 0.7)  # ~70% of estimated distance
            
            # Limit non-regular driver usage to 20% of order items
            self.epsilon_non_regular_driver_use = round(len(self.N) * 0.2)

            # Add epsilon constraints to limit secondary objectives
            self.model.addConstr(self.machine_transport_distance <= self.epsilon_machine_distance, name="EpsilonMachineDistanceConstraint")
            self.model.addConstr(self.worker_work_distance <= self.epsilon_worker_distance, name="EpsilonWorkerDistanceConstraint")
            self.model.addConstr(self.machine_usage <= self.epsilon_machine_use, name="EpsilonMachineUsageConstraint")
            self.model.addConstr(self.worker_usage <= self.epsilon_worker_use, name="EpsilonWorkerUsageConstraint")
            self.model.addConstr(self.non_regular_driver_usage <= self.epsilon_non_regular_driver_use, name="EpsilonPenaltyCostConstraint")

        # ========================
        # 3. Constraint Addition - Mathematical formulation of operational requirements
        # ========================

        # Machine flow balance constraints - ensure flow conservation for each machine at each order item
        for m in self.M:
            for i in self.N_m[m]:
                # Inflow equals outflow for each machine-order combination
                self.model.addConstr(
                    gp.quicksum(x[m, j, i] for j in self.P_mn[m, i]) ==
                    gp.quicksum(x[m, i, j] for j in self.S_mn[m, i]),
                    name=f"machine_flow_balance_{m}_{i}"
                )

        # Machine initialization constraints - each machine starts exactly once
        for m in self.M:
            if (m, self.start) in self.S_mn:
                # Each machine must start from virtual start node exactly once
                self.model.addConstr(
                    gp.quicksum(x[m, self.start, j] for j in self.S_mn[m, self.start]) == 1,
                    name=f"machine_start_constraint_{m}"
                )

        # Regular driver availability constraints - link machine and worker assignments
        for m in self.M:
            for i in self.N_m[m]:
                # Machine can only work if regular driver available or non-regular driver used
                self.model.addConstr(
                    gp.quicksum(x[m, i, j] for j in self.S_mn[m, i]) <=
                    gp.quicksum(y[w, i, j] for w in self.W_m[m] if (w, i) in self.S_wn for j in self.S_wn[w, i]) + r[i],
                    name=f"regular_driver_constraint_{m}_{i}"
                )
                # Worker flow balance constraints - ensure flow conservation for each worker at each order item
        for w in self.W:
            for i in self.N_w[w]:
                # Inflow equals outflow for each worker-order combination
                self.model.addConstr(
                    gp.quicksum(y[w, j, i] for j in self.P_wn[w, i]) ==
                    gp.quicksum(y[w, i, j] for j in self.S_wn[w, i]),
                    name=f"worker_flow_balance_{w}_{i}"
                )

        # Worker initialization constraints - each worker starts exactly once
        for w in self.W:
            if (w, self.start) in self.S_wn:
                # Each worker must start from virtual start node exactly once
                self.model.addConstr(
                    gp.quicksum(y[w, self.start, j] for j in self.S_wn[w, self.start]) == 1,
                    name=f"worker_start_constraint_{w}"
                )

        # Safety constraint: Consecutive night shift limits
        for w in self.W:
            for t in self.T_range:
                if t <= self.T - self.S_Nmax:
                    # Limit consecutive night shifts within rolling time window
                    self.model.addConstr(
                        gp.quicksum(
                            y[w, i, j] for t_ in range(t, t + self.S_Nmax + 1) if t_ in self.N_r for j in self.N_r[t_]
                            if (w, j) in self.P_wn for i in self.P_wn[w, j]
                        ) <= self.S_Nmax,
                        name=f"night_shift_constraint_{w}_t{t}"
                    )

        # Safety constraint: Maximum shifts in time period
        for w in self.W:
            for t in self.T_range:
                if t <= self.T - self.T_Smax:
                    # Limit total shifts (day + night) within monitoring period
                    self.model.addConstr(
                        gp.quicksum(
                            y[w, i, j] for t_ in range(t, t + self.T_Smax) if t_ in self.A_r for j in self.A_r[t_]
                            if (w, j) in self.P_wn for i in self.P_wn[w, j]
                        ) <= self.S_max,
                        name=f"shift_number_constraint_{w}_t{t}"
                    )

        # Working time constraints - enforce maximum working hours per worker
        for w in self.W:
            # Total working time across all assigned order items must not exceed limit
            self.model.addConstr(
                gp.quicksum(self.t_o[i] * y[w, i, j] for i in self.N_w[w] for j in self.S_wn[w, i]) <= self.T_Wmax,
                name=f"work_time_constraint_{w}"
            )

        # Site completion constraints - link order item completion to site fulfillment
        for c in self.C:
            for i in self.N_c[c]:
                # Site is completed only if all order items completed by machines
                self.model.addConstr(
                    gp.quicksum(x[m, i, j] for m in self.M if (m, i) in self.S_mn for j in self.S_mn[m, i]) == u[c],
                    name=f"machine_site_fulfillment_site{c}_order{i}"
                )
                # Site is completed only if all order items completed by workers
                self.model.addConstr(
                    gp.quicksum(y[w, i, j] for w in self.W if (w, i) in self.S_wn for j in self.S_wn[w, i]) == u[c],
                    name=f"worker_site_fulfillment_site{c}_order{i}"
                )



        elapsed_time = time() - current_time
        print("Optimization model created successfully.")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")


    def solve_model(self):
        """
        Execute the Gurobi optimization solver on the configured model.
        
        This method runs the mathematical optimization and handles different
        solution statuses including optimal solutions, time limits, and
        infeasibility cases.
        
        Returns:
            bool/str: True if optimal solution found, False if infeasible,
                     "solution_with_gap" if time limit reached with solution,
                     "time_limit_exceeded" if no solution found within time limit
        """
        print("\nSolving the model...")
        self.model.optimize()  # Execute Gurobi optimization

        print("Time elapsed: {:.2f} seconds".format(self.model.Runtime))

        # Check solution status and return appropriate result
        if self.model.status == GRB.INFEASIBLE:
            return False  # No feasible solution exists
        elif self.model.status == GRB.OPTIMAL:
            return True  # Optimal solution found
        elif self.model.status == GRB.TIME_LIMIT:
            if self.model.SolCount > 0:
                return "solution_with_gap"  # Feasible solution found but not proven optimal
            else:
                return "time_limit_exceeded"  # No solution found within time limit
   
            


    def postprocess_results(self):
        """
        Extract, analyze, and display optimization results.
        
        This method processes the solved optimization model to extract:
        - Objective function values for all optimization strategies
        - Machine and worker flow assignments and routes
        - Site completion status and resource utilization
        - Distance calculations and working hour summaries
        - Formatted output tables for result visualization
        """
        print("\nPostprocessing results...")

        # ========================
        # 0. Objective Value Extraction - Handle different optimization strategies
        # ========================
        self.objectives = []
        
        # Define objective names based on number of objectives being optimized
        if self.number_of_objectives == 6:
            objective_names = [
                "Construction Fulfillment", "Non-Regular Driver Usage", "Worker Work Distance",
                "Machine Transport Distance", "Machine Usage", "Worker Usage"               
            ]
        elif self.number_of_objectives == 5:
            objective_names = [
                "Construction Fulfillment", "Non-Regular Driver Usage", "Worker Work Distance",
                "Machine Transport Distance", "Machine Usage"
            ]
        elif self.number_of_objectives == 4:
            objective_names = [
                "Construction Fulfillment", "Non-Regular Driver Usage", "Worker Work Distance",
                "Machine Transport Distance"
            ]
        elif self.number_of_objectives == 3:
            objective_names = [
                "Construction Fulfillment", "Non-Regular Driver Usage", "Worker Work Distance"
            ]

        # Extract objective values based on optimization strategy
        if self.objective_strategy in ["weighted", "hierarchical", "costs"]:
            # Multi-objective strategies with indexed objectives
            for i, name in enumerate(objective_names):
                value = self.model.getObjective(index=i).getValue()
                if value < 0:
                    value = value * -1  # Convert negative maximization values to positive
                # Round integer-valued objectives
                if name == "Construction Fulfillment" or name == "Non-Regular Driver Usage" or name == "Machine Usage" or name == "Worker Usage":
                    value = round(value)
                self.objectives.append({"Objective": name, "Value": value})

        elif self.objective_strategy == "hierarchical_tolerance":
            # Two-round strategy: use first round construction value
            self.objectives.append({"Objective": "Construction Fulfillment", "Value": self.first_round_construction})
            
            # Extract remaining objectives from second round
            for i, name in enumerate(objective_names):
                if i == 0:
                    continue  # Skip construction fulfillment (already added)
                value = self.model.getObjective(index=i).getValue()         
                if name == "Non-Regular Driver Usage" or name == "Machine Usage" or name == "Worker Usage":
                    value = round(value)
                self.objectives.append({"Objective": name, "Value": value})

        elif self.objective_strategy == "pareto":
            # Pareto analysis: fixed construction level + optimized attribute
            self.objectives.append({"Objective": "Construction Fulfillment", "Value": self.pareto_construction})
            self.objectives.append({"Objective": self.pareto_attribut, "Value": self.model.getObjective(index=0).getValue()})

        elif self.objective_strategy == "epsilon_constraint":
            # Epsilon-constraint: primary objective + constraint analysis
            construction_fulfillment_value = self.model.getObjective().getValue()
            self.objectives.append({"Objective": "Construction Fulfillment", "Value": construction_fulfillment_value})

            # Extract actual values from epsilon constraints using slack analysis
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
                    slack = constr.getAttr(GRB.Attr.Slack)  # Get constraint slack
                    actual_value = epsilon_value - slack  # Calculate actual usage
                self.objectives.append({"Objective": name, "Value": actual_value})



        # ========================
        # 1. Machine Flow Results - Extract and process machine assignments
        # ========================

        # Collect active machine flows for terminal output
        machine_flows = []
        for m in self.M:
            for i in self.N_m[m]:
                for j in self.N_m[m]:
                    # Check all possible flow types for this machine
                    for flow in [
                        (self.start, j),  # Start to order
                        (i, j),           # Order to order
                        (i, self.end),    # Order to end
                        (self.start, self.end)  # Direct start to end (unused)
                    ]:
                        machine_flow_var = self.model.getVarByName(f"x[{m},{flow[0]},{flow[1]}]")
                        if machine_flow_var and machine_flow_var.x > 0.5:  # Binary variable is active
                            flow_entry = [m, flow[0], flow[1]]
                            if flow_entry not in machine_flows:
                                machine_flows.append(flow_entry)

        # Sort machine flows for readable output
        sorted_machine_flows = []
        for machine, group in groupby(sorted(machine_flows, key=lambda x: x[0]), key=lambda x: x[0]):
            sorted_group = sorted(
                list(group),
                key=lambda x: (
                    0 if x[1] == 'start' else  # Start flows first
                    2 if x[2] == 'end' else    # End flows last
                    1,                         # Regular flows in middle
                    self.O_t_start_inverted.get(x[2], float('inf'))  # Sort by start time
                )
            )
            sorted_machine_flows.extend(sorted_group)

        # Create route plans for Solution object (ordered sequences)
        self.route_plan_machine = {m: [] for m in self.M}
        for m in self.M:
            for i in self.N_m[m]:
                for j in self.N_m[m]:
                    # Find order items assigned to this machine
                    machine_flow_var = self.model.getVarByName(f"x[{m},{i},{j}]")
                    if machine_flow_var and machine_flow_var.x > 0.5 and i not in self.route_plan_machine[m]:
                        self.route_plan_machine[m].append(i)
                # Check for final order items (ending at virtual end node)
                machine_flow_var = self.model.getVarByName(f"x[{m},{i},{self.end}]")
                if machine_flow_var and machine_flow_var.x > 0.5 and i not in self.route_plan_machine[m]:
                    self.route_plan_machine[m].append(i)
        # Sort route plans by chronological order
        for m in self.M:
            self.route_plan_machine[m] = sorted(self.route_plan_machine[m], key=lambda x: self.O_t_start_inverted[x])

        # ========================
        # 2. Worker Flow Results - Extract and process worker assignments
        # ========================

        # Collect active worker flows for terminal output
        worker_flows = []
        for w in self.W:
            for i in self.N_w[w]:
                for j in self.N_w[w]:
                    # Check all possible flow types for this worker
                    for flow in [
                        (self.start, j),  # Start to order
                        (i, j),           # Order to order
                        (i, self.end),    # Order to end
                        (self.start, self.end)  # Direct start to end (unused)
                    ]:
                        worker_flow_var = self.model.getVarByName(f"y[{w},{flow[0]},{flow[1]}]")
                        if worker_flow_var and worker_flow_var.x > 0.5:  # Binary variable is active
                            flow_entry = [w, flow[0], flow[1]]
                            if flow_entry not in worker_flows:
                                worker_flows.append(flow_entry)

        # Sort worker flows for readable output
        sorted_worker_flows = []
        for worker, group in groupby(sorted(worker_flows, key=lambda x: x[0]), key=lambda x: x[0]):
            sorted_group = sorted(
                list(group),
                key=lambda x: (
                    0 if x[1] == 'start' else  # Start flows first
                    2 if x[2] == 'end' else    # End flows last
                    1,                         # Regular flows in middle
                    self.O_t_start_inverted.get(x[2], float('inf'))  # Sort by start time
                )
            )
            sorted_worker_flows.extend(sorted_group)

        # Create route plans for Solution object (ordered sequences)
        self.route_plan_worker = {w: [] for w in self.W}
        for w in self.W:
            for i in self.N_w[w]:
                for j in self.N_w[w]:
                    # Find order items assigned to this worker
                    worker_flow_var = self.model.getVarByName(f"y[{w},{i},{j}]")
                    if worker_flow_var and worker_flow_var.x > 0.5 and i not in self.route_plan_worker[w]:
                        self.route_plan_worker[w].append(i)
                # Check for final order items (ending at virtual end node)
                worker_flow_var = self.model.getVarByName(f"y[{w},{i},{self.end}]")
                if worker_flow_var and worker_flow_var.x > 0.5 and i not in self.route_plan_worker[w]:
                    self.route_plan_worker[w].append(i)
        # Sort route plans by chronological order
        for w in self.W:
            self.route_plan_worker[w] = sorted(self.route_plan_worker[w], key=lambda x: self.O_t_start_inverted[x])


        # ========================
        # 3. Site Fulfillment Analysis - Extract completion status and metrics
        # ========================
        
        # Check which sites were successfully completed
        self.site_fulfillment = {}
        for c in self.C:
            self.site_fulfillment[c] = False
            # Site completion variable u[c] indicates if all orders for site c are fulfilled
            if self.model.getVarByName(f"u[{c}]").x > 0.5:
                self.site_fulfillment[c] = True

        # Calculate aggregated completion metrics
        self.sum_finished_sites = round(sum(self.model.getVarByName(f"u[{c}]").x for c in self.C))
        self.sum_total_sites = len(self.C)
        
        # Count total processed order items across all machines and workers
        self.sum_finished_order_items = round(
            sum(self.model.getVarByName(f"x[{m},{i},{j}]").x for m in self.M for i in self.N_m[m] for j in self.N_m[m]) + 
            sum(self.model.getVarByName(f"x[{m},{i},{self.end}]").x for m in self.M for i in self.N_m[m])
        )
        self.sum_order_items = len(self.N)

        # ========================
        # 4. Resource Utilization Metrics - Calculate machine and worker usage
        # ========================
        
        number_of_machines = len(self.M)
        number_of_workers = len(self.W)
        
        # Count active resources (those that start processing from virtual start node)
        self.number_of_used_worker = round(sum(self.model.getVarByName(f"y[{w},{self.start},{j}]").x for w in self.W for j in self.N_w[w]))
        self.number_of_used_machines = round(sum(self.model.getVarByName(f"x[{m},{self.start},{j}]").x for m in self.M for j in self.N_m[m]))
        
        # Count non-regular drivers required (emergency workforce usage)
        self.non_regular_driver_count = round(sum(self.model.getVarByName(f"r[{i}]").x for i in self.N))

        # ========================
        # 5. Transportation Distance Calculation - Machine travel analysis
        # ========================
        
        # Calculate transport distances for each machine
        self.distance_machine = {}
        for m in self.M:
            self.distance_machine[m] = {"Distance": 0, "Utilization": False}
            for i in self.N_m[m]:
                for j in self.N_m[m]:
                    # Add distance for order-to-order transitions
                    if i != j and self.model.getVarByName(f"x[{m},{i},{j}]").x > 0.5:
                        self.distance_machine[m]["Distance"] += self.d_ij[i][j]
                        self.distance_machine[m]["Utilization"] = True


        # Calculate total machine transport distance
        self.total_distance_machine = sum(self.distance_machine[m]["Distance"] for m in self.M)
        
        # ========================
        # 6. Worker Travel Distance Calculation - Worker movement analysis
        # ========================
        
        # Calculate travel distances for each worker (round trip distances)
        self.distance_worker = {}
        for w in self.W:
            self.distance_worker[w] = 0
            for i in self.N_w[w]:
                for j in self.N_w[w]:
                    # Add round-trip distance for order-to-order transitions
                    if i != j and self.model.getVarByName(f"y[{w},{i},{j}]").x > 0.5:
                        self.distance_worker[w] += 2 * self.d_wi[w][i]  # Round trip distance
                # Add round-trip distance for final order (return to depot)
                if self.model.getVarByName(f"y[{w},{i},end]").x > 0.5:
                    self.distance_worker[w] += 2 * self.d_wi[w][i]  # Round trip distance

        # Calculate total worker travel distance
        self.total_distance_worker = sum(self.distance_worker.values())

        # ========================
        # 7. Working Hours Calculation - Worker time commitment analysis
        # ========================

        # Calculate total working hours for each worker
        self.working_hours = {}
        for w in self.W:
            self.working_hours[w] = 0
            for i in self.N_w[w]:
                for j in self.N_w[w]:
                    # Add processing time for order-to-order assignments
                    if i != j and self.model.getVarByName(f"y[{w},{i},{j}]").x > 0.5:
                        self.working_hours[w] += self.t_o[i]  # Duration of order i

                # Add processing time for final order assignments
                if self.model.getVarByName(f"y[{w},{i},end]").x > 0.5:
                    self.working_hours[w] += self.t_o[i]  # Duration of order i

        # Calculate total working hours across all workers
        self.total_working_hours = sum(self.working_hours.values())

        # ========================
        # 8. Results Display - Create summary tables and terminal output
        # ========================
        
        # Create structured DataFrames for result presentation
        df_machine = pd.DataFrame(sorted_machine_flows, columns=["Machine", "From Order", "To Order"])
        df_worker = pd.DataFrame(sorted_worker_flows, columns=["Worker", "From Order", "To Order"])
        df_site = pd.DataFrame.from_dict(self.site_fulfillment, columns=["Fulfilled"], orient="index")
        df_transport = pd.DataFrame.from_dict(self.distance_machine, orient="index")
        df_worker_transport = pd.DataFrame.from_dict(self.distance_worker, columns=["Distance"], orient="index")
        df_working_hours = pd.DataFrame.from_dict(self.working_hours, columns=["Working Hours"], orient="index")

        # Display comprehensive results summary
        if self.print_results:
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
        """
        Save the optimization results to a JSON output file.
        
        This method converts the optimization solution into a structured JSON format
        containing worker assignments, machine schedules, and site completion data.
        The output file can be used for further analysis or as input to other systems.
        """
        print("\nSaving solution to output file...")

        # ========================
        # 1. Worker Assignment Data Structure - Build worker-centric solution
        # ========================
        solution_data = {"Arbeiterzuweisung": {}}  # Worker assignments

        for w in self.W:
            # Find worker object from input data
            current_worker = next(worker for worker in self.data.workers if worker.personal_number == w)
            
            for i in self.N_w[w]:
                # Find order item object from input data
                current_order_item = next(orderItem for orderItem in self.data.order_items if orderItem.id == i)
                
                for j in self.N_w[w]:
                    # Check if worker w processes order i followed by order j
                    if i != j and self.model.getVarByName(f"y[{w},{i},{j}]").x > 0.5:
                        # Initialize worker entry if not exists
                        if current_worker.name not in solution_data["Arbeiterzuweisung"]:
                            solution_data["Arbeiterzuweisung"][current_worker.name] = []
                        
                        # Create assignment record with all order details
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
                        
                # Handle final order assignments (ending at virtual end node)
                if self.model.getVarByName(f"y[{w},{i},end]").x > 0.5:
                    # Initialize worker entry if not exists
                    if current_worker.name not in solution_data["Arbeiterzuweisung"]:
                        solution_data["Arbeiterzuweisung"][current_worker.name] = []
                    
                    # Create assignment record for final order
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
        # 2. Machine Assignment Data Structure - Build machine-centric solution
        # ========================
        solution_data["Maschinenzuweisung"] = {}  # Machine assignments

        for m in self.M:
            # Find machine object from input data
            current_machine = next(machine for machine in self.data.machines if machine.name == m)
            
            for i in self.N_m[m]:
                # Find order item object from input data
                current_order_item = next(orderItem for orderItem in self.data.order_items if orderItem.id == i)
                
                for j in self.N_m[m]:
                    # Check if machine m processes order i followed by order j
                    if i != j and self.model.getVarByName(f"x[{m},{i},{j}]").x > 0.5:
                        # Initialize machine entry if not exists
                        if current_machine.name not in solution_data["Maschinenzuweisung"]:
                            solution_data["Maschinenzuweisung"][current_machine.name] = []
                        
                        # Create assignment record with all order details
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
                        
                # Handle final order assignments (ending at virtual end node)
                if self.model.getVarByName(f"x[{m},{i},end]").x > 0.5:
                    # Initialize machine entry if not exists
                    if current_machine.name not in solution_data["Maschinenzuweisung"]:
                        solution_data["Maschinenzuweisung"][current_machine.name] = []
                    
                    # Create assignment record for final order
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

        # ========================
        # 3. Solution Metadata - Add computation and performance metrics
        # ========================
        
        # Computation time from Gurobi solver
        solution_data["RechenzeitInSekunden"] = self.model.Runtime

        # Site completion summary
        solution_data["Baustellenanzahl"] = self.sum_total_sites          # Total number of sites
        solution_data["Baustellenfertig"] = self.sum_finished_sites       # Number of completed sites
        solution_data["Baustellebearbeitet"] = self.site_fulfillment      # Detailed site status

        # Order processing summary  
        solution_data["OrderItemsanzahl"] = self.sum_order_items           # Total order items
        solution_data["OrderItemsfertig"] = self.sum_finished_order_items  # Processed order items
        solution_data["NichtregulaereFahrer"] = self.non_regular_driver_count  # Emergency drivers used

        # Machine utilization summary
        solution_data["MaschinenanzahlGesamt"] = len(self.M)               # Total machines available
        solution_data["MaschinenGenutzt"] = self.number_of_used_machines   # Machines actually used
        solution_data["MaschinenGenutztDetails"] = {key: value["Utilization"] for key, value in self.distance_machine.items()}

        # Transportation distance metrics
        solution_data["TransportdistanzGesamt"] = self.total_distance_machine  # Total machine travel
        solution_data["Transportdistanz"] = {key: value["Distance"] for key, value in self.distance_machine.items()}

        # Worker utilization summary
        solution_data["ArbeiteranzahlGesamt"] = len(self.W)                # Total workers available
        solution_data["ArbeiterGenutzt"] = self.number_of_used_worker      # Workers actually used

        # Worker travel distance metrics
        solution_data["ArbeitswegGesamt"] = self.total_distance_worker     # Total worker travel
        solution_data["Arbeitsweg"] = self.distance_worker                 # Individual worker distances

        # Working time metrics
        solution_data["ArbeitszeitGesamt"] = self.total_working_hours       # Total work hours
        solution_data["Arbeitszeit"] = self.working_hours                  # Individual worker hours

        # ========================
        # 4. File Output Management - Save solution to structured directory
        # ========================
        
        # Create directory structure based on instance and strategy
        parent_folder = self.data._parent_folder
        solution_path = Path.cwd().parent / "Data" / "Solution_math_model" / parent_folder / self.data.instance / f"{self.number_of_objectives}_Objectives" / self.objective_strategy
        solution_path.mkdir(parents=True, exist_ok=True)
        
        # Save main solution file with comprehensive data
        output_filename = solution_path / f"Solution_{self.data.instance_filename}"
        with open(output_filename, "w") as output_file:
            json.dump(solution_data, output_file, indent=4)

        print(f"Solution saved to: {output_filename} \n")

        # ========================
        # 5. Objective Values Export - Save strategy-specific results
        # ========================

        # Create summary data with instance metadata and objective values
        output_data = {
            "instance": self.data.instance, 
            "computational_time": self.model.Runtime, 
            "strategy": self.objective_strategy, 
            "results": self.objectives
        }

        # Save objective values to separate analysis file
        output_file = solution_path / f"{self.objective_strategy}_strategy_results_{self.data.instance}.json"
        with open(output_file, mode="w") as file:
            json.dump(output_data, file, indent=4)

        # ========================
        # 6. Optional Variable Export - Debug information (disabled)
        # ========================

        on = False  # Flag to control detailed variable export

        if on:
            solution = {}
            # Export all decision variables (optional debug feature)
            solution = {}  # Dictionary to store variable values
            for var in self.model.getVars():
                # Uncomment line below to only save non-zero variables
                # if round(var.X) > 0:
                solution[var.VarName] = round(var.X)  # Store rounded variable value

            # Save variable export file
            output_filename = solution_path / f"Variables_{self.data.instance_filename}"
            with open(output_filename, "w") as output_file:
                json.dump(solution, output_file, indent=4)

    def time_limit_exceeded(self, reason):
        """
        Handle cases where the optimization solver exceeds time limits.
        
        This method creates appropriate indicator files when the solver cannot
        find an optimal solution within the specified time constraints.
        
        Args:
            reason (str): The specific reason for termination
                         - "time_limit_exceeded": No solution found within time limit
                         - "solution_with_gap": Solution found but not proven optimal
        """
        # ========================
        # 1. Create Directory Structure for Time Limit Indicators
        # ========================

        # Construct file path following same structure as solution files
        parent_folder = self.data._parent_folder
        solution_path = Path.cwd().parent / "Data" / "Solution_math_model" / parent_folder / self.data.instance / f"{self.number_of_objectives}_Objectives" / self.objective_strategy
        solution_path.mkdir(parents=True, exist_ok=True)
        
        # ========================
        # 2. Save Appropriate Indicator File Based on Termination Reason
        # ========================
        
        if reason == "time_limit_exceeded":
            # No feasible solution found within time limit
            output_filename = solution_path / f"TIME_{self.data.instance_filename}"
            with open(output_filename, "w") as output_file:
                output_file.write(f"No solution found within the time limit of {self.time_limit} seconds.")

        elif reason == "solution_with_gap":
            # Solution found but optimality gap remains           
            output_filename = solution_path / f"GAP_{self.data.instance_filename}"
            with open(output_filename, "w") as output_file:
                output_file.write(f"Solution found within the time limit of {self.time_limit} seconds, but with a gap.")

    def execute(self):
        """
        Execute the complete optimization workflow.
        
        This method orchestrates the full optimization process including data preprocessing,
        model creation, solving, and result processing. It handles different optimization
        strategies and manages solution output appropriately.
        
        Returns:
            None or tuple: Returns None for most strategies, may return specific values
                          for certain multi-objective approaches.
        """
        
        # ========================
        # 1. Initialization and Core Optimization Steps
        # ========================
        
        self.first_round = True  # Flag for multi-stage optimization strategies

        # Execute core optimization workflow
        self.preprocess_data()           # Process input data and create data structures
        self.create_optimization_model() # Build mathematical model with variables/constraints
        feasible = self.solve_model()    # Solve optimization problem

        # ========================
        # 2. Single Objective Strategy - Model Export Only
        # ========================
        
        if self.objective_strategy == "single":
            # For single objective, just export model files for analysis
            filename = f"model_{self.data.instance}.lp"           # Linear program file
            solution_filename = f"solution_{self.data.instance}.sol"  # Solution file

            # Create directory based on solver status
            save_path = Path.cwd().parent / "Data" / "ModelFiles" / f"ModelStatus_{self.model.status}" / self.data._parent_folder / self.data.instance
            save_path.mkdir(parents=True, exist_ok=True)

            # Export model and solution files
            self.model.write(str(save_path / filename))
            self.model.write(str(save_path / solution_filename))

            return None

        # ========================
        # 3. Hierarchical Tolerance Strategy - Two-Stage Optimization
        # ========================

        if self.objective_strategy == "hierarchical_tolerance":
            # Handle time limit scenarios for first optimization round
            if feasible == "time_limit_exceeded":
                print("Time limit exceeded.")
                self.time_limit_exceeded("time_limit_exceeded")
                return None, None
            
            if feasible == "solution_with_gap":
                print("Solution found within time limit but with a gap.")
                self.time_limit_exceeded("solution_with_gap")
                return None, None

            # Store first round results for second optimization stage
            self.first_round_construction = round(self.model.getObjective(index=0).getValue() * -1)
            self.first_round_time = self.model.Runtime
            
            # Prepare for second optimization round
            self.first_round = False
            self.create_optimization_model()  # Rebuild model with first round constraints
            feasible = self.solve_model()     # Solve second stage

        # ========================
        # 4. General Time Limit Handling for All Strategies
        # ========================
        
        if feasible == "time_limit_exceeded":
            print("Time limit exceeded.")
            self.time_limit_exceeded("time_limit_exceeded")
            return None, None
        
        if feasible == "solution_with_gap":
            print("Solution found within time limit but with a gap.")
            self.time_limit_exceeded("solution_with_gap")
            return None, None

        # ========================
        # 5. Infeasibility Check - Handle impossible problem instances
        # ========================

        if not feasible:
            print("Model is infeasible.")
            return None, None
        
        # ========================
        # 6. Solution Processing and Output Generation
        # ========================
        
        # Process optimization results and create solution object
        self.postprocess_results()  # Extract variable values and calculate metrics

        # Create Solution object for return to calling application
        MIP_solution = Solution(self.route_plan_worker, self.route_plan_machine, self.data)

        # Return solution object and objective values for further analysis
        return MIP_solution, self.objectives

        