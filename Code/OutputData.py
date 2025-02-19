from InputData import *
import json
import pandas as pd
import plotly.express as px
import os
from datetime import timedelta
from collections import Counter



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

        self.not_started_order_item_ids = []

        self.share_finished_orders = -0
        self.number_of_finished_orders = -0
        self.number_of_finished_order_items = -0

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
                f"Dynamic percentage: {self.total_dynamic_percentage}\n"
                f"Number of finished order items: {self.number_of_finished_order_items}\n"
                f"Driver violation: {self.driver_violation}\n"
                f"Commute distance: {round(self.total_commute_distance, 2)}\n"
                f"Transport distance: {round(self.total_transport_distance, 2)}\n"
                f"Transport distance attachment: {round(self.total_transport_distance_attachments, 2)}\n"
                f"Number of workers: {self.number_of_workers}\n"
                f"Number of machines: {self.number_of_machines}\n"
                f"Number of attachments: {self.number_of_attachments}\n")
    

    def repair_solution(self):
        ''' Repair the solution by deleting all order items of semi-finished orders from the route plans'''
        ## OR
        ''' Repair the solution with heuristic or mathamatical optimization by reassigning the order items of semi-finished orders to the route plans'''

        ## TO DO: Implement the repair solution method
        pass


    def create_output_file_greedy(self, time_for_data_loading, time_for_construction ,order_item_attractiveness_technique:str, machine_attractiveness_technique:str):
        ''' Create the output file for the greedy solution for comparing different strategies'''

        # Create a dictionary for the solution
        solution = {
            "Instance": self.data.instance,
            "Time_for_data_loading": time_for_data_loading,
            "Time_for_construction": time_for_construction,
            "Order_item_attractiveness_technique": order_item_attractiveness_technique,
            "Machine_attractiveness_technique": machine_attractiveness_technique,
            "Number_of_finished_orders": self.number_of_finished_orders,
            "Number_of_semifinished_orders": len(self.semifinished_orders),
            "Number_of_not_started_orders": len(self.not_started_orders),
            "Number_of_finished_order_items": self.number_of_finished_order_items,
            "Driver_violation": self.driver_violation,
            "Commute_distance": round(self.total_commute_distance, 2),
            "Transport_distance": round(self.total_transport_distance, 2),
            "Number_of_workers": self.number_of_workers,
            "Number_of_machines": self.number_of_machines,
            "Sum_dynamic_precentage": round(sum([order.dynamic_percentage for order in self.data.orders]),4),
            "Dynamic_percentage": [round(order.dynamic_percentage,4) for order in self.data.orders],
            "Worker_route_plan": self.route_plan_worker,
            "Machine_route_plan": self.route_plan_machine
        }


        print("\nCreating output file...")

        # Define the base directory (parent of the 'Code' directory)
        base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Build the output file path
        output_file_path = os.path.join(
            base_directory, "Data", "Solution", "Greedy_Testing",  self.data._parent_folder, self.data.instance , f"OI_{order_item_attractiveness_technique}_M_{machine_attractiveness_technique}_{self.data.instance}.json"
        )

        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        # Write the solution to the JSON file
        with open(output_file_path, 'w') as file:
            json.dump(solution, file, indent=4)

        print(f"Solution saved to: {output_file_path}")

    def feasibility_check(self, verbose=False):
        """
        Check the feasibility of the solution.
        This function verifies that the assignment of order items to the machine, worker, and attachment routes
        meets all constraints.
        """
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
                    print(f"In attachment route: {attachment_id}, Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                    return False

            if verbose:
                print(f"Route for attachment {attachment_id} is feasible.")

        print("\nFeasibility check completed. Solution is feasible.")
        return True    

    
    # Old Version of Feasibility Check
    '''
    def feasibility_check(self, verbose=False):
        Check the feasibility of the solution.
        print("\nChecking the feasibility of the solution...")
        
        # ========================
        # 1. Order Item Feasibility
        # ========================
        if verbose:
            print("\nChecking if the assigned order items are present in both route plans...")

        # Check if all order items in machine route are present in worker route
        for machine_route_order_items in self.route_plan_machine.values():
            for order_item in machine_route_order_items:
                if not any(order_item in worker_route_order_items for worker_route_order_items in self.route_plan_worker.values()):
                    print(f"Order item {order_item} is not present in the worker route.")
                    return False

        # Check if all order items in worker route are present in machine route
        for worker_route_order_items in self.route_plan_worker.values():
            for order_item in worker_route_order_items:
                if not any(order_item in machine_route_order_items for machine_route_order_items in self.route_plan_machine.values()):
                    print(f"Order item {order_item} is not present in the machine route.")
                    return False

        # 1. Check: No duplicates within each worker's route
        for worker_id, route in self.route_plan_worker.items():
            if len(route) != len(set(route)):
                print(f"Worker {worker_id} has duplicate order items in their route: {route}")
                return False

        # 2. Check: Each order item appears only in one worker's route overall
        all_worker_order_items = [order_item for route in self.route_plan_worker.values() for order_item in route]
        if len(all_worker_order_items) != len(set(all_worker_order_items)):
            print("An order item has been assigned to more than one worker.")
            return False

        # 1. Check: No duplicates within each machine's route
        for machine_id, route in self.route_plan_machine.items():
            if len(route) != len(set(route)):
                print(f"Machine {machine_id} has duplicate order items in its route: {route}")
                return False

        # 2. Check: Each order item appears only in one machine's route overall
        all_machine_order_items = [order_item for route in self.route_plan_machine.values() for order_item in route]
        if len(all_machine_order_items) != len(set(all_machine_order_items)):
            print("An order item has been assigned to more than one machine.")
            return False

        # 1. Check: No duplicates within each attachment's route
        for attachment_id, route in self.route_plan_attachment.items():
            if len(route) != len(set(route)):
                print(f"Attachment {attachment_id} has duplicate order items in its route: {route}")
                return False
                
        # Check that all order items are assigned to the needed attachments with the correct counts
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
                        # If the equipment type isn't required at all or is over-assigned:
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
                    print(f"Machine {machine_name} is not correct assigned to order item {order_item.id}.")
                    return False

            # Check if the sequence of the order items is correct with start, end and travel times
            for order_item_i in order_item_objects:
                for order_item_j in order_item_objects:
                    order_item_i_index = order_item_objects.index(order_item_i)
                    order_item_j_index = order_item_objects.index(order_item_j)
                    if order_item_i_index + 1 == order_item_j_index:
                        order_i = next((order for order in self.data.orders if int(order_item_i.id) in [int(item) for item in order.order_item_ids]), None)
                        order_j = next((order for order in self.data.orders if int(order_item_j.id) in [int(item) for item in order.order_item_ids]), None)
                        distance = self.data.transport_routes[order_i.site_number][order_j.site_number]
                        travel_time_double = (distance / self.data._transport_speed_kmh)
                        travel_time = timedelta(hours=travel_time_double)
                        if order_item_i.end_time + travel_time >= order_item_j.start_time:
                            print(f"Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
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

            # Check if the worker qualifications are correct for the order items in the route
            for order_item in order_item_objects:
                if order_item.worker_qualifications:
                    if not set(order_item.worker_qualifications).issubset(set(worker_object.qualifications)):
                        print(f"Worker {worker_id} (Qualifications: {worker_object.qualifications}) does not have the correct qualifications for order item {order_item.id} (Qualifications: {order_item.worker_qualifications}).")
                        return False

            # Check if the sequence of the order items is correct with start, end and break times
            for order_item_i in order_item_objects:
                for order_item_j in order_item_objects:
                    order_item_i_index = order_item_objects.index(order_item_i)
                    order_item_j_index = order_item_objects.index(order_item_j)
                    if order_item_i_index + 1 == order_item_j_index:
                        break_time_double = self.data._hours_between_shifts
                        break_time = timedelta(hours=break_time_double)
                        if order_item_i.end_time + break_time >= order_item_j.start_time:
                            print(f"Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                            return False

            # Check if the worker does not work more than 5 consecutive night shifts
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
            
            # Check if the worker does not work more than 10 shifts in 14 days
            for i, order_item_i in enumerate(order_item_objects):
                window_start = order_item_i.start_time.date()
                window_end = window_start + self.data._time_period_for_max_shifts
                shift_count = 0
                for order_item_j in order_item_objects:
                    if window_start <= order_item_j.start_time.date() < window_end:
                        shift_count += 1
                if shift_count > self.data._max_shifts_in_time_period:
                    print(f"Worker {worker_id} has more than {self.data._max_shifts_in_time_period} shifts ({shift_count}) within the {self.data._time_period_for_max_shifts}-day period starting on {window_start}.")
                    return False

            # Check if the worker does not work more than 160 hours in a month
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
 
            # Check if the attachment type is correct for the order items in the route
            for order_item in order_item_objects:
                if attachment_object.type not in order_item.equipment_types:
                    print(f"Attachment {attachment_id} is not correctly assigned to order item {order_item.id}.")
                    return False

            # Check if the sequence of the order items is correct with start, end and travel times
            for order_item_i in order_item_objects:
                for order_item_j in order_item_objects:
                    order_item_i_index = order_item_objects.index(order_item_i)
                    order_item_j_index = order_item_objects.index(order_item_j)
                    if order_item_i_index + 1 == order_item_j_index:
                        order_i = next((order for order in self.data.orders if int(order_item_i.id) in [int(item) for item in order.order_item_ids]), None)
                        order_j = next((order for order in self.data.orders if int(order_item_j.id) in [int(item) for item in order.order_item_ids]), None)
                        distance = self.data.transport_routes[order_i.site_number][order_j.site_number]
                        travel_time_double = (distance / self.data._transport_speed_kmh)
                        travel_time = timedelta(hours=travel_time_double)
                        if order_item_i.end_time + travel_time >= order_item_j.start_time:
                            print(f"Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                            return False
                        
            if verbose:
                print(f"Route for attachment {attachment_id} is feasible.")


        print("\nFeasibility check completed. Solution is feasible.")
        return True

        '''
       

class ParetoSolutions:
    ''' Class for creating lits objects containing solution objects'''

    def __init__(self):
        ''' Create an empty list for the solutions'''
        self.ParetoFront = []

    def PurgeParetoFront(self):
        """
        Iterates over all solutions in the Pareto Front (self.ParetoFront) and removes any solution 
        that is dominated by another solution in the list.
        
        Function compare_solutions(solution_a, solution_b) is available:
        - Returns 1 if solution_a dominates solution_b.
        - Returns -1 if solution_b dominates solution_a.
        - Returns 0 if neither dominates the other.
        
        After execution, self.ParetoFront contains only non-dominated solutions.
        """
        non_dominated = []
        for i, sol in enumerate(self.ParetoFront):
            dominated = False
            for j, other_sol in enumerate(self.ParetoFront):
                if i != j:
                    # Check if other_sol dominates sol
                    if self.CompareSolutions(other_sol, sol) == 1:
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
            if self.CompareSolutions(current_solution, new_solution) == -1:
                # new_solution is dominated by current_solution.
                return False

        # Remove all solutions in the Pareto Front that are dominated by new_solution.
        self.ParetoFront = [current_solution for current_solution in self.ParetoFront
                            if self.CompareSolutions(new_solution, current_solution) != 1]

        # Add new_solution to the Pareto Front.
        self.ParetoFront.append(new_solution)
        return True
    

    def CompareSolutions(self, current_solution: Solution, new_solution: Solution) -> int:
        """
        Compares current_solution and new_solution.
        
        Returns:
        1  if new_solution dominates current_solution,
        -1  if current_solution dominates new_solution,
        0  if neither dominates the other.
        
        For total_dynamic_percentage: higher is better.
        For all other objectives: lower is better.
        
        A solution dominates another if it is not worse in any objective and is strictly better in at least one.
        """
        objectives = [
            ("total_dynamic_percentage", "max"),
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

        for attr, goal in objectives:
            new_val = getattr(new_solution, attr)
            curr_val = getattr(current_solution, attr)
            
            if goal == "max":
                # Higher is better
                if new_val > curr_val:
                    new_better_count += 1
                elif new_val < curr_val:
                    current_better_count += 1
            else:
                # Lower is better
                if new_val < curr_val:
                    new_better_count += 1
                elif new_val > curr_val:
                    current_better_count += 1

        # new_solution dominates current_solution if:
        # - in keinem Ziel ist new_solution schlechter (d.h. current_better_count == 0)
        # - und in mindestens einem Ziel ist new_solution besser (new_better_count > 0)
        if current_better_count == 0 and new_better_count > 0:
            return 1

        # current_solution dominates new_solution if:
        # - in keinem Ziel ist current_solution schlechter (new_better_count == 0)
        # - und in mindestens einem Ziel ist current_solution besser (current_better_count > 0)
        if new_better_count == 0 and current_better_count > 0:
            return -1

        return 0  # Neither dominates the other

    def ShowFront(self):
        ''' Show the Pareto Front as a DataFrame'''

        # Create a DataFrame from the Pareto Front

        # Create a list of dictionaries for the solutions
        solutions = []
        for solution in self.ParetoFront:
            solutions.append({
                "Total Dynamic Percentage": solution.total_dynamic_percentage,
                "Driver Violation": solution.driver_violation,
                "Total Commute Distance": solution.total_commute_distance,
                "Total Transport Distance": solution.total_transport_distance,
                "Total Transport Distance Attachments": solution.total_transport_distance_attachments,
                "Number of Machines": solution.number_of_machines,
                "Number of Workers": solution.number_of_workers,
                "Number of Attachments": solution.number_of_attachments
            })

        # Create a DataFrame from the list of dictionaries
        df = pd.DataFrame(solutions)

        # Sort according to the total_dynamic_percentage (higher is better), then sort by the other objectives
        df = df.sort_values(by=["Total Dynamic Percentage", "Driver Violation", "Total Commute Distance",
                                "Total Transport Distance", "Total Transport Distance Attachments",
                                "Number of Machines", "Number of Workers", "Number of Attachments"],
                            ascending=[False, True, True, True, True, True, True, True])
        

        # Show the DataFrame
        print(df)



























class GanttDiagramGenerator:
    def __init__(self, input_file, parent_folder, optimization_strategy, number_of_objectives):
        """
        Initialize the GanttDiagramGenerator with input file and parent folder.
        """
        self.input_file = input_file
        self.parent_folder = parent_folder
        self.instance = input_file.split('Construction_')[1].split('.json')[0]
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.optimization_strategy = optimization_strategy
        self.number_of_objectives = number_of_objectives

        # Paths for input and output files
        self.input_file_path = os.path.join(
            self.script_dir, "..", "Data", "Instanzen", parent_folder, input_file
        )
        self.output_file_path = os.path.join(
            self.script_dir, "..", "Data", "Solution", parent_folder, self.instance, f"{self.number_of_objectives}_Objectives" ,self.optimization_strategy, f"Solution_{input_file}"
        )

        # Load input and output data
        self.input_data = self._load_json(self.input_file_path)
        self.output_data = self._load_json(self.output_file_path)

    @staticmethod
    def _load_json(file_path):
        """
        Load JSON data from the given file path.
        """
        with open(file_path, 'r') as file:
            return json.load(file)

    def create_gantt_diagrams(self):
        """
        Generate Gantt diagrams for both worker shifts and machine assignments.
        """
        print(f"Creating Gantt diagrams for instance {self.instance}...")

        self._create_shift_plan()
        self._create_machine_plan()

        print(f"Gantt diagrams have been created.\n")

    def _create_shift_plan(self):
        """
        Create a Gantt diagram for worker shifts based on input and output data.
        """
        worker_assignments = self.output_data['Arbeiterzuweisung']
        unassigned_workers = [
            w['Name'] for w in self.input_data['Arbeiter'] if w['Name'] not in worker_assignments
        ]

        # Build DataFrame for worker shifts
        df = pd.DataFrame([
            {'Arbeiter': worker, 'Start': shift['Start'], 'Ende': shift['Ende'], 'ID': shift['ID']}
            for worker, shifts in worker_assignments.items() for shift in shifts
        ])

        # Determine shift type (early or late shift) based on start time
        df['Shift_Type'] = df['Start'].apply(
            lambda start: 'Early Shift' if pd.to_datetime(start).hour < 14 else 'Late Shift'
        )

        # Add site number based on task ID
        df['Site_Number'] = df['ID'].apply(self._get_site_number)

        # Create Gantt chart
        fig = px.timeline(
            df, x_start="Start", x_end="Ende", y="Arbeiter", color="Shift_Type",
            hover_data={'Shift_Type': False, 'Site_Number': True, 'Start': True, 'Ende': True, 'Arbeiter': False},
            category_orders={"Arbeiter": sorted(df["Arbeiter"].unique(), key=lambda x: int(x.split("_")[1]), reverse=True)},
            color_discrete_map={"Early Shift": "lightblue", "Late Shift": "lightcoral"}
        )
        fig.update_layout(
            title=f"Worker Assignments with Site Information for Instance {self.instance}",
            xaxis_title="Date", yaxis_title="Worker"
        )

        # Save and show the chart
        self._save_chart(fig, f"Shift_Plan_{self.instance}.html")
        print(f"Workers without shifts: {unassigned_workers}")

    def _create_machine_plan(self):
        """
        Create a Gantt diagram for machine and attachment assignments.
        """
        machine_assignments = self.output_data['Maschinenzuweisung']
        attachment_assignments = self.output_data.get('Anbaugeraetzuweisung', {})
        unassigned_machines = [
            m['Name'] for m in self.input_data['Maschinen'] if m['Name'] not in machine_assignments
        ]

        # Build DataFrames for machines and attachments
        machine_rows = [
            {'Name': machine, 'Start': usage['Start'], 'Ende': usage['Ende'], 'ID': usage['ID'], 'Type': 'Machine'}
            for machine, usages in machine_assignments.items() for usage in usages
        ]
        attachment_rows = [
            {'Name': attachment, 'Start': usage['Start'], 'Ende': usage['Ende'], 'ID': usage['ID'], 'Type': 'Attachment'}
            for attachment, usages in attachment_assignments.items() for usage in usages
        ]
        df_combined = pd.concat([pd.DataFrame(machine_rows), pd.DataFrame(attachment_rows)])

        # Add site number based on task ID
        df_combined['Site_Number'] = df_combined['ID'].apply(self._get_site_number)

        # Create Gantt chart
        fig = px.timeline(
            df_combined, x_start="Start", x_end="Ende", y="Name", color="Site_Number",
            hover_data={'Site_Number': False, 'Start': True, 'Ende': True, 'Type': True, 'Name': False},
            category_orders={
                "Name": sorted(df_combined["Name"].unique(), reverse=True),
                "Site_Number": sorted(df_combined["Site_Number"].unique(), key=lambda x: int(x))
            }
        )
        fig.update_layout(
            title=f"Machine and Attachment Assignments by Site for Instance {self.instance}",
            xaxis_title="Date", yaxis_title="Name"
        )

        # Save and show the chart
        self._save_chart(fig, f"Machine_Plan_{self.instance}.html")
        print(f"Machines without assignments: {unassigned_machines}")

    def _get_site_number(self, task_id):
        """
        Get the site number for a given task ID.
        """
        for task in self.input_data['Bestellpositionen']:
            if task['ID'] == task_id:
                return task['Auftragsnummer']
        return None

    def _save_chart(self, fig, file_name):
        """
        Save the Gantt chart as an HTML file and display it.
        """

        html_file_path = os.path.join(
            self.script_dir, "..", "Data", "Solution", self.parent_folder, self.instance, f"{self.number_of_objectives}_Objectives" , self.optimization_strategy,file_name
        )
        os.makedirs(os.path.dirname(html_file_path), exist_ok=True)
        fig.write_html(html_file_path)
        #fig.show()
