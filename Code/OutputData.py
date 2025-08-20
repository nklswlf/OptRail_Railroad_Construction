"""
===============================================================================
                    OUTPUT DATA MODULE
===============================================================================

Output Data Management for Railroad Construction Optimization

This module provides comprehensive data structures and algorithms for managing
optimization results in railroad construction scheduling problems. It implements
solution representation, feasibility validation, and Pareto-optimal solution
management for multi-objective optimization scenarios.

Key Components:
- Solution: Complete solution representation with route plans and metrics
- ParetoSolutions: Multi-objective optimization with Pareto front management

The module supports complex constraint validation, solution comparison,
and advanced Pareto front operations including interpolation and dominance
analysis for effective multi-objective decision making.

Dependencies:
- Code.InputData: Problem instance data and constraints
- pandas, numpy: Data manipulation and numerical computations
- plotly: Visualization capabilities for solution analysis
- numba: High-performance numerical operations for Pareto analysis
"""

from Code.InputData import InputData
import json
import pandas as pd
import plotly.express as px
import os
from datetime import timedelta
from collections import Counter
import numpy as np
#import pygmo as pg  # Optional: Advanced hypervolume calculations
import math
from numba import njit




class Solution:
    """
    Comprehensive solution representation for railroad construction scheduling.
    
    This class encapsulates a complete solution to the railroad construction
    optimization problem, including route assignments for all resources
    (workers, machines, attachments) and comprehensive solution metrics.
    
    The solution maintains feasibility through constraint validation and
    provides detailed analytics on resource utilization, distances, and
    order completion status.
    """

    def __init__(self, route_plan_worker:dict, route_plan_machine:dict, data:InputData):
        """
        Initialize a complete solution with route plans for all resource types.
        
        Args:
            route_plan_worker: Dictionary mapping worker IDs to ordered lists of order item IDs
            route_plan_machine: Dictionary mapping machine IDs to ordered lists of order item IDs  
            route_plan_attachment: Dictionary mapping attachment IDs to ordered lists of order item IDs
            data: Input data containing problem instance information and constraints
        """
        # Store input data and route plans
        self.data = data
        self.route_plan_worker = route_plan_worker
        self.route_plan_machine = route_plan_machine
        
        # Order completion status tracking
        self.finished_orders = []              # Completely finished orders
        self.semifinished_orders = []          # Partially completed orders
        self.not_started_orders = []           # Orders with no progress
        self.not_recognized_orders = []        # Orders not found in input data

        # Order item status tracking
        self.not_started_order_item_ids = []   # Unscheduled order items
        self.not_recognized_order_item_ids = [] # Invalid order item references

        # Summary statistics for order completion
        self.share_finished_orders = -0        # Percentage of completed orders
        self.number_of_finished_orders = -0    # Count of fully completed orders
        self.number_of_finished_order_items = -0  # Count of completed order items
        self.number_of_unrecognized_orders = -0   # Count of invalid orders

        # Resource utilization tracking
        self.used_machines = []                # Active machine IDs
        self.used_workers = []                 # Active worker IDs
        self.unused_machines = []              # Idle machine IDs
        self.unused_workers = []               # Idle worker IDs

        # Distance and transportation metrics
        self.transport_distance_per_machine = {}     # Machine-specific transport distances
        self.total_transport_distance = -0           # Total machine transport distance
        self.commute_distance_per_worker = {}        # Worker-specific commute distances
        self.total_commute_distance = -0             # Total worker commute distance
        
        # Resource count metrics
        self.number_of_workers = -0            # Count of utilized workers
        self.number_of_machines = -0           # Count of utilized machines
        self.driver_violation = -0             # Safety constraint violations
        self.desired_work_hours = -0
        self.deviation_from_desired_hours = -0

        # Resource utilization time tracking
        self.worker_work_time = {}             # Working hours per worker
        self.machine_utilization_time = {}     # Utilization hours per machine

        # Dynamic resource allocation metrics
        self.dynamic_percentage_order = {}     # Dynamic allocation percentage per order
        self.total_dynamic_percentage = -0     # Total dynamic allocation percentage


    def __str__(self) -> str:
        """
        Provide comprehensive string representation of solution metrics.
        
        Returns detailed information about order completion, resource utilization,
        constraint violations, and transportation costs for solution analysis.
        
        Returns:
            str: Formatted solution summary with key performance indicators
        """
        return (f"Instance: {self.data.instance}\n"
                f"Number of finished orders: {self.number_of_finished_orders}\n"
                #f"Number of semi-finished orders: {len(self.semifinished_orders)}\n"
                #f"Number of not started orders: {len(self.not_started_orders)}\n"
                #f"Number of unrecognized orders: {self.number_of_unrecognized_orders}\n"
                #f"Dynamic percentage: {self.total_dynamic_percentage}\n"
                #f"Number of finished order items: {self.number_of_finished_order_items}\n"
                f"Driver violation: {self.driver_violation}\n"
                f"Deviation from desired work hours: {round(self.deviation_from_desired_hours, 2)}\n"
                f"Commute distance: {round(self.total_commute_distance, 2)}\n"
                f"Transport distance: {round(self.total_transport_distance, 2)}\n"
                f"Extra Info:\n"
                f"Number of machines: {self.number_of_machines}\n"
                f"Number of workers: {self.number_of_workers}")

    def feasibility_check(self, verbose=False, allverbose=False):
        """
        Comprehensive feasibility validation for the complete solution.
        
        This method performs extensive validation of the solution against all
        problem constraints including resource assignments, timing constraints,
        precedence relationships, worker safety regulations, and equipment
        compatibility requirements.
        
        Validation Categories:
        1. Order Item Feasibility: Consistency across all route plans
        2. Machine Route Feasibility: Timing and capability constraints  
        3. Worker Route Feasibility: Skills, working hours, and safety regulations
        
        Args:
            verbose: Enable detailed output for individual constraint checks
            allverbose: Enable comprehensive output for all validation steps
            
        Returns:
            bool: True if solution satisfies all constraints, False otherwise
        """
        if allverbose:
            print("\nChecking the feasibility of the solution...")

        # ========================
        # 1. Order Item Feasibility Validation
        # ========================
        if verbose:
            print("\nChecking that the assigned order items are present in both route plans...")

        # Verify consistency between machine and worker route assignments
        for machine_route_order_items in self.route_plan_machine.values():
            for order_item in machine_route_order_items:
                if not any(order_item in worker_route for worker_route in self.route_plan_worker.values()):
                    print(f"Order item {order_item} is not present in the worker route.")
                    return False

        # Verify consistency between worker and machine route assignments
        for worker_route in self.route_plan_worker.values():
            for order_item in worker_route:
                if not any(order_item in machine_route for machine_route in self.route_plan_machine.values()):
                    print(f"Order item {order_item} is not present in the machine route.")
                    return False

        # Check for duplicate order items within individual worker routes
        for worker_id, route in self.route_plan_worker.items():
            if len(route) != len(set(route)):
                print(f"Worker {worker_id} has duplicate order items in their route: {route}")
                return False

        # Ensure each order item is assigned to exactly one worker
        all_worker_order_items = [order_item for route in self.route_plan_worker.values() for order_item in route]
        if len(all_worker_order_items) != len(set(all_worker_order_items)):
            print("An order item has been assigned to more than one worker.")
            return False

        # Check for duplicate order items within individual machine routes
        for machine_id, route in self.route_plan_machine.items():
            if len(route) != len(set(route)):
                print(f"Machine {machine_id} has duplicate order items in its route: {route}")
                return False

        # Ensure each order item is assigned to exactly one machine
        all_machine_order_items = [order_item for route in self.route_plan_machine.values() for order_item in route]
        if len(all_machine_order_items) != len(set(all_machine_order_items)):
            print("An order item has been assigned to more than one machine.")
            return False

        if verbose:
            print("The assigned order items are present in both route plans.")

        # ========================
        # 2. Machine Route Feasibility Validation
        # ========================
        for machine_name, route in self.route_plan_machine.items():
            if verbose:
                print(f"\nChecking route for machine {machine_name}...")

            machine_object = next((m for m in self.data.machines if m.id == machine_name), None)
            order_item_objects = [next((o for o in self.data.order_items if o.id == order_id), None) for order_id in route]

            # Validate machine type compatibility with order items
            for order_item in order_item_objects:
                if machine_object.type != order_item.machine_type:
                    print(f"Machine {machine_name} is not correctly assigned to order item {order_item.id}.")
                    return False

            # Validate timing constraints and transportation between consecutive order items
            for i in range(len(order_item_objects) - 1):
                order_item_i = order_item_objects[i]
                order_item_j = order_item_objects[i + 1]
                
                # Find parent orders for distance calculation
                order_i = next((order for order in self.data.orders 
                                if int(order_item_i.id) in [int(item) for item in order.order_item_ids]), None)
                order_j = next((order for order in self.data.orders 
                                if int(order_item_j.id) in [int(item) for item in order.order_item_ids]), None)
                
                # Calculate travel time between sites
                distance = self.data.transport_routes[order_i.site_number][order_j.site_number]
                travel_time_double = distance / self.data._transport_speed_kmh
                travel_time = timedelta(hours=travel_time_double)
                
                # Check timing feasibility with travel time
                if order_item_i.end_time + travel_time > order_item_j.start_time:
                    print(f"In machine route: {machine_name}, Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                    return False

            if verbose:
                print(f"Route for machine {machine_name} is feasible.")
    
        # ========================
        # 3. Worker Route Feasibility Validation
        # ========================
        for worker_id, route in self.route_plan_worker.items():
            if verbose:
                print(f"\nChecking route for worker {worker_id}...")

            worker_object = next((w for w in self.data.workers if w.personal_number == worker_id), None)
            order_item_objects = [next((o for o in self.data.order_items if o.id == order_id), None) for order_id in route]

            # Validate worker qualifications against order item requirements
            for order_item in order_item_objects:
                if order_item.worker_qualifications:
                    if not set(order_item.worker_qualifications).issubset(set(worker_object.qualifications)):
                        print(f"Worker {worker_id} (Qualifications: {worker_object.qualifications}) does not have the correct qualifications for order item {order_item.id} (Required: {order_item.worker_qualifications}).")
                        return False

            # Validate timing constraints with break times between consecutive order items
            for i in range(len(order_item_objects) - 1):
                order_item_i = order_item_objects[i]
                order_item_j = order_item_objects[i + 1]
                break_time_double = self.data._hours_between_shifts
                break_time = timedelta(hours=break_time_double)
                if order_item_i.end_time + break_time > order_item_j.start_time:
                    print(f"In worker route: {worker_id}, Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                    return False

            # Validate maximum consecutive night shifts safety regulation
            checked_indices = set()
            for i, order_item_i in enumerate(order_item_objects):
                if i in checked_indices:
                    continue
                
                # Check if this is a night shift (starts after boundary hour)
                if order_item_i.start_time.hour >= self.data._day_and_night_shift_boundary:
                    night_shifts = 1
                    # Count consecutive night shifts starting from this position
                    for j in range(i + 1, len(order_item_objects)):
                        order_item_j = order_item_objects[j]
                        time_difference = (order_item_j.start_time - order_item_i.start_time).days
                        
                        # Check if next shift is consecutive and also a night shift
                        if time_difference == night_shifts:
                            if order_item_j.start_time.hour >= self.data._day_and_night_shift_boundary:
                                night_shifts += 1
                                checked_indices.add(j)
                            else:
                                break  # Day shift breaks the consecutive night shift sequence
                        else:
                            break  # Non-consecutive shift breaks the sequence
                    
                    # Check maximum consecutive night shifts constraint
                    if night_shifts > self.data._max_consecutive_night_shifts:
                        print(f"Worker {worker_id} has more than {self.data._max_consecutive_night_shifts} consecutive night shifts ({night_shifts}).")
                        return False
                    checked_indices.add(i)

            # Validate maximum shifts in time period regulation
            for i, order_item_i in enumerate(order_item_objects):
                window_start = order_item_i.start_time.date()
                window_end = window_start + self.data._time_period_for_max_shifts
                
                # Count shifts within the time window
                shift_count = sum(1 for order_item_j in order_item_objects 
                                if window_start <= order_item_j.start_time.date() < window_end)
                
                if shift_count > self.data._max_shifts_in_time_period:
                    print(f"Worker {worker_id} has more than {self.data._max_shifts_in_time_period} shifts ({shift_count}) within the {self.data._time_period_for_max_shifts}-day period starting on {window_start}.")
                    return False

            # Validate maximum total working hours constraint
            total_duration_hours = sum(order_item.duration for order_item in order_item_objects)
            if total_duration_hours > self.data._max_working_hours:
                print(f"Worker {worker_id} exceeds the maximum allowed total working hours ({self.data._max_working_hours} hours) with {total_duration_hours:.2f} hours.")
                return False

            if verbose:
                print(f"Route for worker {worker_id} is feasible.")

        if allverbose:
            print("\nFeasibility check completed. Solution is feasible.")
        return True    

    def clone(self):
        """
        Create an efficient shallow copy of the solution with deep-copied route plans.
        
        This method provides memory-efficient solution cloning by avoiding full
        deepcopy overhead while preserving route data integrity. Only the route
        plans are deep-copied since they are modified during optimization.
        
        Returns:
            Solution: New solution instance with copied route plans and shared data reference
        """
        # Create shallow copies of route plans to avoid modification conflicts
        machine_route_plan = {k: v[:] for k, v in self.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in self.route_plan_worker.items()}

        return Solution(
            route_plan_worker=worker_route_plan,
            route_plan_machine=machine_route_plan,
            data=self.data  # Shared reference to immutable input data
        )
       

class ParetoSolutions:
    """
    Advanced Pareto front management for multi-objective railroad construction optimization.
    
    This class implements sophisticated algorithms for maintaining and analyzing
    Pareto-optimal solutions in multi-objective optimization scenarios. It provides
    efficient dominance checking, front purging, interpolation for enhanced solution
    exploration, and comprehensive metrics for solution quality assessment.
    
    Key Features:
    - Dynamic Pareto front maintenance with automatic dominance filtering
    - Interpolated point generation for enhanced solution space exploration
    - High-performance NumPy-based operations with Numba acceleration
    - Comprehensive solution comparison and ranking mechanisms
    - Advanced metrics including hypervolume and spread calculations
    """

    def __init__(self, data:InputData, rng = None):
        """
        Initialize Pareto front management with optimization objectives.
        
        Args:
            data: Input data containing problem instance information
            rng: Random number generator for stochastic operations
        """
        self.data = data
        self.RNG = rng
        self.ParetoFront = []                    # List of non-dominated solutions
        self._front_version = 0                  # Version counter for front changes
        self._last_front_version_for_cache = -1  # Last cached version
        self._interpolated_points_cache = []     # Cached interpolated points
        
        # Caching and performance parameters
        self._min_version_delta = 1              # Minimum version changes before cache refresh
        self.S_threshold = len(self.data.orders) * 10  # Maximum front size for interpolation

        # Multi-objective optimization objectives (all minimization)
        self.objectives = [
            ("total_commute_distance", "min"),           # Worker commute distance
            ("total_transport_distance", "min"),         # Machine transport distance  
            ("driver_violation", "min"),                  # Safety constraint violations
            ("deviation_from_desired_hours", "min"),     # Work hours deviation
            ("number_of_workers", "min"),                # Worker count minimization
            ("number_of_machines", "min"),               # Machine count minimization
        ]

    def PurgeParetoFront(self):
        """
        Remove dominated and duplicate solutions from the Pareto front.
        
        This method performs comprehensive front cleaning by:
        1. Identifying and removing dominated solutions using pairwise comparison
        2. Eliminating duplicate solutions with identical objective values
        3. Maintaining only non-dominated, unique solutions
        
        Uses CompareSolutions for dominance relationships:
        - Returns 1 if solution_a dominates solution_b
        - Returns -1 if solution_b dominates solution_a  
        - Returns 0 if neither dominates the other
        - Returns 100 if solutions are identical
        """
        non_dominated = []
        seen_objective_tuples = set()
        
        for i, sol in enumerate(self.ParetoFront):
            dominated = False
            
            # Create objective tuple for duplicate detection
            obj_tuple = (
                sol.total_commute_distance,
                sol.total_transport_distance,
                sol.driver_violation,
                sol.deviation_from_desired_hours,
                sol.number_of_workers,
                sol.number_of_machines
            )
            
            # Check for duplicate objective values
            if obj_tuple in seen_objective_tuples:
                dominated = True
            else:
                seen_objective_tuples.add(obj_tuple)
            
            # Perform dominance comparison with all other solutions
            for j, other_sol in enumerate(self.ParetoFront):
                if i != j:
                    # If other solution dominates current solution, mark as dominated
                    if self.CompareSolutions(other_sol, sol) == -1:
                        dominated = True
                        break
            
            # Keep only non-dominated solutions
            if not dominated:
                non_dominated.append(sol)
        
        self.ParetoFront = non_dominated

    def UpdateParetoFront(self, new_solution: Solution) -> bool:
        """
        Integrate a new solution into the Pareto front with dominance checking.
        
        This method performs the core Pareto front update operation:
        1. Check if new solution is dominated by any existing solution
        2. Remove all existing solutions dominated by the new solution  
        3. Add new solution if it's non-dominated
        4. Update front version for cache management
        
        Dominance Rules:
        - For all objectives: lower values are better (minimization)
        - Solution A dominates B if A is not worse in any objective and better in at least one
        
        Args:
            new_solution: Candidate solution for Pareto front inclusion
            
        Returns:
            bool: True if solution was added to front, False if dominated or duplicate
        """
        # Check if new solution is dominated by any existing solution
        for current_solution in list(self.ParetoFront):
            comparison_result = self.CompareSolutions(current_solution, new_solution)
            
            if comparison_result == -1:
                # new_solution is dominated by current_solution
                return False
            elif comparison_result == 100:
                # new_solution is identical to current_solution
                return False
            elif comparison_result == 1:
                # current_solution is dominated by new_solution - remove it
                self.ParetoFront.remove(current_solution)
            # comparison_result == 0: neither dominates - both remain

        # Add new solution to Pareto front and update version
        self.ParetoFront.append(new_solution)
        self._front_version += 1
        return True
    
    def CompareSolutions(self, current_solution: Solution, new_solution: Solution) -> int:
        """
        Perform comprehensive dominance comparison between two solutions.
        
        This method implements the mathematical definition of Pareto dominance
        for multi-objective optimization. A solution dominates another if it
        is not worse in any objective and strictly better in at least one.
        
        Comparison Logic:
        - All objectives use minimization (lower is better)
        - Dominance requires being not worse in all objectives AND better in at least one
        - Identical solutions are detected separately
        
        Args:
            current_solution: First solution for comparison
            new_solution: Second solution for comparison
            
        Returns:
            int: 1 if new_solution dominates current_solution
                -1 if current_solution dominates new_solution
                 0 if neither dominates (non-dominated)
               100 if solutions are identical in all objectives
        """
        new_better_count = 0      # Objectives where new_solution is strictly better
        current_better_count = 0  # Objectives where current_solution is strictly better
        identical_count = 0       # Objectives with identical values

        # Compare each objective according to its optimization direction
        for attr, goal in self.objectives:
            new_val = getattr(new_solution, attr)
            curr_val = getattr(current_solution, attr)
            
            if new_val == curr_val:
                identical_count += 1
            elif goal == "max":
                # For maximization objectives (higher is better)
                if new_val > curr_val:
                    new_better_count += 1
                else:
                    current_better_count += 1
            else:  # goal == "min"
                # For minimization objectives (lower is better)
                if new_val < curr_val:
                    new_better_count += 1
                else:
                    current_better_count += 1

        # Determine dominance relationship
        if identical_count == len(self.objectives):
            return 100  # Solutions are identical in all objectives

        if current_better_count == 0 and new_better_count > 0:
            return 1    # new_solution dominates current_solution

        if new_better_count == 0 and current_better_count > 0:
            return -1   # current_solution dominates new_solution

        return 0        # Neither dominates (non-dominated solutions)

    def GenerateInterpolatedPoints(self):
        """
        Generate interpolated points between Pareto-optimal solutions for enhanced exploration.
        
        This advanced algorithm creates synthetic points within the Pareto front
        convex hull to provide better coverage of the objective space. The method
        uses dimensionality-based sampling and dominance checking to ensure all
        generated points are meaningful.
        
        Algorithm Steps:
        1. Extract objective vectors into NumPy array for vectorized operations
        2. Precompute sorted indices and bounds for each objective dimension
        3. Generate candidate points through uniform sampling within bounds
        4. Snap candidate points to existing Pareto front values in random dimensions
        5. Validate points using fast NumPy-based dominance checking
        
        Returns:
            list: Dictionary representations of valid interpolated points
        """
        # Require minimum solutions for meaningful interpolation
        interpolated_points = []
        if len(self.ParetoFront) < 2:
            return interpolated_points

        D = len(self.objectives)  # Number of objectives
        
        # Stack objective vectors into (N, D) NumPy array for vectorized operations
        arr = np.vstack([
            [
                sol.driver_violation,
                sol.deviation_from_desired_hours,
                sol.total_commute_distance,
                sol.total_transport_distance,
                sol.number_of_workers,
                sol.number_of_machines
            ]
            for sol in self.ParetoFront
        ])

        # Precompute sorted indices for efficient dimension-wise access
        sorted_idx = [np.argsort(arr[:, d]) for d in range(D)]
        # Precompute bounds for each objective dimension
        min_vals = arr.min(axis=0)
        max_vals = arr.max(axis=0)

        # Generate samples with adaptive count based on front size
        num_samples = min(100, arr.shape[0])
        for _ in range(num_samples):
            # Sample candidate point uniformly within objective bounds
            v = self.RNG.uniform(min_vals, max_vals, size=D)
            d = int(self.RNG.integers(0, D))  # Random dimension to snap

            # Snap candidate point to existing Pareto values in dimension d
            for idx in sorted_idx[d]:
                u = arr[idx]
                v[d] = u[d]  # Align with existing solution in dimension d
                
                # Check if any Pareto solution dominates this candidate point
                if self.dominates_any(arr, v):
                    interpolated_points.append({
                        "driver_violation": float(v[0]),
                        "deviation_from_desired_hours": float(v[1]),
                        "commute_distance": float(v[2]),
                        "transport_distance": float(v[3]),
                        "worker_count": float(v[4]),
                        "machine_count": float(v[5])
                    })
                    break

        return interpolated_points

    def get_interpolated_points(self):
        """
        Retrieve cached interpolated points with intelligent cache management.
        
        This method implements efficient caching to avoid expensive interpolation
        recalculation. Interpolated points are regenerated only when:
        1. Sufficient Pareto front changes have accumulated
        2. The front size is below the performance threshold
        
        Performance Optimization:
        - Skips interpolation for large fronts (> S_threshold) to maintain performance
        - Uses version-based caching to minimize computational overhead
        - Balances exploration benefits against computational cost
        
        Returns:
            list: Cached or newly generated interpolated points
        """
        # Skip interpolation for large Pareto fronts to maintain performance
        if len(self.ParetoFront) >= self.S_threshold:
            return []
            
        # Regenerate cache only if sufficient front changes have occurred
        if (self._front_version - self._last_front_version_for_cache) >= self._min_version_delta:
            self._interpolated_points_cache = self.GenerateInterpolatedPoints()
            self._last_front_version_for_cache = self._front_version
            
        return self._interpolated_points_cache

    @staticmethod
    @njit
    def dominates_any(arr: np.ndarray, v: np.ndarray) -> bool:
        """
        High-performance dominance checking using Numba JIT compilation.
        
        This method provides optimized dominance verification for interpolated
        point validation. Uses just-in-time compilation for maximum performance
        in computationally intensive Pareto front operations.
        
        Dominance Definition:
        - Array row dominates vector v if: arr[i] <= v componentwise AND arr[i] < v in at least one component
        - Essential for ensuring interpolated points lie within feasible objective space
        
        Args:
            arr: NumPy array of Pareto front objective vectors (N, D)
            v: Candidate vector for dominance checking (D,)
            
        Returns:
            bool: True if any row in arr dominates vector v, False otherwise
        """
        N, D = arr.shape
        for i in range(N):
            less_equal = True       # Check if arr[i] <= v in all components
            strictly_less = False   # Check if arr[i] < v in at least one component
            
            for d in range(D):
                if arr[i, d] > v[d]:
                    less_equal = False
                    break  # Cannot dominate if worse in any objective
                if arr[i, d] < v[d]:
                    strictly_less = True  # Better in this objective
                    
            # Dominance requires both conditions
            if less_equal and strictly_less:
                return True
        return False

    def CountDominatingSolutions(self, new_solution, interpolated_points=None, objective_dict_point=None, solution_point=None):
        """
        Count solutions that dominate a given candidate solution.
        
        This method implements comprehensive dominance counting for solution
        quality assessment. It considers the complete solution space including:
        - Existing Pareto archive solutions
        - Interpolated points for enhanced coverage  
        - Additional reference points for comparison
        
        Applications:
        - Solution ranking and selection
        - Search guidance in multi-objective optimization
        - Performance assessment of optimization algorithms
        
        Args:
            new_solution: Candidate solution (Solution object or objective dictionary)
            interpolated_points: Optional cached interpolated points
            objective_dict_point: Optional additional reference point as dictionary
            solution_point: Optional additional reference solution
            
        Returns:
            tuple: (domination_count, interpolated_points_used)
        """
        # Convert solution to standardized objective dictionary format
        if isinstance(new_solution, Solution):
            objective_dict = {
                "driver_violation": new_solution.driver_violation,
                "deviation_from_desired_hours": new_solution.deviation_from_desired_hours,
                "commute_distance": new_solution.total_commute_distance,
                "transport_distance": new_solution.total_transport_distance,
                "worker_count": new_solution.number_of_workers,
                "machine_count": new_solution.number_of_machines
            }
        elif isinstance(new_solution, dict):
            objective_dict = new_solution
        else:
            raise ValueError("new_solution must be of type Solution or dict.")

        # Generate interpolated points if not provided
        if interpolated_points is None:
            interpolated_points = self.get_interpolated_points()

        # Skip counting if solution already in Pareto front
        if new_solution in self.ParetoFront:
            return 0, interpolated_points

        count = 0
        
        # Count domination from Pareto archive solutions
        for solution in self.ParetoFront:
            if self.ShortCompareSolutions(solution, objective_dict):
                count += 1
                
        # Count domination from interpolated points
        for point in interpolated_points:
            if self.ShortCompareSolutions(point, objective_dict):
                count += 1
                
        # Count domination from additional reference points
        if objective_dict_point is not None:
            if self.ShortCompareSolutions(objective_dict_point, objective_dict):
                count += 1
                
        if solution_point is not None:
            if self.ShortCompareSolutions(solution_point, objective_dict):
                count += 1

        return count, interpolated_points
    
    def ShortCompareSolutions(self, current_solution, objective_dict):
        """
        Efficient dominance check between a solution and objective dictionary.
        
        This streamlined comparison method determines if current_solution dominates
        the candidate represented by objective_dict. Used extensively in dominance
        counting and solution ranking operations.
        
        Dominance Criteria (for minimization objectives):
        - current_solution must be <= objective_dict in all objectives
        - current_solution must be < objective_dict in at least one objective
        
        Args:
            current_solution: Solution object or objective dictionary
            objective_dict: Target objective values as dictionary
            
        Returns:
            bool: True if current_solution dominates objective_dict, False otherwise
        """
        # Convert solution to objective dictionary if needed
        if isinstance(current_solution, dict):
            curr_obj = current_solution
        else:
            # Convert Solution object to objective dictionary
            curr_obj = {
                "driver_violation": current_solution.driver_violation,
                "deviation_from_desired_hours": current_solution.deviation_from_desired_hours,
                "commute_distance": current_solution.total_commute_distance,
                "transport_distance": current_solution.total_transport_distance,
                "machine_count": current_solution.number_of_machines,
                "worker_count": current_solution.number_of_workers
            }

        # Check dominance conditions for all minimization objectives
        is_better_or_equal = True   # Must be not worse in any objective
        is_strictly_better = False  # Must be better in at least one objective

        objectives = [
            "driver_violation",
            "deviation_from_desired_hours",
            "commute_distance",
            "transport_distance",
            "machine_count",
            "worker_count"
        ]

        for key in objectives:
            if curr_obj[key] > objective_dict[key]:
                # current_solution is worse in this objective - cannot dominate
                is_better_or_equal = False
                break
            elif curr_obj[key] < objective_dict[key]:
                # current_solution is strictly better in this objective
                is_strictly_better = True

        # Dominance requires both conditions: not worse anywhere AND better somewhere
        return is_better_or_equal and is_strictly_better

        



    def SortParetoFront(self, criteria: str = None):
        """
        Sort Pareto front with hierarchical criteria prioritization.
        
        This method implements a sophisticated sorting strategy that balances
        primary optimization goals with secondary performance metrics:
        
        Primary Criteria (Fixed Priority):
        1. Number of finished orders (maximization - more completed orders preferred)
        2. Total dynamic percentage (maximization - higher resource efficiency preferred)  
        3. Number of finished order items (maximization - more completed items preferred)
        
        Secondary Criteria (Configurable):
        - Optional criteria parameter moves specified objective to front of secondary ranking
        - All remaining objectives maintain original preference order
        
        Args:
            criteria: Optional secondary sorting criterion to prioritize
                     ('driver_violation', 'commute_distance', 'transport_distance', 
                      'attachment_distance', 'machines', 'workers', 'attachments')
        """
        # Define secondary objectives with their extraction functions
        ordered_objectives = [
            ("driver_violation", lambda x: x.driver_violation),
            ("deviation_from_desired_hours", lambda x: x.deviation_from_desired_hours),
            ("commute_distance", lambda x: x.total_commute_distance),
            ("transport_distance", lambda x: x.total_transport_distance),
            ("machines", lambda x: x.number_of_machines),
            ("workers", lambda x: x.number_of_workers)
        ]

        def sort_key(x):
            # Primary criteria (fixed priority order)
            key = [
                -x.number_of_finished_orders,      # Maximize completed orders
                -x.total_dynamic_percentage,       # Maximize resource efficiency
                -x.number_of_finished_order_items  # Maximize completed items
            ]

            # Add prioritized secondary criterion if specified
            if criteria:
                for name, func in ordered_objectives:
                    if name == criteria:
                        key.append(func(x))  # Prioritize specified criterion
                        break

            # Add remaining secondary criteria in original order
            for name, func in ordered_objectives:
                if name != criteria:
                    key.append(func(x))

            return tuple(key)

        # Apply hierarchical sorting
        self.ParetoFront = sorted(self.ParetoFront, key=sort_key)
    
    def SelectRandomBestSolution(self, all_values: bool = False):
        """
        Select representative solution using random best-objective sampling.
        
        This method provides balanced solution selection by:
        1. Identifying the best value for each individual objective
        2. Finding solutions that achieve each best value
        3. Using normalized scoring for tie-breaking among candidate solutions
        4. Random selection among equally good options for robustness
        
        Selection Strategy:
        - For each objective, find solutions achieving the global optimum
        - Use weighted scoring across other objectives for tie-breaking
        - Prefer solutions with balanced performance across multiple objectives
        
        Args:
            all_values: If True, display best values table instead of selecting solution
            
        Returns:
            Solution: Randomly selected solution from best performers
            None: If all_values=True (displays table instead)
            
        Raises:
            KeyError: If no valid solutions found in Pareto front
        """
        # Define objective extraction functions
        objective_map = {
            "driver_violation": lambda x: x.driver_violation,
            "deviation_from_desired_hours": lambda x: x.deviation_from_desired_hours,
            "commute_distance": lambda x: x.total_commute_distance,
            "transport_distance": lambda x: x.total_transport_distance,
            "machines": lambda x: x.number_of_machines,
            "workers": lambda x: x.number_of_workers
        }

        selected_solutions = []
        best_value_dict = {}

        # Precompute objective values for all solutions (performance optimization)
        solution_values = {sol: {k: func(sol) for k, func in objective_map.items()} for sol in self.ParetoFront}

        # Process each objective independently
        for key in objective_map:
            try:
                # Find global best value for this objective
                values = [vals[key] for vals in solution_values.values()]
                best_value = min(values)  # All objectives are minimization
                best_value_dict[key] = round(best_value, 2)

                # Identify solutions achieving the best value
                candidate_solutions = [sol for sol, vals in solution_values.items() if vals[key] == best_value]

                # If unique best solution, select it directly
                if len(candidate_solutions) == 1:
                    selected_solutions.append(candidate_solutions[0])
                    continue

                # Tie-breaking using normalized scores across other objectives
                normalized_scores = []
                
                # Precompute ranges for normalization
                precomputed_sub_values = {
                    sub_key: [solution_values[s][sub_key] for s in candidate_solutions] 
                    for sub_key in objective_map if sub_key != key
                }
                
                # Calculate normalized scores for each candidate
                for sol in candidate_solutions:
                    score = 0.0
                    for sub_key in objective_map:
                        if sub_key == key:
                            continue  # Skip current objective
                            
                        # Normalize objective value to [0,1] range
                        v_min = min(precomputed_sub_values[sub_key])
                        v_max = max(precomputed_sub_values[sub_key])
                        val = solution_values[sol][sub_key]
                        norm = (val - v_min) / (v_max - v_min) if v_max != v_min else 0.0
                        score += norm
                        
                    normalized_scores.append((score, sol))

                # Select solution with best (lowest) normalized score
                best_sol = min(normalized_scores, key=lambda x: x[0])[1]
                selected_solutions.append(best_sol)

            except ValueError:
                # Handle empty value lists gracefully
                continue

        # Display best values table if requested
        if all_values:
            df = pd.DataFrame(best_value_dict.items(), columns=["Objective", "Best Value"])
            print("\nBest individual values:")
            print(df.to_string(index=False))
            return None

        # Validate that solutions were found
        if not selected_solutions:
            raise KeyError("No solutions found.")

        # Random selection among best solutions for robustness
        return self.RNG.choice(selected_solutions)

    def ShowFront(self):
        """
        Display comprehensive Pareto front analysis with formatted output.
        
        This method creates a detailed tabular representation of the Pareto front
        including all key objectives and solution metrics. The output is formatted
        for readability and automatically saved for further analysis.
        
        Display Features:
        - Hierarchical sorting by primary completion metrics and secondary objectives
        - Rounded distance values for better readability
        - Comprehensive solution indexing for easy reference
        - Automatic CSV export for data analysis and visualization
        
        Output Columns:
        - Solution ID: Sequential identifier for each Pareto solution
        - Orders: Number of fully completed orders
        - Order Items: Number of completed individual order items
        - Driver Violation: Safety constraint violation count
        - Distance Metrics: Commute, machine transport, and attachment transport distances
        - Resource Counts: Number of utilized workers, machines, and attachments
        """
        # Build solution data for tabular display
        solutions = []
        for idx, solution in enumerate(self.ParetoFront):
            solutions.append({
                "Solution ID": idx + 1,
                "Orders": solution.number_of_finished_orders,
                "Order Items": solution.number_of_finished_order_items,
                "Driver Violation": solution.driver_violation,
                "Deviation from Desired Hours": round(solution.deviation_from_desired_hours, 2),
                "Commute Distance": round(solution.total_commute_distance, 2),
                "Transport Machines": round(solution.total_transport_distance, 2),
                "Machines": solution.number_of_machines,
                "Workers": solution.number_of_workers
            })

        # Create formatted DataFrame
        df = pd.DataFrame(solutions)

        # Apply hierarchical sorting (primary completion metrics, then secondary objectives)
        df = df.sort_values(
            by=["Orders", "Order Items", "Driver Violation", "Deviation from Desired Hours", "Commute Distance",
                "Transport Machines", 
                "Machines", "Workers"],
            ascending=[False, False, True, True, True, True, True, True]
        )

        # Display formatted table
        print(df)
        
        # Export to CSV for further analysis
        df.to_csv(self.data.solutions_path / "ParetoFront.csv", index=False)




# Advanced Pareto Front Quality Metrics (Currently Disabled)
# These methods provide sophisticated quality assessment for Pareto fronts
# but require additional dependencies and are currently not in active use

    def CalculateParetoFrontMetrics(self):
        """
        Calculate comprehensive Pareto front quality metrics.
        
        This method computes advanced quality indicators for Pareto front
        assessment including hypervolume and spread metrics. Results are
        automatically saved to CSV for comparative analysis.
        
        Quality Metrics:
        - Hypervolume: Volume of objective space dominated by the front
        - Spread: Distribution uniformity of solutions across the front
        - Front size: Number of non-dominated solutions
        
        Note: Currently disabled due to pygmo dependency requirements
        """
        # Validate non-empty Pareto front
        if not self.ParetoFront:
            print("Pareto Front is empty. Cannot calculate metrics.")
            return

        # Calculate quality metrics
        hv_value, hv_log, hv_sqrt = self.CalculateHypervolume()
        spread_value = self.CalculateSpread()

        # Compile metrics for export
        metrics = {
            "Number of Solutions": len(self.ParetoFront),
            "Reference Point": self.ReferencePoint.tolist(),
            "Hypervolume": hv_value,
            "Hypervolume Log10": hv_log,
            "Hypervolume Sqrt": hv_sqrt,
            "Spread": spread_value,
        }
        
        # Export metrics for analysis
        metrics_df = pd.DataFrame([metrics])
        metrics_df.to_csv(self.data.solutions_path / "pareto_metrics.csv", index=False)

    def SetReferencePoint(self, solution: Solution):
        """
        Configure reference point for hypervolume calculation based on solution.
        
        The reference point defines the worst acceptable values for hypervolume
        computation. It should dominate all Pareto front solutions to ensure
        meaningful hypervolume measurements.
        
        Reference Point Strategy:
        - Use scaled versions of solution objectives with safety margins
        - Apply different scaling factors based on objective characteristics
        - Add small epsilon values to avoid numerical computation issues
        
        Args:
            solution: Reference solution for determining appropriate bounds
            
        Raises:
            ValueError: If solution is None or objectives are not properly set
        """
        if solution is None:
            raise ValueError("Solution cannot be None.")
        
        # Define scaling factors for different objective types
        epsilon = 4      # Standard scaling for count-based objectives
        epsilon_2 = 8    # Enhanced scaling for distance-based objectives
        
        # Calculate scaled reference values with safety margins
        driver = solution.driver_violation * epsilon
        commute = solution.total_commute_distance * epsilon_2
        transport = solution.total_transport_distance * epsilon_2
        workers = solution.number_of_workers * epsilon
        machines = solution.number_of_machines * epsilon

        # Add numerical stability epsilon
        epsilon = 1e-6  
        self.ReferencePoint = np.array([
            driver + epsilon,
            commute + epsilon,
            transport + epsilon,
            workers + epsilon,
            machines + epsilon
        ])

    def CalculateHypervolume(self) -> float:
        """
        Calculate hypervolume indicator for Pareto front quality assessment.
        
        Hypervolume measures the volume of objective space dominated by the
        Pareto front relative to a reference point. Higher hypervolume indicates
        better front quality and broader coverage of the objective space.
        
        Algorithm Requirements:
        - Reference point must be set via SetReferencePoint()
        - All solutions must have consistent objective structure
        - Requires pygmo library for computation (currently disabled)
        
        Objective Order:
        1. driver_violation
        2. total_commute_distance  
        3. total_transport_distance
        4. total_transport_distance_attachments
        5. number_of_workers
        6. number_of_machines
        7. number_of_attachments
        
        Returns:
            tuple: (raw_hypervolume, log10_scaled, sqrt_scaled)
            
        Note: Currently disabled due to pygmo dependency
        """
        # Extract objective vectors from Pareto front
        objs = []
        for sol in self.ParetoFront:
            objs.append([
                sol.driver_violation,
                sol.total_commute_distance,
                sol.total_transport_distance,
                sol.total_transport_distance_attachments,
                sol.number_of_workers,
                sol.number_of_machines,
                sol.number_of_attachments
            ])
        objs = np.array(objs)
        
        # Hypervolume computation using pygmo (currently commented out)
        # hv = pg.hypervolume(objs)
        # hv_value = hv.compute(self.ReferencePoint)
        
        # Apply scaling transformations for different analysis perspectives
        # hv_log = math.log10(hv_value) * 10    # Logarithmic scaling
        # hv_sqrt = math.sqrt(hv_value)         # Square root scaling
        
        # return hv_value, hv_log, hv_sqrt
        
        # Placeholder return for disabled functionality
        return 0, 0, 0

    def CalculateSpread(self):
        """
        Computes the spread (also known as spacing) across all objective values.
        This metric evaluates how evenly the solutions are distributed across the Pareto front.
        """
        if len(self.ParetoFront) < 2:
            print("Cannot compute spread: not enough solutions.")
            return None

        # Extract all objective vectors from Pareto front
        def objective_vector(sol):
            return np.array([
                sol.driver_violation,
                sol.total_commute_distance,
                sol.total_transport_distance,
                sol.total_transport_distance_attachments,
                sol.number_of_workers,
                sol.number_of_machines,
                sol.number_of_attachments
            ])

        # Create a list of all objective vectors
        points = [objective_vector(sol) for sol in self.ParetoFront]

        # Sort the points by the second objective (commute_distance)
        points = sorted(points, key=lambda x: x[1])

        # Compute Euclidean distances between consecutive points
        distances = [np.linalg.norm(points[i + 1] - points[i]) for i in range(len(points) - 1)]

        # Compute the mean of these distances
        d_mean = np.mean(distances)

        # Compute the sum of absolute deviations from the mean distance
        d_sum = sum(abs(d - d_mean) for d in distances)

        # Compute distance between extreme points (endpoints of the front)
        df = np.linalg.norm(points[0] - points[-1])

        # Compute spread using the NSGA-II formula
        spread = (df + d_sum) / (df + (len(distances) * d_mean))

        return spread
        
