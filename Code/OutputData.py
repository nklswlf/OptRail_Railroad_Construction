from Code.InputData import InputData
import json
import pandas as pd
import plotly.express as px
import os
from datetime import timedelta
from collections import Counter
import numpy as np
import pygmo as pg
import math
from numba import njit




class Solution:

    def __init__(self, route_plan_worker:dict, route_plan_machine:dict, route_plan_attachment:dict, data:InputData):
        ''' Define the attributes for solution'''

        self.data = data
        self.route_plan_worker = route_plan_worker
        self.route_plan_machine = route_plan_machine
        self.route_plan_attachment = route_plan_attachment
        
        self.finished_orders = []
        self.semifinished_orders = []
        self.not_started_orders = []
        self.not_recognized_orders = []

        self.not_started_order_item_ids = []
        self.not_recognized_order_item_ids = []

        self.share_finished_orders = -0
        self.number_of_finished_orders = -0
        self.number_of_finished_order_items = -0
        self.number_of_unrecognized_orders = -0

        self.used_machines = []
        self.used_workers = []
        self.unused_machines = []
        self.unused_workers = []
        self.used_attachments = []
        self.unused_attachments = []

        self.transport_distance_per_machine = {}
        self.total_transport_distance = -0
        self.commute_distance_per_worker = {}
        self.total_commute_distance = -0
        self.transport_distance_per_attachment = {}
        self.total_transport_distance_attachments = -0
        self.number_of_workers = -0
        self.number_of_machines = -0
        self.number_of_attachments = -0
        self.driver_violation = -0
        self.worker_work_time = {}
        self.machine_utilization_time = {}
        self.attachment_utilization_time = {}

        self.dynamic_percentage_order = {}
        self.total_dynamic_percentage = -0


    def __str__(self) -> str:
        ''' Define the string representation of the solution'''
        return (f"Instance: {self.data.instance}\n"
                f"Number of finished orders: {self.number_of_finished_orders}\n"
                f"Number of semi-finished orders: {len(self.semifinished_orders)}\n"
                f"Number of not started orders: {len(self.not_started_orders)}\n"
                f"Number of unrecognized orders: {self.number_of_unrecognized_orders}\n"
                f"Dynamic percentage: {self.total_dynamic_percentage}\n"
                f"Number of finished order items: {self.number_of_finished_order_items}\n"
                f"Driver violation: {self.driver_violation}\n"
                f"Commute distance: {round(self.total_commute_distance, 2)}\n"
                f"Transport distance: {round(self.total_transport_distance, 2)}\n"
                f"Transport distance attachment: {round(self.total_transport_distance_attachments, 2)}\n"
                f"Number of machines: {self.number_of_machines}\n"
                f"Number of workers: {self.number_of_workers}\n"
                f"Number of attachments: {self.number_of_attachments}")

    def feasibility_check(self, verbose=False, allverbose=False):
        """
        Check the feasibility of the solution.
        This function verifies that the assignment of order items to the machine, worker, and attachment routes
        meets all constraints.
        """
        if allverbose:
            print("\nChecking the feasibility of the solution...")

        # ========================
        # 1. Order Item Feasibility
        # ========================
        if verbose:
            print("\nChecking that the assigned order items are present in both route plans...")

        # Check that every order item in the machine routes is present in the worker routes
        for machine_route_order_items in self.route_plan_machine.values():
            for order_item in machine_route_order_items:
                if not any(order_item in worker_route for worker_route in self.route_plan_worker.values()):
                    print(f"Order item {order_item} is not present in the worker route.")
                    return False

        # Check that every order item in the worker routes is present in the machine routes
        for worker_route in self.route_plan_worker.values():
            for order_item in worker_route:
                if not any(order_item in machine_route for machine_route in self.route_plan_machine.values()):
                    print(f"Order item {order_item} is not present in the machine route.")
                    return False

        # Check 1: No duplicates within each worker's route
        for worker_id, route in self.route_plan_worker.items():
            if len(route) != len(set(route)):
                print(f"Worker {worker_id} has duplicate order items in their route: {route}")
                return False

        # Check 2: Each order item appears only in one worker's route overall
        all_worker_order_items = [order_item for route in self.route_plan_worker.values() for order_item in route]
        if len(all_worker_order_items) != len(set(all_worker_order_items)):
            print("An order item has been assigned to more than one worker.")
            return False

        # Check 1: No duplicates within each machine's route
        for machine_id, route in self.route_plan_machine.items():
            if len(route) != len(set(route)):
                print(f"Machine {machine_id} has duplicate order items in its route: {route}")
                return False

        # Check 2: Each order item appears only in one machine's route overall
        all_machine_order_items = [order_item for route in self.route_plan_machine.values() for order_item in route]
        if len(all_machine_order_items) != len(set(all_machine_order_items)):
            print("An order item has been assigned to more than one machine.")
            return False

        # Check: No duplicates within each attachment's route
        # (An order item may appear in different attachment routes but not more than once in the same route)
        for attachment_id, route in self.route_plan_attachment.items():
            if len(route) != len(set(route)):
                print(f"Attachment {attachment_id} has duplicate order items in its route: {route}")
                return False

        # Check that each order item is assigned to the needed attachments with the correct counts
        for machine_route_order_items in self.route_plan_machine.values():
            for order_item_id in machine_route_order_items:
                order_item_object = next((o for o in self.data.order_items if o.id == order_item_id), None)
                if order_item_object is None:
                    print(f"Order Item {order_item_id} was not found in the data.")
                    return False
                if order_item_object.equipment_types:
                    assigned_types = []
                    for attachment_id, route in self.route_plan_attachment.items():
                        if order_item_id in route:
                            attachment_object = self.data.attachments[int(attachment_id)]
                            assigned_types.append(attachment_object.type)

                    required_counts = Counter(order_item_object.equipment_types)
                    assigned_counts = Counter(assigned_types)

                    # Check for too few attachments for each required equipment type
                    for equipment_type, required_count in required_counts.items():
                        if assigned_counts[equipment_type] < required_count:
                            print(f"Order Item {order_item_id} needs {required_count}x Equipment-Type {equipment_type}, "
                                f"but there are only {assigned_counts[equipment_type]} assigned.")
                            return False

                    # Check for too many attachments or attachments that are not needed
                    for equipment_type, assigned_count in assigned_counts.items():
                        if assigned_count > required_counts.get(equipment_type, 0):
                            print(f"Order Item {order_item_id} has {assigned_count}x Equipment-Type {equipment_type} assigned, "
                                f"but only {required_counts.get(equipment_type, 0)} are needed.")
                            return False

        if verbose:
            print("The assigned order items are present in both route plans.")

        # ========================
        # 2. Machine Route Feasibility
        # ========================
        for machine_name, route in self.route_plan_machine.items():
            if verbose:
                print(f"\nChecking route for machine {machine_name}...")

            machine_object = next((m for m in self.data.machines if m.id == machine_name), None)
            order_item_objects = [next((o for o in self.data.order_items if o.id == order_id), None) for order_id in route]

            # Check if the machine type is correct for the order items in the route
            for order_item in order_item_objects:
                if machine_object.type != order_item.machine_type:
                    print(f"Machine {machine_name} is not correctly assigned to order item {order_item.id}.")
                    return False

            # Check the sequence of the order items (using index-based iteration for clarity)
            for i in range(len(order_item_objects) - 1):
                order_item_i = order_item_objects[i]
                order_item_j = order_item_objects[i + 1]
                order_i = next((order for order in self.data.orders 
                                if int(order_item_i.id) in [int(item) for item in order.order_item_ids]), None)
                order_j = next((order for order in self.data.orders 
                                if int(order_item_j.id) in [int(item) for item in order.order_item_ids]), None)
                distance = self.data.transport_routes[order_i.site_number][order_j.site_number]
                travel_time_double = distance / self.data._transport_speed_kmh
                travel_time = timedelta(hours=travel_time_double)
                if order_item_i.end_time + travel_time >= order_item_j.start_time:
                    print(f"In machine route: {machine_name}, Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                    return False

            if verbose:
                print(f"Route for machine {machine_name} is feasible.")
    
        # ========================
        # 3. Worker Route Feasibility
        # ========================
        for worker_id, route in self.route_plan_worker.items():
            if verbose:
                print(f"\nChecking route for worker {worker_id}...")

            worker_object = next((w for w in self.data.workers if w.personal_number == worker_id), None)
            order_item_objects = [next((o for o in self.data.order_items if o.id == order_id), None) for order_id in route]

            # Check if the worker's qualifications meet the requirements of the order items
            for order_item in order_item_objects:
                if order_item.worker_qualifications:
                    if not set(order_item.worker_qualifications).issubset(set(worker_object.qualifications)):
                        print(f"Worker {worker_id} (Qualifications: {worker_object.qualifications}) does not have the correct qualifications for order item {order_item.id} (Required: {order_item.worker_qualifications}).")
                        return False

            # Check the sequence of order items using start/end times and break times
            for i in range(len(order_item_objects) - 1):
                order_item_i = order_item_objects[i]
                order_item_j = order_item_objects[i + 1]
                break_time_double = self.data._hours_between_shifts
                break_time = timedelta(hours=break_time_double)
                if order_item_i.end_time + break_time >= order_item_j.start_time:
                    print(f"In worker route: {worker_id}, Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                    return False

            # Check that the worker does not work more than the maximum allowed consecutive night shifts
            checked_indices = set()
            for i, order_item_i in enumerate(order_item_objects):
                if i in checked_indices:
                    continue
                if order_item_i.start_time.hour >= self.data._day_and_night_shift_boundary:
                    night_shifts = 1
                    for j in range(i + 1, len(order_item_objects)):
                        order_item_j = order_item_objects[j]
                        time_difference = (order_item_j.start_time - order_item_i.start_time).days
                        if time_difference == night_shifts:
                            if order_item_j.start_time.hour >= self.data._day_and_night_shift_boundary:
                                night_shifts += 1
                                checked_indices.add(j)
                            else:
                                break
                        else:
                            break
                    if night_shifts > self.data._max_consecutive_night_shifts:
                        print(f"Worker {worker_id} has more than {self.data._max_consecutive_night_shifts} consecutive night shifts ({night_shifts}).")
                        return False
                    checked_indices.add(i)

            # Check that the worker does not work more than the allowed number of shifts in a given period
            for i, order_item_i in enumerate(order_item_objects):
                window_start = order_item_i.start_time.date()
                window_end = window_start + self.data._time_period_for_max_shifts
                shift_count = sum(1 for order_item_j in order_item_objects if window_start <= order_item_j.start_time.date() < window_end)
                if shift_count > self.data._max_shifts_in_time_period:
                    print(f"Worker {worker_id} has more than {self.data._max_shifts_in_time_period} shifts ({shift_count}) within the {self.data._time_period_for_max_shifts}-day period starting on {window_start}.")
                    return False

            # Check that the worker does not work more than the maximum allowed total working hours
            total_duration_hours = sum(order_item.duration for order_item in order_item_objects)
            if total_duration_hours > self.data._max_working_hours:
                print(f"Worker {worker_id} exceeds the maximum allowed total working hours ({self.data._max_working_hours} hours) with {total_duration_hours:.2f} hours.")
                return False

            if verbose:
                print(f"Route for worker {worker_id} is feasible.")

        # ========================
        # 4. Attachment Route Feasibility
        # ========================
        for attachment_id, route in self.route_plan_attachment.items():
            if verbose:
                print(f"\nChecking route for attachment {attachment_id}...")

            attachment_object = next((a for a in self.data.attachments if a.id == attachment_id), None)
            order_item_objects = [next((o for o in self.data.order_items if o.id == order_id), None) for order_id in route]

            # Check if the attachment's type is valid for the order items in the route
            for order_item in order_item_objects:
                if attachment_object.type not in order_item.equipment_types:
                    print(f"Attachment {attachment_id} is not correctly assigned to order item {order_item.id}.")
                    return False

            # Check the sequence of order items using start/end times and travel times
            for i in range(len(order_item_objects) - 1):
                order_item_i = order_item_objects[i]
                order_item_j = order_item_objects[i + 1]
                order_i = next((order for order in self.data.orders 
                                if int(order_item_i.id) in [int(item) for item in order.order_item_ids]), None)
                order_j = next((order for order in self.data.orders 
                                if int(order_item_j.id) in [int(item) for item in order.order_item_ids]), None)
                distance = self.data.transport_routes[order_i.site_number][order_j.site_number]
                travel_time_double = distance / self.data._transport_speed_kmh
                travel_time = timedelta(hours=travel_time_double)
                if order_item_i.end_time + travel_time >= order_item_j.start_time:
                    print(f"Route {route}")
                    print(f"In attachment {attachment_id} route: Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                    return False

            if verbose:
                print(f"Route for attachment {attachment_id} is feasible.")

        if allverbose:
            print("\nFeasibility check completed. Solution is feasible.")
        return True    

    def clone(self):
        """
        Creates a shallow copy of the solution object with deep-copied route plans.
        This avoids full deepcopy overhead, while preserving route data integrity.
        """
        machine_route_plan = {k: v[:] for k, v in self.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in self.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in self.route_plan_attachment.items()}

        return Solution(
            route_plan_worker=worker_route_plan,
            route_plan_machine=machine_route_plan,
            route_plan_attachment=attachment_route_plan,
            data=self.data
        )
       

class ParetoSolutions:
    ''' Class for creating lits objects containing solution objects'''

    def __init__(self, data:InputData, rng = None):
        self.data = data
        self.RNG = rng
        self.ParetoFront = []
        self._front_version = 0
        self._last_front_version_for_cache = -1
        self._interpolated_points_cache = []
        # Minimum number of front-version increments before regenerating samples
        self._min_version_delta = 1
        # Maximum Pareto front size beyond which no interpolation is done
        self.S_threshold = 200

    def PurgeParetoFront(self):
        """
        Iterates over all solutions in the Pareto Front (self.ParetoFront) and removes any solution 
        that is dominated by another solution in the list, or that is completely identical in all objectives.
        
        The function CompareSolutions(solution_a, solution_b) is available:
        - Returns 1 if solution_a dominates solution_b.
        - Returns -1 if solution_b dominates solution_a.
        - Returns 0 if neither dominates the other.
        
        After execution, self.ParetoFront contains only non-dominated, unique solutions.
        """
        non_dominated = []
        seen_objective_tuples = set()
        
        for i, sol in enumerate(self.ParetoFront):
            dominated = False
            
            # Create a tuple of objective values. Adjust the order if necessary.
            obj_tuple = (
                sol.total_commute_distance,
                sol.total_transport_distance,
                sol.total_transport_distance_attachments,
                sol.driver_violation,
                sol.number_of_workers,
                sol.number_of_machines,
                sol.number_of_attachments
            )
            
            # If an identical solution has already been seen, mark this solution as dominated.
            if obj_tuple in seen_objective_tuples:
                dominated = True
            else:
                seen_objective_tuples.add(obj_tuple)
            
            # Compare with all other solutions in the Pareto Front.
            for j, other_sol in enumerate(self.ParetoFront):
                if i != j:
                    if self.CompareSolutions(other_sol, sol) == -1:
                        dominated = True
                        break
            
            if not dominated:
                non_dominated.append(sol)
        
        self.ParetoFront = non_dominated

    def UpdateParetoFront(self, new_solution: Solution) -> bool:
        """
        Compares new_solution with all solutions in the Pareto Front.
        
        If new_solution is dominated by any solution in the Pareto Front,
        it is not added and the function returns False.
        
        Otherwise, it removes all solutions that are dominated by new_solution,
        adds new_solution to the Pareto Front, and returns True.
        
        For total_dynamic_percentage: higher is better.
        For all other objectives: lower is better.
        
        Returns:
        True if new_solution can be added to the Pareto Front,
        False if it is dominated by an existing solution.
        """
        # First, check if any solution in the Pareto Front dominates new_solution.
        for current_solution in list(self.ParetoFront):
            # CompareSolutions returns:
            #   1  if new_solution dominates current_solution,
            #  -1  if current_solution dominates new_solution,
            #   0  if neither dominates the other.
            # 100  if both solutions are identical.
            if self.CompareSolutions(current_solution, new_solution) == -1:
                # new_solution is dominated by current_solution.
                return False
            if self.CompareSolutions(current_solution, new_solution) == 100:
                # new_solution is identical to current_solution.
                return False
            if self.CompareSolutions(current_solution, new_solution) == 1:
                # current_solution is dominated by new_solution.
                self.ParetoFront.remove(current_solution)
            if self.CompareSolutions(current_solution, new_solution) == 0:
                # current_solution and new_solution are not dominated by each other.
                continue

        # Add new_solution to the Pareto Front.
        self.ParetoFront.append(new_solution)
        self._front_version += 1
        return True
    
    def CompareSolutions(self, current_solution: Solution, new_solution: Solution) -> int:
        """
        Compares current_solution and new_solution.
        
        Returns:
        1  if new_solution dominates current_solution,
        -1 if current_solution dominates new_solution,
        0  if neither dominates the other.
        100 if both solutions are identical.
        
        For total_dynamic_percentage: higher is better.
        For all other objectives: lower is better.
        
        A solution dominates another if it is not worse in any objective and is strictly better in at least one.
        """
        objectives = [
            ("total_commute_distance", "min"),
            ("total_transport_distance", "min"),
            ("total_transport_distance_attachments", "min"),
            ("driver_violation", "min"),
            ("number_of_workers", "min"),
            ("number_of_machines", "min"),
            ("number_of_attachments", "min")
        ]
        
        new_better_count = 0  # Anzahl der Ziele, in denen new_solution besser ist
        current_better_count = 0  # Anzahl der Ziele, in denen current_solution besser ist
        identical_count = 0  # Anzahl der identischen Werte

        for attr, goal in objectives:
            new_val = getattr(new_solution, attr)
            curr_val = getattr(current_solution, attr)
            
            if new_val == curr_val:
                identical_count += 1
            elif goal == "max":
                if new_val > curr_val:
                    new_better_count += 1
                else:
                    current_better_count += 1
            else:  # goal == "min"
                if new_val < curr_val:
                    new_better_count += 1
                else:
                    current_better_count += 1

        # Falls alle Werte identisch sind, return 100
        if identical_count == len(objectives):
            return 100

        # new_solution dominiert current_solution
        if current_better_count == 0 and new_better_count > 0:
            return 1

        # current_solution dominiert new_solution
        if new_better_count == 0 and current_better_count > 0:
            return -1

        return 0  # Keine Dominanz

    def GenerateInterpolatedPoints(self):
        """
        Generates interpolated points between Pareto-optimal solutions.
        Uses NumPy to vectorize bounds extraction and dominance checks for performance.
        """
        # Require at least two solutions to interpolate
        interpolated_points = []
        if len(self.ParetoFront) < 2:
            return interpolated_points

        D = 7
        # Stack objective vectors into an (N, D) NumPy array
        arr = np.vstack([
            [
                sol.driver_violation,
                sol.total_commute_distance,
                sol.total_transport_distance,
                sol.total_transport_distance_attachments,
                sol.number_of_workers,
                sol.number_of_machines,
                sol.number_of_attachments
            ]
            for sol in self.ParetoFront
        ])

        # Precompute sorted indices for each dimension
        sorted_idx = [np.argsort(arr[:, d]) for d in range(D)]
        # Precompute min and max for each dimension
        min_vals = arr.min(axis=0)
        max_vals = arr.max(axis=0)

        num_samples = min(100, arr.shape[0])
        for _ in range(num_samples):
            # Sample uniformly within bounds
            v = self.RNG.uniform(min_vals, max_vals, size=D)
            d = int(self.RNG.integers(0, D))

            # Snap v[d] down to the nearest Pareto-front value in dimension d
            for idx in sorted_idx[d]:
                u = arr[idx]
                if np.all(u <= v) and np.any(u < v):
                    v[d] = u[d]
                    break

            # Check if any Pareto solution dominates v using JIT-compiled function
            if self.dominates_any(arr, v):
                interpolated_points.append({
                    "driver_violation": float(v[0]),
                    "commute_distance": float(v[1]),
                    "transport_distance": float(v[2]),
                    "attachment_distance": float(v[3]),
                    "worker_count": float(v[4]),
                    "machine_count": float(v[5]),
                    "attachment_count": float(v[6])
                })

        return interpolated_points

    def get_interpolated_points(self):
        """
        Returns cached interpolated points, regenerating only if enough version increments have accumulated.
        """
        # If the Pareto front has grown too large, skip interpolation
        if len(self.ParetoFront) >= self.S_threshold:
            return []
        # Regenerate only if enough version increments have accumulated
        if (self._front_version - self._last_front_version_for_cache) >= self._min_version_delta:
            self._interpolated_points_cache = self.GenerateInterpolatedPoints()
            self._last_front_version_for_cache = self._front_version
        return self._interpolated_points_cache

    @staticmethod
    @njit
    def dominates_any(arr: np.ndarray, v: np.ndarray) -> bool:
        """
        Returns True if any row of arr dominates vector v (arr[i] <= v componentwise and < v in at least one component).
        """
        N, D = arr.shape
        for i in range(N):
            less_equal = True
            strictly_less = False
            for d in range(D):
                if arr[i, d] > v[d]:
                    less_equal = False
                    break
                if arr[i, d] < v[d]:
                    strictly_less = True
            if less_equal and strictly_less:
                return True
        return False

    def CountDominatingSolutions(self, new_solution, interpolated_points=None):
        """
        Zählt, wie viele Lösungen aus der Pareto-Front die new_solution dominieren.
        Implementiert Algorithmus 2 mit slices und Feasibility-Check für interpolierte Punkte.
        """
        if isinstance(new_solution, Solution):
            objective_dict = {
                "driver_violation": new_solution.driver_violation,
                "commute_distance": new_solution.total_commute_distance,
                "transport_distance": new_solution.total_transport_distance,
                "attachment_distance": new_solution.total_transport_distance_attachments,
                "worker_count": new_solution.number_of_workers,
                "machine_count": new_solution.number_of_machines,
                "attachment_count": new_solution.number_of_attachments
            }
        elif isinstance(new_solution, dict):
            objective_dict = new_solution
        else:
            raise ValueError("new_solution must be of type Solution or dict.")

        # Interpolierte Punkte erzeugen (Algorithmus 2 mit Slicing und Feasibility)
        if interpolated_points is None:
            interpolated_points = self.get_interpolated_points()

        count = 0
        for solution in self.ParetoFront:
            if self.ShortCompareSolutions(solution, objective_dict):
                count += 1
        for point in interpolated_points:
            if self.ShortCompareSolutions(point, objective_dict):
                count += 1

        return count, interpolated_points
    
    def ShortCompareSolutions(self, current_solution, objective_dict):
        """
        Prüft, ob current_solution die neue Lösung (objective_dict) dominiert.
        
        "Dominanz" bedeutet hier:
        - current_solution ist in jedem Zielwert <= objective_dict (nicht schlechter)
        - und in mindestens einem Zielwert < objective_dict (strictly better)
        
        Rückgabe:
        True,  wenn current_solution die new_solution dominiert
        False, sonst
        """

        # 1. Falls current_solution noch kein Dict ist, wandle es in ein Dict um
        if isinstance(current_solution, dict):
            curr_obj = current_solution
        else:
            # Falls es ein Solution-Objekt ist
            curr_obj = {
                "driver_violation": current_solution.driver_violation,
                "commute_distance": current_solution.total_commute_distance,
                "transport_distance": current_solution.total_transport_distance,
                "attachment_distance": current_solution.total_transport_distance_attachments,
                "machine_count": current_solution.number_of_machines,
                "worker_count": current_solution.number_of_workers,
                "attachment_count": current_solution.number_of_attachments
            }

        # 2. Bestimme, ob current_solution <= objective_dict für alle Ziele
        #    und in mindestens einem Ziel < objective_dict
        is_better_or_equal = True
        is_strictly_better = False

        # Liste aller Ziele, bei denen "kleiner = besser" gilt
        objectives = [
            "driver_violation",
            "commute_distance",
            "transport_distance",
            "attachment_distance",
            "machine_count",
            "worker_count",
            "attachment_count"
        ]

        for key in objectives:
            if curr_obj[key] > objective_dict[key]:
                # current_solution ist schlechter in diesem Ziel
                is_better_or_equal = False
                break
            elif curr_obj[key] < objective_dict[key]:
                # current_solution ist in diesem Ziel strictly besser
                is_strictly_better = True

        # 3. Dominanzbedingung: in allen Zielen <= und in mindestens einem < 
        return is_better_or_equal and is_strictly_better

        



    def SortParetoFront(self, criteria: str = None):
        '''
        Sorts the Pareto front:
        - Always starts with: finished_orders, dynamic_percentage, order_items
        - Then: given `criteria` (if any), moved forward in original order
        - Then: all remaining objectives in original order
        '''

        # Feste Reihenfolge der sekundären Ziele (wird nicht verändert)
        ordered_objectives = [
            ("driver_violation", lambda x: x.driver_violation),
            ("commute_distance", lambda x: x.total_commute_distance),
            ("transport_distance", lambda x: x.total_transport_distance),
            ("attachment_distance", lambda x: x.total_transport_distance_attachments),
            ("machines", lambda x: x.number_of_machines),
            ("workers", lambda x: x.number_of_workers),
            ("attachments", lambda x: x.number_of_attachments)
        ]

        def sort_key(x):
            key = [
                -x.number_of_finished_orders,
                -x.total_dynamic_percentage,
                -x.number_of_finished_order_items
            ]

            # Falls ein Kriterium angegeben ist → nach vorne
            if criteria:
                for name, func in ordered_objectives:
                    if name == criteria:
                        key.append(func(x))  # zuerst das gewünschte Kriterium

            # Dann alle restlichen (in ursprünglicher Reihenfolge, außer dem schon verwendeten)
            for name, func in ordered_objectives:
                if name != criteria:
                    key.append(func(x))

            return tuple(key)

        self.ParetoFront = sorted(self.ParetoFront, key=sort_key)
    
    def SelectRandomBestSolution(self, all_values: bool = False):
        objective_map = {
            "driver_violation": lambda x: x.driver_violation,
            "commute_distance": lambda x: x.total_commute_distance,
            "transport_distance": lambda x: x.total_transport_distance,
            "attachment_distance": lambda x: x.total_transport_distance_attachments,
            "machines": lambda x: x.number_of_machines,
            "workers": lambda x: x.number_of_workers,
            "attachments": lambda x: x.number_of_attachments
        }

        selected_solutions = []
        best_value_dict = {}

        # Precompute all objective values for each solution once
        solution_values = {sol: {k: func(sol) for k, func in objective_map.items()} for sol in self.ParetoFront}

        

        for key in objective_map:
            try:
                # Extract values for the current objective
                values = [vals[key] for vals in solution_values.values()]
                best_value = min(values)
                best_value_dict[key] = round(best_value, 2)

                # Filter candidates that match best_value
                candidate_solutions = [sol for sol, vals in solution_values.items() if vals[key] == best_value]

                if len(candidate_solutions) == 1:
                    selected_solutions.append(candidate_solutions[0])
                    continue

                # Normalize other objectives
                normalized_scores = []
                precomputed_sub_values = {sub_key: [solution_values[s][sub_key] for s in candidate_solutions] for sub_key in objective_map if sub_key != key}
                for sol in candidate_solutions:
                    score = 0.0
                    for sub_key in objective_map:
                        if sub_key == key:
                            continue
                        v_min = min(precomputed_sub_values[sub_key])
                        v_max = max(precomputed_sub_values[sub_key])
                        val = solution_values[sol][sub_key]
                        norm = (val - v_min) / (v_max - v_min) if v_max != v_min else 0.0
                        score += norm
                    normalized_scores.append((score, sol))

                best_sol = min(normalized_scores, key=lambda x: x[0])[1]
                selected_solutions.append(best_sol)

            except ValueError:
                continue

        if all_values:
            df = pd.DataFrame(best_value_dict.items(), columns=["Objective", "Best Value"])
            print("\nBest individual values:")
            print(df.to_string(index=False))
            return None

        if not selected_solutions:
            raise KeyError("No solutions found.")

        return self.RNG.choice(selected_solutions)

    def ShowFront(self):
        ''' Show the Pareto Front as a DataFrame'''

        # Create a DataFrame from the Pareto Front

        # Create a list of dictionaries for the solutions
        solutions = []
        for solution in self.ParetoFront:
            solutions.append({
                "Orders": solution.number_of_finished_orders,
                "Order Items": solution.number_of_finished_order_items,
                "Driver Violation": solution.driver_violation,
                "Commute Distance": round(solution.total_commute_distance, 2),
                "Transport Machines": round(solution.total_transport_distance, 2),
                "Transport Attachments": round(solution.total_transport_distance_attachments, 2),
                "Machines": solution.number_of_machines,
                "Workers": solution.number_of_workers,
                "Attachments": solution.number_of_attachments
            })

        # Create a DataFrame from the list of dictionaries
        df = pd.DataFrame(solutions)

        # Sort according to the total_dynamic_percentage (higher is better), then sort by the other objectives
        df = df.sort_values(by=["Orders" , "Order Items", "Driver Violation", "Commute Distance",
                                "Transport Machines", "Transport Attachments",
                                "Machines", "Workers", "Attachments"],
                            ascending=[False, False, True, True, True, True, True, True, True])
        

        # Show the DataFrame
        print(df)
        # Write the DataFrame to a CSV file to self.InputData.solution_path
        df.to_csv(self.data.solutions_path / "ParetoFront.csv", index=False)




# Not in use
    def CalculateParetoFrontMetrics(self):
        """
        Calculates the hypervolume and spread of the Pareto Front
        and write the results to a CSV file.
        """
        # Check if Pareto Front is empty
        if not self.ParetoFront:
            print("Pareto Front is empty. Cannot calculate metrics.")
            return

        # Calculate hypervolume
        hv_value, hv_log, hv_sqrt = self.CalculateHypervolume()

        # Calculate spread
        spread_value = self.CalculateSpread()

        # Save metrics to CSV file
        metrics = {
            "Number of Solutions": len(self.ParetoFront),
            "Reference Point": self.ReferencePoint.tolist(),
            "Hypervolume": hv_value,
            "Hypervolume Log10": hv_log,
            "Hypervolume Sqrt": hv_sqrt,
            "Spread": spread_value,
        }
        
        metrics_df = pd.DataFrame([metrics])
        metrics_df.to_csv(self.data.solutions_path / "pareto_metrics.csv", index=False)

    def SetReferencePoint(self, solution: Solution):
        """
        Sets the reference point for hypervolume calculation based on a given solution.
        
        Args:
            solution (Solution): A solution object containing the objectives.
        
        Raises:
            ValueError: If the solution is None or if the objectives are not set.
        """
        if solution is None:
            raise ValueError("Solution cannot be None.")
        
        epsilon = 4
        epsilon_2 = 8
        driver = solution.driver_violation * epsilon
        commute = solution.total_commute_distance * epsilon_2
        transport = solution.total_transport_distance * epsilon_2
        attachments = solution.total_transport_distance_attachments * epsilon_2
        workers = solution.number_of_workers * epsilon
        machines = solution.number_of_machines * epsilon
        attach_count = solution.number_of_attachments * epsilon

        epsilon = 1e-6  # Small value to avoid numerical issues
        self.ReferencePoint = np.array([
            driver + epsilon,
            commute + epsilon,
            transport + epsilon,
            attachments + epsilon,
            workers + epsilon,
            machines + epsilon,
            attach_count + epsilon
        ])

    def CalculateHypervolume(self) -> float:
        """
        Calculates the hypervolume of the Pareto Front using pygmo.
        
        Assumptions:
        - The Pareto Front is stored in self.ParetoFront.
        - Each solution in the Pareto Front has the following attributes:
            driver_violation,
            total_commute_distance,
            total_transport_distance,
            total_transport_distance_attachments,
            number_of_workers,
            number_of_machines,
            number_of_attachments.
        - The reference point is set via SetReferencePoint and stored in self.ReferencePoint
            as a NumPy array with the same order of objectives.
        
        Returns:
            float: The computed hypervolume.
        """

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
        
        # Create a Hypervolume object with the objectives
        hv = pg.hypervolume(objs)
        
        # Calculate the hypervolume using the reference point
        hv_value = hv.compute(self.ReferencePoint)

        # Adjust hypervolume for comparison
        hv_log = math.log10(hv_value) * 10
        hv_sqrt = math.sqrt(hv_value)
        
        return hv_value, hv_log, hv_sqrt

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
        
